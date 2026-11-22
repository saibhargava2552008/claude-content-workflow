"""Acoustic model wrapper: load CTC models and compute frame-level emissions."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .audio_io import SAMPLE_RATE

FRAME_SAMPLES = 320
FRAME_DURATION = FRAME_SAMPLES / SAMPLE_RATE  # 0.02s
CACHE_ROOT = Path.home() / ".content-workflow-cache" / "emissions"


@dataclass(frozen=True)
class ModelConfig:
    key: str
    hf_model_id: str
    license_id: str
    description: str


AVAILABLE_MODELS = {
    "wav2vec2": ModelConfig(
        "wav2vec2",
        "facebook/wav2vec2-large-960h-lv60-self",
        "Apache-2.0",
        "English CTC character model; permissive license",
    ),
    "mms": ModelConfig(
        "mms",
        "MahmoudAshraf/mms-300m-1130-forced-aligner",
        "CC-BY-NC-4.0",
        "Multilingual forced aligner; non-commercial license",
    ),
}


class AcousticEngine:
    """Wraps a wav2vec2-style CTC model for emission computation."""

    def __init__(self, model_key: str, num_threads: int = 4):
        import torch
        from transformers import AutoFeatureExtractor, AutoTokenizer, Wav2Vec2ForCTC

        torch.set_num_threads(num_threads)
        self.config = AVAILABLE_MODELS[model_key]

        def _load(cls, **kwargs):
            try:
                return cls.from_pretrained(self.config.hf_model_id, local_files_only=True, **kwargs)
            except OSError:
                return cls.from_pretrained(self.config.hf_model_id, **kwargs)

        self.extractor = _load(AutoFeatureExtractor)
        self.tokenizer = _load(AutoTokenizer)
        self.model = _load(Wav2Vec2ForCTC).eval()
        self.vocabulary: dict[str, int] = self.tokenizer.get_vocab()
        self.blank_id = self._find_blank()
        self.separator_id = self.vocabulary.get("|")
        self.uses_uppercase = "A" in self.vocabulary and "a" not in self.vocabulary

    def _find_blank(self) -> int:
        for candidate in ("<blank>", "<pad>"):
            if candidate in self.vocabulary:
                return self.vocabulary[candidate]
        return int(self.model.config.pad_token_id)

    def text_to_tokens(self, phonetic: str) -> tuple[list[int], list[str]]:
        """Convert phonetic text to token IDs. Returns (ids, dropped_chars)."""
        ids: list[int] = []
        dropped: list[str] = []
        for part_idx, part in enumerate(phonetic.split()):
            if part_idx > 0 and self.separator_id is not None:
                ids.append(self.separator_id)
            for ch in part:
                lookup = ch.upper() if self.uses_uppercase else ch
                if lookup in self.vocabulary:
                    ids.append(self.vocabulary[lookup])
                else:
                    dropped.append(ch)
        return ids, dropped

    def compute_emissions(
        self, audio: np.ndarray, window_s: float = 30.0,
        overlap_s: float = 2.0, cache_key: str | None = None,
    ) -> np.ndarray:
        """Compute per-frame log-probabilities from audio."""
        cache_path = None
        if cache_key:
            digest = hashlib.sha256(
                f"{self.config.hf_model_id}|{cache_key}|{window_s}|{overlap_s}".encode()
            ).hexdigest()[:24]
            cache_path = CACHE_ROOT / f"{self.config.key}_{digest}.npy"
            if cache_path.exists():
                return np.load(cache_path)

        import torch

        total_samples = len(audio)
        num_frames = int(np.ceil(total_samples / FRAME_SAMPLES))
        vocab_size = self.model.config.vocab_size
        result = np.full((num_frames, vocab_size), -30.0, dtype=np.float32)
        result[:, self.blank_id] = 0.0

        win = int(window_s * SAMPLE_RATE)
        ctx = int(overlap_s * SAMPLE_RATE)

        for chunk_start in range(0, total_samples, win):
            chunk_end = min(total_samples, chunk_start + win)
            padded_start = max(0, chunk_start - ctx)
            padded_end = min(total_samples, chunk_end + ctx)

            inputs = self.extractor(
                audio[padded_start:padded_end],
                sampling_rate=SAMPLE_RATE, return_tensors="pt",
            )
            with torch.inference_mode():
                logits = self.model(inputs.input_values).logits[0]
            log_probs = torch.log_softmax(logits.float(), dim=-1).numpy()

            offset = (chunk_start - padded_start) // FRAME_SAMPLES
            count = int(np.ceil((chunk_end - chunk_start) / FRAME_SAMPLES))
            segment = log_probs[offset:offset + count]
            dest_start = chunk_start // FRAME_SAMPLES
            length = min(len(segment), num_frames - dest_start)
            result[dest_start:dest_start + length] = segment[:length]

        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_path, result)
        return result

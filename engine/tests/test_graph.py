"""Tests for CTC graph construction and Viterbi decoder."""
import numpy as np

from engine.graph import (
    BLANK_STATE, LABEL_STATE, WILDCARD_STATE,
    append_wildcard_column, construct_graph, viterbi_decode,
    extract_spans, find_wildcard_regions,
)

BLANK = 0
VOCAB = 6  # blank + tokens 1..5


def _synthetic_emissions(frame_tokens: list[int], noise: float = 0.0, seed: int = 0) -> np.ndarray:
    """Create emissions where each frame strongly predicts a given token."""
    rng = np.random.default_rng(seed)
    em = np.full((len(frame_tokens), VOCAB), -8.0, dtype=np.float32)
    for t, tok in enumerate(frame_tokens):
        if tok == -1:  # random speech
            em[t, rng.integers(1, VOCAB)] = -0.1
        else:
            em[t, tok] = -0.05
    em += rng.normal(0, noise, em.shape).astype(np.float32)
    return em


def test_simple_two_word_alignment():
    # word0=[1,2], word1=[3]: blank, 1, 1, 2, blank, 3, 3, 3, blank
    frames = [0, 0, 0, 1, 1, 2, 0, 0, 3, 3, 3, 0]
    em = _synthetic_emissions(frames)
    g = construct_graph([[1, 2], [3]], BLANK)
    path, scores = viterbi_decode(em, g)
    spans = extract_spans(path, scores, g, 2)
    assert (spans[0].first_frame, spans[0].last_frame) == (3, 6)
    assert (spans[1].first_frame, spans[1].last_frame) == (8, 11)


def test_repeated_tokens_need_blank():
    frames = [0, 4, 0, 4, 0]
    g = construct_graph([[4, 4]], BLANK)
    path, scores = viterbi_decode(_synthetic_emissions(frames), g)
    spans = extract_spans(path, scores, g, 1)
    assert spans[0].char_spans == [(1, 2), (3, 4)]


def test_separator_excluded_from_words():
    frames = [0, 1, 5, 2, 0]
    g = construct_graph([[1], [2]], BLANK, separator_id=5)
    path, scores = viterbi_decode(_synthetic_emissions(frames), g)
    spans = extract_spans(path, scores, g, 2)
    assert (spans[0].first_frame, spans[0].last_frame) == (1, 2)
    assert (spans[1].first_frame, spans[1].last_frame) == (3, 4)


def test_wildcard_absorbs_noise():
    # word0=[1], then 8 frames of noise, then word1=[2]
    frames = [0, 1, 1, 0] + [-1] * 8 + [0, 2, 2, 0]
    em, wc_col = append_wildcard_column(_synthetic_emissions(frames, seed=7), BLANK, penalty=-1.0)
    g = construct_graph([[1], [2]], BLANK, wildcard_col=wc_col, wildcard_positions={1})
    path, scores = viterbi_decode(em, g)
    spans = extract_spans(path, scores, g, 2)
    assert (spans[0].first_frame, spans[0].last_frame) == (1, 3)
    assert (spans[1].first_frame, spans[1].last_frame) == (13, 15)
    regions = find_wildcard_regions(path, g)
    assert len(regions) == 1 and regions[0][2] == 1
    assert regions[0][1] - regions[0][0] >= 6


def test_wildcard_skipped_when_clean():
    frames = [0, 1, 1, 0, 2, 2, 0]
    em, wc_col = append_wildcard_column(_synthetic_emissions(frames), BLANK, penalty=-2.0)
    g = construct_graph([[1], [2]], BLANK, wildcard_col=wc_col, wildcard_positions={0, 1, 2})
    path, _ = viterbi_decode(em, g)
    assert not (g.state_type[path] == WILDCARD_STATE).any()


def test_adjacent_words_no_gap():
    frames = [1, 1, 2, 2]
    g = construct_graph([[1], [2]], BLANK)
    path, scores = viterbi_decode(_synthetic_emissions(frames), g)
    spans = extract_spans(path, scores, g, 2)
    assert spans[0].last_frame == spans[1].first_frame == 2

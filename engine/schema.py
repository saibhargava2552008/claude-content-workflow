"""JSON Schema definition for timing output validation."""
from __future__ import annotations

SCHEMA_VERSION = 1

_num = {"type": "number"}
_int = {"type": "integer"}
_str = {"type": "string"}
_bool = {"type": "boolean"}
_str_array = {"type": "array", "items": _str}

WORD_SCHEMA = {
    "type": "object",
    "required": [
        "i", "raw", "display", "phonetic", "start", "end", "score", "conf",
        "language", "tags", "punctuation", "sentence_id", "phrase_id",
        "is_signpost", "rms_db", "duration_z", "flags",
    ],
    "properties": {
        "i": _int, "raw": _str, "display": _str, "phonetic": _str,
        "start": _num, "end": _num, "score": _num, "conf": _num, "score_z": _num,
        "language": {"enum": ["en", "num", "other"]},
        "tags": _str_array, "punctuation": _str,
        "sentence_id": _int, "phrase_id": _int,
        "is_signpost": _bool, "rms_db": _num, "duration_z": _num, "flags": _str_array,
    },
}

GROUP_SCHEMA = {
    "type": "object",
    "required": ["id", "first_word", "last_word", "start", "end", "text"],
    "properties": {
        "id": _int, "first_word": _int, "last_word": _int,
        "start": _num, "end": _num, "text": _str,
    },
}

TIMING_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "claude-content-workflow timing.json",
    "type": "object",
    "required": [
        "schema_version", "meta", "words", "boundaries",
        "sentences", "phrases", "speech_rate", "unscripted_regions",
    ],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "meta": {
            "type": "object",
            "required": [
                "project", "script_hash", "audio_hash", "audio_file",
                "duration_s", "model", "frame_duration",
            ],
        },
        "words": {"type": "array", "items": WORD_SCHEMA, "minItems": 1},
        "boundaries": {"type": "array"},
        "sentences": {"type": "array", "items": GROUP_SCHEMA},
        "phrases": {"type": "array", "items": GROUP_SCHEMA},
        "speech_rate": {"type": "object", "required": ["window_s", "step_s", "values"]},
        "unscripted_regions": {"type": "array"},
    },
}


def validate_timing(data: dict) -> None:
    """Validate timing data against the schema."""
    import jsonschema
    jsonschema.validate(data, TIMING_SCHEMA)

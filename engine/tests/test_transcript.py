"""Tests for the transcript tokenizer."""
from pathlib import Path

from engine.transcript import Token, number_to_words, tokenize, normalize_text


def _find(tokens, raw):
    return next(t for t in tokens if t.raw == raw)


def test_basic_sentence_splitting():
    tokens = tokenize("Build great apps. Ship them fast.")
    assert tokens[-1].sentence_id >= 1
    assert all(t.phonetic for t in tokens)


def test_number_conversion_basic():
    assert number_to_words(0) == "zero"
    assert number_to_words(7) == "seven"
    assert number_to_words(42) == "forty two"
    assert number_to_words(100) == "one hundred"
    assert number_to_words(2026) == "two thousand twenty six"


def test_number_token_with_unit():
    tokens = tokenize("starts at 7pm and runs for 3days")
    seven = _find(tokens, "7pm")
    assert seven.display == "7 PM"
    assert seven.phonetic == "seven pee em"
    assert seven.language == "num"
    three = _find(tokens, "3days")
    assert three.display == "3 days"
    assert "check_pronunciation" in three.flags


def test_symbol_handling():
    tokens = tokenize("coding + practice = mastery")
    plus = _find(tokens, "+")
    assert plus.phonetic == "plus"
    assert "symbol" in plus.tags
    eq = _find(tokens, "=")
    assert eq.phonetic == "equals"


def test_abbreviation_expansion():
    tokens = tokenize("the AI model uses a REST API")
    ai = _find(tokens, "AI")
    assert ai.phonetic == "ay eye"
    assert "abbreviation" in ai.tags
    api = _find(tokens, "API")
    assert api.phonetic == "ay pee eye"


def test_unicode_normalization():
    result = normalize_text("it\u2019s a \u201csmart\u201d quote\u2026")
    assert "\u2019" not in result
    assert "\u201c" not in result


def test_punctuation_attaches_to_previous():
    tokens = tokenize("wait... what?! really.")
    wait = _find(tokens, "wait")
    assert "..." in wait.punctuation
    assert "trailing_dots" in wait.tags
    what = _find(tokens, "what")
    assert "question" in what.tags
    assert "exclamation" in what.tags


def test_phrase_boundaries():
    tokens = tokenize("first, do this; then do that")
    first = _find(tokens, "first")
    then_tok = _find(tokens, "then")
    assert then_tok.phrase_id > first.phrase_id


def test_empty_input():
    tokens = tokenize("")
    assert tokens == []


def test_elongated_words():
    tokens = tokenize("that is soooo cool")
    so = _find(tokens, "soooo")
    assert "elongated" in so.tags
    assert so.phonetic == "so"


def test_all_phonetic_chars_valid():
    tokens = tokenize("Write clean code. Test everything. Deploy with confidence!")
    for t in tokens:
        assert set(t.phonetic) <= set("abcdefghijklmnopqrstuvwxyz' "), f"Invalid phonetic: {t.phonetic!r}"

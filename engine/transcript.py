"""Script tokenizer: convert raw text into structured tokens for alignment.

Each token carries multiple text representations:
  raw       — the original text as written
  display   — cleaned version for on-screen rendering
  phonetic  — lowercase pronunciation form for alignment (a-z and apostrophe only)

Plus metadata: punctuation context, language tag, sentence/phrase IDs,
semantic tags, and QC flags.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

SPLIT_PATTERN = re.compile(r"\n+|[A-Za-z0-9']+|[^\sA-Za-z0-9']+")

SYMBOL_PRONUNCIATIONS = {
    "+": "plus", "&": "and", "=": "equals",
    "%": "percent", "@": "at", "#": "hash",
}

UNIT_DISPLAY = {"pm": "PM", "am": "AM", "gb": "GB", "mb": "MB", "kb": "KB", "hz": "Hz"}
UNIT_SPOKEN = {
    "pm": "pee em", "am": "ay em", "gb": "gee bee", "mb": "em bee",
    "kb": "kay bee", "hz": "hertz", "st": "", "nd": "", "rd": "", "th": "",
}

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


@dataclass
class Token:
    index: int
    raw: str
    display: str
    phonetic: str
    punctuation: str = ""
    ends_line: bool = False
    tags: list[str] = field(default_factory=list)
    language: str = "unknown"
    sentence_id: int = 0
    phrase_id: int = 0
    is_signpost: bool = False
    flags: list[str] = field(default_factory=list)


def number_to_words(n: int) -> str:
    """Convert integer to English words."""
    if n < 0:
        return "minus " + number_to_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        remainder = n % 100
        return ONES[n // 100] + " hundred" + ("" if remainder == 0 else " " + number_to_words(remainder))
    if n < 1_000_000:
        remainder = n % 1000
        return number_to_words(n // 1000) + " thousand" + ("" if remainder == 0 else " " + number_to_words(remainder))
    return " ".join(ONES[int(ch)] for ch in str(n))


def normalize_text(text: str) -> str:
    """Normalize unicode and whitespace."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _to_phonetic(s: str) -> str:
    """Reduce to alignment-safe characters: lowercase a-z and apostrophe."""
    s = s.lower()
    s = re.sub(r"[^a-z' ]+", " ", s)
    s = re.sub(r"([a-z])\1{2,}", r"\1", s)  # collapse repeated letters
    s = re.sub(r"(^|\s)'+|'+(s|\s|$)", r"\1\2", s)
    return " ".join(s.split())


KNOWN_ABBREVIATIONS = {
    "ai": "ay eye", "ml": "em el", "api": "ay pee eye",
    "ui": "yoo eye", "ux": "yoo ex", "url": "yoo ar el",
    "html": "aitch tee em el", "css": "see es es",
    "js": "jay es", "sql": "es kyoo el", "cpu": "see pee yoo",
    "gpu": "jee pee yoo", "ram": "ar ay em", "os": "oh es",
    "dm": "dee em", "pm": "pee em", "am": "ay em",
    "id": "eye dee", "ip": "eye pee", "io": "eye oh",
}


def _derive_forms(raw: str) -> tuple[str, str, list[str], list[str]]:
    """Compute (display, phonetic, tags, flags) for a raw token."""
    tags: list[str] = []
    flags: list[str] = []
    lower = raw.lower().strip("'")

    # Symbol tokens
    if raw in SYMBOL_PRONUNCIATIONS:
        return raw, SYMBOL_PRONUNCIATIONS[raw], ["symbol"], []

    # Number + optional unit suffix: "7pm", "3days", "100GB"
    m = re.fullmatch(r"(\d+)([a-zA-Z]*)", raw)
    if m:
        num_val, suffix = int(m.group(1)), m.group(2).lower()
        spoken_num = number_to_words(num_val)
        spoken_suffix = UNIT_SPOKEN.get(suffix, suffix)
        phonetic = _to_phonetic(f"{spoken_num} {spoken_suffix}".strip())
        disp_suffix = UNIT_DISPLAY.get(suffix, suffix)
        if suffix in ("st", "nd", "rd", "th"):
            display = f"{num_val}{suffix}"
        else:
            display = f"{num_val} {disp_suffix}".strip() if suffix else str(num_val)
        return display, phonetic, ["number"], ["check_pronunciation"]

    # Known abbreviations
    if lower in KNOWN_ABBREVIATIONS:
        tags.append("abbreviation")
        return raw.upper() if len(lower) <= 4 else raw, _to_phonetic(KNOWN_ABBREVIATIONS[lower]), tags, flags

    # All-caps short word — likely acronym
    if raw.isupper() and len(raw) >= 2:
        if len(raw) <= 3:
            tags.append("abbreviation")
            flags.append("check_pronunciation")
            spelled = " ".join(KNOWN_ABBREVIATIONS.get(c.lower(), c.lower()) for c in raw)
            return raw, _to_phonetic(spelled), tags, flags
        tags.append("emphasis")

    # Elongated words like "soooo"
    if re.search(r"([a-z])\1{2,}", lower):
        tags.append("elongated")

    return raw.strip("'"), _to_phonetic(lower), tags, flags


SENTENCE_END = re.compile(r"[.?!]")
PHRASE_BREAK = re.compile(r"[,;:\-]")

SIGNPOST_PHRASES = [
    "but", "however", "so", "because", "therefore",
    "first", "second", "third", "finally", "next",
    "for example", "in other words", "on the other hand",
]


def _detect_language(phonetic: str, tags: list[str]) -> str:
    """Simple language heuristic."""
    if "number" in tags:
        return "num"
    if "symbol" in tags:
        return "other"
    if "abbreviation" in tags:
        return "en"
    return "en"


def tokenize(text: str) -> list[Token]:
    """Tokenize a script into structured Token objects."""
    text = normalize_text(text)
    tokens: list[Token] = []

    for match in SPLIT_PATTERN.findall(text):
        # Newlines
        if match.startswith("\n"):
            if tokens:
                tokens[-1].ends_line = True
            continue

        has_alphanum = bool(re.search(r"[A-Za-z0-9]", match))
        if not has_alphanum and match.strip() not in SYMBOL_PRONUNCIATIONS:
            # Pure punctuation — attach to previous token
            if tokens:
                tokens[-1].punctuation += match
            continue

        display, phonetic, tags, flags = _derive_forms(match.strip())
        if not phonetic:
            if tokens:
                tokens[-1].punctuation += match
            continue

        tokens.append(Token(
            index=len(tokens),
            raw=match.strip(),
            display=display,
            phonetic=phonetic,
            tags=tags,
            flags=flags,
        ))

    # Assign sentence and phrase IDs, detect signposts
    _assign_structure(tokens)
    return tokens


def _assign_structure(tokens: list[Token]) -> None:
    """Assign sentence_id, phrase_id, language, and signpost flags."""
    sent = 0
    phrase = 0
    phonetics = [t.phonetic for t in tokens]

    for idx, tok in enumerate(tokens):
        if idx > 0:
            prev = tokens[idx - 1]
            if prev.ends_line or SENTENCE_END.search(prev.punctuation):
                sent += 1
                phrase += 1
            elif PHRASE_BREAK.search(prev.punctuation) or tok.is_signpost:
                phrase += 1

        tok.sentence_id = sent
        tok.phrase_id = phrase
        tok.language = _detect_language(tok.phonetic, tok.tags)

        # Punctuation-based tags
        if "?" in tok.punctuation:
            tok.tags.append("question")
        if "!" in tok.punctuation:
            tok.tags.append("exclamation")
        if re.search(r"\.{2,}", tok.punctuation):
            tok.tags.append("trailing_dots")

    # Mark signpost words
    for idx, tok in enumerate(tokens):
        for sp in SIGNPOST_PHRASES:
            sp_words = sp.split()
            if phonetics[idx:idx + len(sp_words)] == sp_words:
                tok.is_signpost = True
                break


def punctuation_break_weight(tok: Token) -> float:
    """Score the boundary strength after a token (0.0 to 1.0)."""
    p = tok.punctuation
    if tok.ends_line or "?" in p or "!" in p:
        return 1.0
    if re.search(r"\.{2,}", p):
        return 0.8
    if "." in p:
        return 0.9
    if PHRASE_BREAK.search(p):
        return 0.5
    return 0.0

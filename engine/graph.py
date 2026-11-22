"""CTC token graph construction and Viterbi decoder for forced alignment.

Builds a constrained graph of states (blank, label, wildcard) from token
sequences, then finds the most likely path through acoustic emissions
using the Viterbi algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# State types
BLANK_STATE = 0
LABEL_STATE = 1
WILDCARD_STATE = 2

TRANSITION_DEPTH = 4
NINF = np.float32(-1e30)


@dataclass
class TokenGraph:
    """CTC alignment graph."""
    state_type: np.ndarray     # (N,) int8 — BLANK / LABEL / WILDCARD
    emission_col: np.ndarray   # (N,) int64 — which emission column each state reads
    token_word: np.ndarray     # (N,) int64 — word index for label states, -1 otherwise
    token_char: np.ndarray     # (N,) int64 — char position within word, -1 otherwise
    transitions: np.ndarray    # (N, TRANSITION_DEPTH+1) bool — allowed predecessor offsets
    can_start: np.ndarray      # (N,) bool — valid start states
    can_end: np.ndarray        # (N,) bool — valid end states

    @property
    def required_frames(self) -> int:
        return int((self.state_type == LABEL_STATE).sum())


def construct_graph(
    word_tokens: list[list[int]],
    blank_id: int,
    wildcard_col: int | None = None,
    wildcard_positions: set[int] | frozenset = frozenset(),
    separator_id: int | None = None,
) -> TokenGraph:
    """Build the CTC alignment graph from word token sequences."""
    types: list[int] = [BLANK_STATE]
    columns: list[int] = [blank_id]
    words: list[int] = [-1]
    chars: list[int] = [-1]

    def _append_state(stype: int, col: int, w: int = -1, c: int = -1) -> None:
        types.extend([stype, BLANK_STATE])
        columns.extend([col, blank_id])
        words.extend([w, -1])
        chars.extend([c, -1])

    has_wildcard = wildcard_col is not None
    for wi, toks in enumerate(word_tokens):
        if separator_id is not None and wi > 0:
            _append_state(LABEL_STATE, separator_id)
        if has_wildcard and wi in wildcard_positions:
            _append_state(WILDCARD_STATE, wildcard_col)
        for ci, tid in enumerate(toks):
            _append_state(LABEL_STATE, tid if tid != separator_id else tid, wi if tid != separator_id else -1, ci)
    if has_wildcard and len(word_tokens) in wildcard_positions:
        _append_state(WILDCARD_STATE, wildcard_col)

    st = np.array(types, dtype=np.int8)
    ec = np.array(columns, dtype=np.int64)
    N = len(st)

    # Build transition matrix: for each state, which offsets k (0..TRANSITION_DEPTH) are valid predecessors
    trans = np.zeros((N, TRANSITION_DEPTH + 1), dtype=bool)
    trans[:, 0] = True   # self-loop
    trans[1:, 1] = True  # from previous state

    for s in range(N):
        if st[s] != BLANK_STATE:
            # Skip blank between two different labels
            if s >= 2 and st[s - 1] == BLANK_STATE and st[s - 2] != BLANK_STATE and ec[s - 2] != ec[s]:
                trans[s, 2] = True
            # Skip wildcard group: blank, WILDCARD, blank -> s
            if s >= 3 and st[s - 1] == BLANK_STATE and st[s - 2] == WILDCARD_STATE and st[s - 3] == BLANK_STATE:
                trans[s, 3] = True
                if s >= 4 and st[s - 4] != BLANK_STATE and ec[s - 4] != ec[s]:
                    trans[s, 4] = True
        elif s >= 2 and st[s - 1] == WILDCARD_STATE and st[s - 2] == BLANK_STATE:
            trans[s, 2] = True  # skip wildcard from blank

    optional = st != LABEL_STATE
    start_ok = np.zeros(N, dtype=bool)
    end_ok = np.zeros(N, dtype=bool)
    for s in range(N):
        start_ok[s] = True
        if not optional[s]:
            break
    for s in range(N - 1, -1, -1):
        end_ok[s] = True
        if not optional[s]:
            break

    return TokenGraph(st, ec, np.array(words, dtype=np.int64), np.array(chars, dtype=np.int64),
                      trans, start_ok, end_ok)


def append_wildcard_column(emissions: np.ndarray, blank_id: int, penalty: float) -> tuple[np.ndarray, int]:
    """Add a wildcard emission column: best non-blank score plus penalty."""
    non_blank = np.delete(emissions, blank_id, axis=1)
    wildcard_scores = non_blank.max(axis=1, keepdims=True) + np.float32(penalty)
    extended = np.concatenate([emissions, wildcard_scores.astype(emissions.dtype)], axis=1)
    return extended, emissions.shape[1]


def viterbi_decode(emissions: np.ndarray, graph: TokenGraph) -> tuple[np.ndarray, np.ndarray]:
    """Find the optimal state path through emissions using Viterbi algorithm.

    Returns (path, frame_scores): state index per frame and log-prob per frame.
    """
    T = emissions.shape[0]
    N = len(graph.state_type)
    if graph.required_frames > T:
        raise ValueError(f"Audio too short: need >= {graph.required_frames} frames, got {T}")

    # Gather emission scores for each state at each frame
    scores = emissions[:, graph.emission_col].astype(np.float32)  # (T, N)
    blocked = [None] + [~graph.transitions[:, k] for k in range(1, TRANSITION_DEPTH + 1)]

    # Forward pass
    dp = np.full(N, NINF, dtype=np.float32)
    dp[graph.can_start] = scores[0, graph.can_start]
    backtrack = np.zeros((T, N), dtype=np.int8)
    candidate = np.empty(N, dtype=np.float32)

    for t in range(1, T):
        best = dp.copy()
        best_offset = np.zeros(N, dtype=np.int8)
        for k in range(1, TRANSITION_DEPTH + 1):
            candidate[:k] = NINF
            candidate[k:] = dp[:-k]
            candidate[blocked[k]] = NINF
            improved = candidate > best
            best[improved] = candidate[improved]
            best_offset[improved] = k
        dp = best + scores[t]
        backtrack[t] = best_offset

    # Backtrace
    terminal = np.where(graph.can_end, dp, NINF)
    s = int(np.argmax(terminal))
    if terminal[s] <= NINF / 2:
        raise RuntimeError("No valid alignment path exists")
    path = np.empty(T, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        path[t] = s
        s -= int(backtrack[t, s])
    frame_scores = scores[np.arange(T), path]
    return path, frame_scores


@dataclass
class WordSpan:
    """Frame span for a single word in the alignment."""
    word_index: int
    first_frame: int
    last_frame: int         # exclusive
    mean_score: float
    char_spans: list[tuple[int, int]]  # (start, end) per character token


def extract_spans(path: np.ndarray, frame_scores: np.ndarray, graph: TokenGraph, num_words: int) -> list[WordSpan]:
    """Extract per-word frame ranges from the alignment path."""
    results: list[WordSpan] = []
    path_words = graph.token_word[path]
    path_chars = graph.token_char[path]
    is_label = (graph.state_type[path] == LABEL_STATE) & (path_words >= 0)

    for w in range(num_words):
        frames = np.nonzero(is_label & (path_words == w))[0]
        if len(frames) == 0:
            results.append(WordSpan(w, -1, -1, float("-inf"), []))
            continue
        char_ranges: list[tuple[int, int]] = []
        for ci in np.unique(path_chars[frames]):
            cf = frames[path_chars[frames] == ci]
            char_ranges.append((int(cf[0]), int(cf[-1]) + 1))
        results.append(WordSpan(
            w, int(frames[0]), int(frames[-1]) + 1,
            float(frame_scores[frames].mean()), char_ranges,
        ))
    return results


def find_wildcard_regions(path: np.ndarray, graph: TokenGraph) -> list[tuple[int, int, int]]:
    """Find contiguous wildcard frame runs. Returns (start, end, next_word_index)."""
    is_wc = graph.state_type[path] == WILDCARD_STATE
    regions: list[tuple[int, int, int]] = []
    t, T = 0, len(path)
    while t < T:
        if is_wc[t]:
            start = t
            while t < T and is_wc[t]:
                t += 1
            next_word = -1
            for u in range(t, T):
                if graph.state_type[path[u]] == LABEL_STATE and graph.token_word[path[u]] >= 0:
                    next_word = int(graph.token_word[path[u]])
                    break
            regions.append((start, t, next_word))
        else:
            t += 1
    return regions

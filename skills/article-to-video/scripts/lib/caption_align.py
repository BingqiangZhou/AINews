"""Caption text alignment utilities shared by subtitle pipelines.

Extracted from map-ai-captions.py so both the (currently disabled) AI
caption path and the tts_script-driven alignment in
generate-timeline-captions.py share one implementation.

Key difference from the original map-ai-captions.py versions: the raw
character stream built from Whisper words is normalized here (punctuation
and whitespace stripped). Whisper word tokens often carry trailing
punctuation (e.g. ``你好,``), and tts_script sentences carry their own
punctuation; aligning a normalized sentence against an un-normalized word
stream miscounts characters and breaks the substring lookup. Both sides go
through ``normalize`` so matching is on bare characters only.
"""

from __future__ import annotations

import re
import sys
from typing import Any

# Characters stripped when matching caption text to raw word text.
# Whitespace + Chinese/ASCII punctuation + brackets/dashes/ellipsis.
PUNCT_RE = re.compile(
    r'[\s，。！？、；：""''（）【】《》,.!?;:\'"()\[\]{}\-—…·~`]'
)


def normalize(text: str) -> str:
    """Strip punctuation and whitespace for matching."""
    return PUNCT_RE.sub('', text)


def build_char_index(words: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Build normalized raw text and character-to-word mapping.

    Each character of each word is normalized (punctuation/whitespace
    dropped); only surviving characters are appended, so ``norm_text`` is a
    bare-character stream that matches ``normalize(sentence)`` exactly.

    Returns:
        (norm_text, char_to_word) where char_to_word[i] is the word dict
        whose normalized character is norm_text[i].
    """
    norm_text = ''
    char_to_word: list[dict[str, Any]] = []
    for w in words:
        word_text = str(w.get('text', w.get('word', ''))).strip()
        for ch in word_text:
            nch = normalize(ch)
            if not nch:
                continue
            # PUNCT_RE only deletes characters, so nch is at most one char,
            # but iterate defensively in case the regex changes later.
            for nc in nch:
                char_to_word.append(w)
                norm_text += nc
    return norm_text, char_to_word


def map_sentences(
    sentences: list[str],
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Map sentences to word timestamps via normalized character matching.

    Both the raw word text and the sentence text are normalized (stripped
    of punctuation and whitespace) before matching. Each mapped caption
    carries the sentence's original (punctuated) text and the start/end
    timestamps of its first/last aligned word.
    """
    raw_text, char_to_word = build_char_index(words)
    if not raw_text or not char_to_word:
        return None

    captions: list[dict[str, Any]] = []
    raw_pos = 0
    unmapped: list[str] = []

    for sent in sentences:
        sent_raw = normalize(sent)
        if not sent_raw:
            continue

        # Find exact match starting from current position
        found_pos = raw_text.find(sent_raw, raw_pos)

        if found_pos < 0:
            # Try a wider search — maybe a previous sentence consumed extra chars
            found_pos = raw_text.find(sent_raw, max(0, raw_pos - len(sent_raw)))
            if found_pos < 0:
                unmapped.append(sent[:30])
                continue

        start_char = found_pos
        end_char = found_pos + len(sent_raw)

        if end_char > len(char_to_word):
            unmapped.append(sent[:30])
            continue

        start_word = char_to_word[start_char]
        end_word = char_to_word[end_char - 1]

        captions.append({
            'text': sent,
            'startMs': start_word.get('startMs', 0),
            'endMs': end_word.get('endMs', 0),
            'index': len(captions),
        })

        raw_pos = end_char

    if unmapped:
        print(
            f'  WARNING: {len(unmapped)} sentence(s) could not be mapped: {unmapped[:3]}',
            file=sys.stderr,
        )

    return captions if captions else None


def verify_coverage(captions: list[dict[str, Any]], words: list[dict[str, Any]]) -> float:
    """Verify text coverage: how much of the raw word text is covered by captions.

    Both sides are normalized to bare characters before comparison, so
    punctuation in either source does not skew the ratio. Returns a value
    in [0.0, 1.0]; 1.0 means the caption text is a superset of the raw word
    text (full coverage).
    """
    if not captions or not words:
        return 0.0

    target = normalize(''.join(str(w.get('text', w.get('word', ''))) for w in words))
    source = normalize(''.join(c.get('text', '') for c in captions))

    if not target:
        return 0.0
    if source == target:
        return 1.0

    # Character-level DP alignment so scattered ASR substitutions
    # (e.g. 麦麦 vs 卖卖, 她 vs 他) don't crater the ratio. A one-pass
    # subsequence scan would jump to EOF at the first char in `target` that
    # is absent from `source` and report ~25% for text that is ~99% identical.
    s_to_t = _char_align_map(source, target)
    matches = sum(
        1 for i, t in enumerate(s_to_t)
        if t >= 0 and source[i] == target[t]
    )
    return matches / len(target)


def _char_align_map(source: str, target: str, match: int = 2,
                    mismatch: int = -1, gap: int = -2) -> list[int]:
    """Needleman–Wunsch global alignment of ``source`` chars onto ``target`` chars.

    Returns ``s_to_t`` where ``s_to_t[i]`` is the target index aligned to
    ``source[i]``, or -1 when ``source[i]`` aligns to a gap. Length == len(source).

    Tolerates scattered substitutions/insertions/deletions, which is exactly
    what we need: Whisper re-transcribing TTS audio makes a handful of
    character errors, and an exact substring match fails on whole sentences
    because of them. Character-level alignment absorbs those errors while
    still mapping each source character to its nearest target character.
    """
    n, m = len(source), len(target)
    if n == 0:
        return []
    # dp[i][j]: best score aligning source[:i] with target[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i * gap
    for j in range(1, m + 1):
        dp[0][j] = j * gap
    for i in range(1, n + 1):
        si = source[i - 1]
        row = dp[i]
        prev = dp[i - 1]
        for j in range(1, m + 1):
            sc = match if si == target[j - 1] else mismatch
            diag = prev[j - 1] + sc
            up = prev[j] + gap       # source[i-1] -> gap (deletion vs target)
            left = row[j - 1] + gap  # target[j-1] -> gap (insertion vs source)
            best = diag
            if up > best:
                best = up
            if left > best:
                best = left
            row[j] = best
    # Backtrack
    s_to_t = [-1] * n
    i, j = n, m
    while i > 0 and j > 0:
        sc = match if source[i - 1] == target[j - 1] else mismatch
        if dp[i][j] == dp[i - 1][j - 1] + sc:
            s_to_t[i - 1] = j - 1
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + gap:
            i -= 1  # source[i-1] aligned to gap
        else:
            j -= 1  # target[j-1] aligned to gap
    # Any remaining source chars (i>0, j==0) stay -1
    return s_to_t


def align_sentences_to_words(
    sentences: list[str],
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Align each sentence onto word timestamps via character-level DP.

    Robust replacement for :func:`map_sentences` when the sentence text and
    the word text differ by scattered character errors (the common case for
    tts_script vs Whisper re-transcription). Caption text is the original
    (punctuated) sentence; start/end timestamps come from the words aligned
    to the sentence's first/last characters.

    Returns captions list, or None if there is nothing to align on.
    """
    raw_text, char_to_word = build_char_index(words)
    if not raw_text or not char_to_word:
        return None

    # source = normalized sentences concatenated; track each sentence's span
    source = ''
    spans: list[tuple[int, int, int]] = []  # (sentence index, start off, end off)
    for si, sent in enumerate(sentences):
        ns = normalize(sent)
        if not ns:
            continue
        start = len(source)
        source += ns
        spans.append((si, start, len(source)))
    if not source:
        return None

    s_to_t = _char_align_map(source, raw_text)

    def _resolve(off: int) -> int:
        # Nearest non-gap target index at or after off, else before off.
        i = off
        while i < len(s_to_t) and s_to_t[i] < 0:
            i += 1
        if i < len(s_to_t):
            return s_to_t[i]
        i = off
        while i >= 0 and s_to_t[i] < 0:
            i -= 1
        return s_to_t[i] if i >= 0 else -1

    captions: list[dict[str, Any]] = []
    for si, start, end in spans:
        ts = _resolve(start)
        te = _resolve(end - 1)
        if ts < 0 or te < 0 or ts >= len(char_to_word) or te >= len(char_to_word):
            continue
        w0 = char_to_word[ts]
        w1 = char_to_word[te]
        captions.append({
            'text': sentences[si],
            'startMs': w0.get('startMs', 0),
            'endMs': w1.get('endMs', 0),
            'index': len(captions),
        })

    return captions if captions else None

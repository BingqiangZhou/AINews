#!/usr/bin/env python3
"""Generate word-aligned timeline_captions.json for each highlight.

Uses word-level timestamps from captions.json to create sentence-level
subtitles with accurate timing. Each caption is 0-based relative to the
clip audio start (clip_start_ms from clips.json).
"""

import json
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import setup_windows_encoding, read_json, write_json, probe_duration
from lib.caption_align import align_sentences_to_words, verify_coverage

load_json = read_json
save_json = write_json


def get_words_in_range(captions, start_ms, end_ms, clip_start_ms, clip_end_ms=None):
    """Extract all words that overlap the actual clip audio range."""
    effective_end_ms = clip_end_ms if clip_end_ms is not None else end_ms
    words = []
    for seg in captions:
        for w in seg.get('words', []):
            ws = w.get('startMs')
            we = w.get('endMs')
            if ws is None or we is None:
                continue
            if ws < effective_end_ms and we > clip_start_ms:
                clipped = dict(w)
                clipped['startMs'] = max(ws, clip_start_ms)
                clipped['endMs'] = min(we, effective_end_ms)
                if clipped['endMs'] > clipped['startMs']:
                    words.append(clipped)
    # Sort by startMs and deduplicate
    words.sort(key=lambda w: w['startMs'])
    seen = set()
    unique = []
    for w in words:
        key = (w['startMs'], w['word'])
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def smooth_inter_segment_gaps(words):
    """Fix small gaps and overlaps between words from different Whisper segments.

    Operates on the flattened word list after extraction and dedup.
    - Gap < 20ms: split at midpoint
    - Overlap > 50ms: split evenly
    - Gap > 3000ms: leave unchanged (real pause)
    """
    if len(words) < 2:
        return words
    smoothed = [dict(words[0])]
    for i in range(1, len(words)):
        w = dict(words[i])
        prev = smoothed[-1]
        gap = w['startMs'] - prev['endMs']
        if 0 <= gap < 20:
            mid = (prev['endMs'] + w['startMs']) / 2
            prev['endMs'] = mid
            w['startMs'] = mid
        elif gap < 0 and abs(gap) > 50:
            overlap = abs(gap)
            split_point = prev['endMs'] - overlap / 2
            prev['endMs'] = split_point
            w['startMs'] = split_point
        smoothed.append(w)
    return smoothed


def compress_stretched_words(words, max_ms_per_char=1500, target_ms_per_char=500,
                             gap_threshold_ms=2000):
    """Clip endMs of words with excessive duration per character.

    Only shortens endMs — does NOT shift subsequent words. The clipped endMs
    creates gaps where the speaker paused but Whisper assigned the pause to a
    single word. These gaps become real pauses (no subtitle) in the output.
    """
    if not words:
        return []
    result = []
    for w in words:
        w = dict(w)
        dur = w['endMs'] - w['startMs']
        chars = len(w.get('word', ''))
        if chars > 0 and dur / chars > max_ms_per_char:
            w['endMs'] = w['startMs'] + chars * target_ms_per_char
        result.append(w)
    return result


def _find_split_point(text, target_chars, tolerance):
    """Find the best character position to split Chinese text.

    Searches within [target - tolerance, target + tolerance] for a natural
    break point. Priority: sentence-end > comma > tone particle > structure particle.
    Returns the split position (split AFTER that char), or target if no better point.
    """
    SENTENCE_END = '。！？.!?'
    CLAUSE_END = '，；：、,;:'
    TONE_PARTICLES = '啊呢吧嘛呀哦哈嗯'
    STRUCT_PARTICLES = '的地得了着过'

    lo = max(4, target_chars - tolerance)
    hi = min(len(text), target_chars + tolerance)

    PUNCT_SET = SENTENCE_END + CLAUSE_END
    for chars in (SENTENCE_END, CLAUSE_END, TONE_PARTICLES, STRUCT_PARTICLES):
        best = None
        for pos in range(lo, hi + 1):
            if pos <= len(text) and text[pos - 1] in chars:
                # Structure particles (的/地/得) connect to the following word —
                # don't split after them unless followed by punctuation or end of text
                if chars is STRUCT_PARTICLES and pos < len(text) and text[pos] not in PUNCT_SET:
                    continue
                best = pos
        if best is not None:
            return best

    return min(target_chars, len(text))


SENTENCE_END = '。！？.!?'
CLAUSE_END = '，；：、,;:,'
SOFT_PAUSE_END = CLAUSE_END + SENTENCE_END
FORBIDDEN_FIRST_CHARS = set('的了着过吗呢吧啊呀嘛哦哈嗯')
FORBIDDEN_LAST_CHARS = set('所但因而虽并且还就才却只')
WEAK_TAIL_WORDS = {
    '我', '你', '他', '她', '它', '我们', '你们', '他们', '她们', '它们',
    '只', '就', '才', '还', '并', '且', '但', '因为', '所以', '如果',
    '一个', '这个', '那个', '的', '地', '得',
}
WEAK_HEAD_WORDS = {
    '的', '地', '得', '了', '着', '过', '吗', '呢', '吧', '啊', '呀',
    '才', '就', '并', '且', '但', '而', '所以',
}
PROTECTED_PHRASES = {
    '不配得感',
    '配得感',
    '价值投资',
    '机械工程',
    '永远',
    '足够优秀',
    '值得被爱',
    '只有足够优秀才值得被爱',
}


def _caption_text(words):
    text = ''.join(w.get('word', '') for w in words).strip()
    # Strip trailing punctuation (Chinese + ASCII) for cleaner subtitle display
    if text and text[-1] in '，。！？、；：,!?;:':
        text = text[:-1]
    return text


def _caption_from_words(words):
    return {
        'text': _caption_text(words),
        'startMs': words[0]['startMs'],
        'endMs': words[-1]['endMs'],
    }


def _caption_duration(words):
    return words[-1]['endMs'] - words[0]['startMs']


def _crosses_protected_phrase(left_text, right_text):
    window = left_text[-12:] + right_text[:12]
    left_len = len(left_text[-12:])
    for phrase in PROTECTED_PHRASES:
        start = window.find(phrase)
        if start == -1:
            continue
        end = start + len(phrase)
        if start < left_len < end:
            return True
    return False


def _has_clause_boundary(text):
    return any(ch in CLAUSE_END for ch in text)


def _needs_split(words, max_dur_ms, readable_chars, max_cps):
    text = _caption_text(words)
    chars = len(text)
    if len(words) < 2 or chars == 0:
        return False

    dur = max(1, _caption_duration(words))
    cps = chars / (dur / 1000)

    if dur > max_dur_ms:
        return True
    if cps > max_cps:
        return True
    if chars > readable_chars:
        return True
    # A long spoken clause with punctuation usually reads better as two beats,
    # but this is still a soft readability rule, not a fixed length target.
    if chars > max(20, readable_chars - 6) and _has_clause_boundary(text):
        return True
    return False


def _boundary_score(words, split_at, min_split_chars, readable_chars, max_dur_ms):
    """Score a split after words[split_at - 1]. Higher is better."""
    left_words = words[:split_at]
    right_words = words[split_at:]
    left_text = _caption_text(left_words)
    right_text = _caption_text(right_words)
    if not left_text or not right_text:
        return -10_000

    left_chars = len(left_text)
    right_chars = len(right_text)
    prev_word = left_words[-1].get('word', '')
    next_word = right_words[0].get('word', '')
    prev_char = left_text[-1]
    next_char = right_text[0]
    gap = right_words[0]['startMs'] - left_words[-1]['endMs']

    score = 0

    if prev_char in SENTENCE_END:
        score += 140
    elif prev_char in CLAUSE_END:
        score += 100
    elif gap >= 800:
        score += 85
    elif gap >= 300:
        score += 45

    if prev_word in WEAK_TAIL_WORDS:
        score -= 90
    if next_word in WEAK_HEAD_WORDS or next_char in FORBIDDEN_FIRST_CHARS:
        score -= 90
    if prev_char in FORBIDDEN_LAST_CHARS:
        score -= 90
    if _crosses_protected_phrase(left_text, right_text):
        score -= 500

    if left_chars < min_split_chars:
        score -= 160
    if right_chars < min_split_chars:
        score -= 160
    if left_chars == 1 or right_chars == 1:
        score -= 220

    left_dur = _caption_duration(left_words)
    right_dur = _caption_duration(right_words)
    if left_dur < 500:
        score -= 70
    if right_dur < 500:
        score -= 70

    if left_dur > max_dur_ms:
        score -= min(120, (left_dur - max_dur_ms) / 100)
    if right_dur > max_dur_ms:
        score -= min(120, (right_dur - max_dur_ms) / 100)

    # Prefer balanced, readable chunks without forcing a fixed character range.
    if 8 <= left_chars <= readable_chars:
        score += 20
    if 8 <= right_chars <= readable_chars:
        score += 20
    score -= abs(left_chars - right_chars) * 0.5

    return score


def _best_split_index(words, min_split_chars, readable_chars, max_dur_ms):
    if len(words) < 2:
        return None

    best_idx = None
    best_score = -10_000
    for split_at in range(1, len(words)):
        score = _boundary_score(
            words,
            split_at,
            min_split_chars=min_split_chars,
            readable_chars=readable_chars,
            max_dur_ms=max_dur_ms,
        )
        if score > best_score:
            best_score = score
            best_idx = split_at

    return best_idx


def _split_word_segment(words, max_dur_ms, min_split_chars, readable_chars, max_cps):
    pending = [words]
    chunks = []
    guard = 0

    while pending:
        current = pending.pop()
        guard += 1
        if guard > 1000:
            chunks.append(current)
            continue

        if not _needs_split(current, max_dur_ms, readable_chars, max_cps):
            chunks.append(current)
            continue

        split_at = _best_split_index(current, min_split_chars, readable_chars, max_dur_ms)
        if split_at is None:
            chunks.append(current)
            continue

        left = current[:split_at]
        right = current[split_at:]
        if not left or not right:
            chunks.append(current)
            continue

        # Stack is LIFO; push right first so output order stays natural.
        pending.append(right)
        pending.append(left)

    return chunks


def split_words_to_captions(words, max_dur_ms=8000, max_chars=60,
                            gap_threshold_ms=2000, min_dur_before_split_ms=1500,
                            clause_split_dur_ms=2000, min_split_chars=4,
                            target_chars=18, target_tolerance=8):
    """Split words into natural captions using word-boundary scoring.

    Length is a soft readability signal. The splitter keeps complete sentences
    together when they are readable, splits long compound sentences on natural
    clause/pause boundaries, and never cuts through a word or protected phrase.
    """
    if not words:
        return []

    # First pass: split at large gaps (real pauses)
    # These are hard boundaries that cannot be crossed
    gap_segments = []
    seg_start_idx = 0
    for i in range(1, len(words)):
        gap = words[i]['startMs'] - words[i - 1]['endMs']
        if gap > gap_threshold_ms:
            gap_segments.append((seg_start_idx, i))
            seg_start_idx = i
    gap_segments.append((seg_start_idx, len(words)))

    readable_chars = max(28, min(max_chars, target_chars + target_tolerance + 2))
    max_cps = 9.0

    # Second pass: within each gap-segment, split text at natural boundaries
    captions = []
    for seg_word_start, seg_word_end in gap_segments:
        seg_words = words[seg_word_start:seg_word_end]
        if not seg_words:
            continue

        if not _caption_text(seg_words):
            continue

        chunks = _split_word_segment(
            seg_words,
            max_dur_ms=max_dur_ms,
            min_split_chars=min_split_chars,
            readable_chars=readable_chars,
            max_cps=max_cps,
        )
        for chunk_words in chunks:
            cap = _caption_from_words(chunk_words)
            if cap['text']:
                captions.append(cap)

    return captions


def merge_short_captions(captions, min_dur_ms=800, max_dur_ms=8000, max_chars=60,
                         min_merge_chars=4):
    """Merge captions that are too short (by duration OR character count).

    Two passes:
    1. Duration-based: merge captions shorter than min_dur_ms with previous.
    2. Character-count-based: merge captions with fewer than min_merge_chars
       characters. Tries forward merge first, then backward merge.
    """
    if len(captions) < 2:
        return captions

    # Pass 1: Duration-based merge
    merged = [dict(captions[0])]
    for i in range(1, len(captions)):
        cap = captions[i]
        prev = merged[-1]
        cap_dur = cap['endMs'] - cap['startMs']

        if cap_dur >= min_dur_ms:
            merged.append(dict(cap))
            continue

        combined_text = prev['text'] + cap['text']
        combined_dur = cap['endMs'] - prev['startMs']

        if len(combined_text) <= max_chars and combined_dur <= max_dur_ms:
            prev['text'] = combined_text
            prev['endMs'] = cap['endMs']
        else:
            merged.append(dict(cap))

    # Pass 2: Character-count-based merge (Layer 3)
    if min_merge_chars <= 0:
        return merged

    changed = True
    merge_guard = 0
    while changed and merge_guard < 50:
        changed = False
        merge_guard += 1
        result = []
        i = 0
        while i < len(merged):
            cap = merged[i]
            text_chars = len(cap['text'])

            if text_chars < min_merge_chars:
                forward = None
                if i + 1 < len(merged):
                    next_cap = merged[i + 1]
                    combined_text = cap['text'] + next_cap['text']
                    if len(combined_text) <= max_chars:
                        forward = {
                            'text': combined_text,
                            'startMs': cap['startMs'],
                            'endMs': next_cap['endMs'],
                        }

                backward = None
                if result:
                    prev = result[-1]
                    combined_text = prev['text'] + cap['text']
                    if len(combined_text) <= max_chars:
                        backward = {
                            'text': combined_text,
                            'startMs': prev['startMs'],
                            'endMs': cap['endMs'],
                        }

                if forward or backward:
                    forward_score = 0
                    backward_score = 0

                    if forward:
                        next_text = merged[i + 1]['text'] if i + 1 < len(merged) else ''
                        if cap['text'] and cap['text'][0] in FORBIDDEN_FIRST_CHARS:
                            forward_score -= 40
                        if next_text and next_text[0] in FORBIDDEN_FIRST_CHARS:
                            forward_score += 20

                    if backward:
                        prev_text = result[-1]['text']
                        if prev_text and prev_text[-1] not in SENTENCE_END:
                            backward_score += 35
                        if cap['text'] and cap['text'][-1] in SENTENCE_END:
                            backward_score += 25
                        if _crosses_protected_phrase(prev_text, cap['text']):
                            backward_score += 80

                    if backward and (not forward or backward_score >= forward_score):
                        result[-1] = backward
                        i += 1
                        changed = True
                        continue

                    if forward:
                        result.append(forward)
                        i += 2
                        changed = True
                        continue

            result.append(dict(cap))
            i += 1
        merged = result

    return merged


def make_relative(captions, clip_start_ms, clip_end_ms=None):
    """Convert absolute timestamps to 0-based relative to clip start."""
    result = []
    for i, s in enumerate(captions):
        start_ms = max(0, s['startMs'] - clip_start_ms)
        end_ms = max(0, s['endMs'] - clip_start_ms)
        if clip_end_ms is not None:
            max_end = max(0, clip_end_ms - clip_start_ms)
            start_ms = min(start_ms, max_end)
            end_ms = min(end_ms, max_end)
        if end_ms <= start_ms:
            continue
        result.append({
            'text': s['text'],
            'startMs': start_ms,
            'endMs': end_ms,
            'index': len(result),
        })
    return result


def _is_valid_captions(out_path: Path, captions_data: list, highlight: dict) -> bool:
    """Check if existing timeline_captions.json is valid and likely matches source data."""
    if not out_path.exists() or out_path.stat().st_size == 0:
        return False
    try:
        existing = json.loads(out_path.read_text(encoding='utf-8'))
        # Support both old format (plain list) and new format (dict with captions key)
        caps = existing.get('captions', existing) if isinstance(existing, dict) else existing
        if not isinstance(caps, list) or len(caps) == 0:
            return False
        # Check timestamps are monotonically increasing
        for i in range(1, len(caps)):
            if caps[i].get('startMs', 0) < caps[i-1].get('startMs', 0):
                return False
        return True
    except (json.JSONDecodeError, OSError, KeyError):
        return False


def _get_captions_list(data) -> list:
    """Extract captions list from either old or new format."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get('captions', data.get('items', []))
    return []


def split_text_to_sentences(text: str, min_chars: int = 4) -> list[str]:
    """Split text into sentences at natural punctuation boundaries.

    Splits on sentence-end punctuation first (。！？.!?),
    then on clause-end punctuation (，；：、,;:) if segments are too long.
    """
    import re
    # Split on sentence-end punctuation, keeping the punctuation
    parts = re.split(r'((?<=[。！？.!?])[）)》」』]?)', text)
    segments = []
    current = ''
    for part in parts:
        current += part
        if part and part[-1] in '。！？.!?）)》」』':
            stripped = current.strip()
            if stripped:
                segments.append(stripped)
            current = ''
    if current.strip():
        segments.append(current.strip())

    # Further split overly long segments at clause boundaries
    result = []
    for seg in segments:
        if len(seg) <= 60:
            result.append(seg)
            continue
        # Split at commas/semicolons
        sub_parts = re.split(r'((?<=[，；：、,;:])[）)》」』]?)', seg)
        current = ''
        for sp in sub_parts:
            current += sp
            if len(current) >= 20 and current[-1] in '，；：、,;:）)》」』':
                stripped = current.strip()
                if stripped:
                    result.append(stripped)
                current = ''
        if current.strip():
            result.append(current.strip())

    # Merge tiny fragments back into previous segment
    merged = []
    for seg in result:
        if merged and len(seg) < min_chars:
            merged[-1] += seg
        else:
            merged.append(seg)
    return merged if merged else [text]


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Split an over-long sentence at internal clause punctuation.

    Splits after clause punctuation (，、；,;：:) so each piece stays a readable
    clause. Pieces accumulate until adding the next would exceed max_chars and
    the current piece is already >= 4 chars. A piece with no clause punctuation
    stays intact even if long — splitting mid-clause reads worse than a long line.
    """
    import re
    if len(sentence) <= max_chars:
        return [sentence]
    parts = re.split(r'(?<=[，、；,;：:])', sentence)
    pieces: list[str] = []
    current = ''
    for p in parts:
        candidate = current + p
        if current and len(current) >= 4 and len(candidate) > max_chars:
            pieces.append(current)
            current = p
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces if pieces else [sentence]


def align_tts_script_captions(tts_script: str, words: list[dict],
                              max_chars: int = 40, max_dur_ms: int = 6000,
                              min_coverage: float = 0.95) -> list[dict] | None:
    """Split tts_script by its own punctuation and align to word timestamps.

    tts_script is the AI-rewritten, punctuated spoken text — its punctuation is
    the authoritative sentence boundary. Splits on that punctuation (reusing
    split_text_to_sentences), refines over-long sentences at clause punctuation,
    then maps each sentence onto Whisper word timestamps via
    lib.caption_align.map_sentences. Caption text is the clean tts_script text
    (no ASR typos).

    Returns None when alignment coverage < min_coverage so the caller falls back
    to algorithmic splitting (split_words_to_captions). max_dur_ms is accepted
    for API symmetry; per-sentence duration gating is left to caller stats.
    """
    import re
    text = re.sub(r'\s+', '', tts_script)
    if not text or not words:
        return None

    sentences = split_text_to_sentences(text, min_chars=4)
    refined: list[str] = []
    for s in sentences:
        refined.extend(_split_long_sentence(s, max_chars))

    captions = align_sentences_to_words(refined, words)
    if not captions:
        return None

    coverage = verify_coverage(captions, words)
    if coverage < min_coverage:
        return None

    return captions


def generate_synthetic_captions(text: str, audio_duration_ms: float,
                                gap_ms: int = 200, min_chars: int = 4) -> list[dict]:
    """Generate captions with synthetic timing from text + audio duration.

    Splits text into sentences, then distributes time proportionally
    by character count with small gaps between captions.
    """
    sentences = split_text_to_sentences(text, min_chars=min_chars)
    if not sentences:
        return []

    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return []

    # Reserve gap time
    total_gap_ms = gap_ms * max(0, len(sentences) - 1)
    available_ms = max(0, audio_duration_ms - total_gap_ms)

    captions = []
    current_ms = 0.0
    for i, sent in enumerate(sentences):
        char_ratio = len(sent) / total_chars
        dur_ms = available_ms * char_ratio
        start_ms = round(current_ms)
        end_ms = round(current_ms + dur_ms)
        if end_ms <= start_ms:
            end_ms = start_ms + 100
        captions.append({
            'text': sent,
            'startMs': start_ms,
            'endMs': end_ms,
            'index': i,
            'timing_source': 'tts_synthetic',
        })
        current_ms = end_ms + gap_ms

    # Clamp last caption end to audio duration
    if captions and captions[-1]['endMs'] > audio_duration_ms:
        captions[-1]['endMs'] = round(audio_duration_ms)

    return captions


def _extract_all_words(whisper_segments):
    """Extract and flatten all words from Whisper segment output.

    Unlike get_words_in_range (which clips to a range), this takes all words
    since the Whisper output is already per-clip.
    """
    words = []
    for seg in whisper_segments:
        for w in seg.get('words', []):
            ws = w.get('startMs')
            we = w.get('endMs')
            if ws is None or we is None:
                continue
            if we > ws:
                words.append({'word': w.get('word', ''), 'startMs': ws, 'endMs': we})
    words.sort(key=lambda w: w['startMs'])
    seen = set()
    unique = []
    for w in words:
        key = (w['startMs'], w['word'])
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def _run_whisper_aligned_mode(args, project_dir: Path):
    """Handle --whisper-json mode: use Whisper word timestamps for accurate alignment."""
    whisper_path = Path(args.whisper_json)
    if not whisper_path.exists():
        print(f'ERROR: --whisper-json file not found: {whisper_path}', file=sys.stderr)
        sys.exit(1)

    whisper_data = load_json(whisper_path)
    segments = _get_captions_list(whisper_data) if isinstance(whisper_data, dict) else whisper_data
    if not segments:
        print(f'ERROR: No segments in {whisper_path}', file=sys.stderr)
        sys.exit(1)

    highlights = load_json(project_dir / 'highlights' / 'final_highlights.json')
    target_ids = [args.highlight_id] if args.highlight_id else [h['id'] for h in highlights]

    for hid in target_ids:
        hl = next((h for h in highlights if h['id'] == hid), None)
        if not hl:
            print(f'  H{hid:02d}: SKIP (highlight not found)')
            continue

        out_dir = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio'
        out_path = out_dir / 'timeline_captions.json'
        if not args.force and _is_valid_captions(out_path, [], hl):
            print(f'  H{hid:02d}: SKIP (valid output exists, use --force to regenerate)')
            continue

        words = _extract_all_words(segments)
        if not words:
            print(f'  H{hid:02d}: SKIP (no words in Whisper output)')
            continue

        words = smooth_inter_segment_gaps(words)
        words = compress_stretched_words(words, max_ms_per_char=args.max_ms_per_char)

        # Save word-level data
        relative_words = make_relative(
            [{'text': w['word'], 'startMs': w['startMs'], 'endMs': w['endMs']} for w in words],
            0,
        )

        # Primary: align tts_script punctuation to word timestamps. Falls back
        # to algorithmic splitting when tts_script is absent or coverage is low.
        tts_script = (hl.get('tts_script') or '').replace('\r', '')
        captions = None
        timing_source = 'whisper_aligned'
        if args.tts_script_align and tts_script:
            captions = align_tts_script_captions(
                tts_script, words,
                max_chars=args.max_caption_chars,
                max_dur_ms=args.max_duration,
            )
            if captions is not None:
                timing_source = 'tts_script_aligned'
            else:
                print(f'  H{hid:02d}: tts_script align skipped (absent/low coverage), using algorithmic')

        if captions is None:
            captions = split_words_to_captions(
                words,
                max_dur_ms=args.max_duration,
                gap_threshold_ms=args.gap_threshold,
                min_dur_before_split_ms=args.sentence_split_dur,
                clause_split_dur_ms=args.clause_split_dur,
                min_split_chars=args.min_split_chars,
            )
            captions = merge_short_captions(
                captions,
                min_dur_ms=500,
                max_dur_ms=args.max_duration,
                min_merge_chars=args.min_merge_chars,
            )

        relative = make_relative(captions, 0)

        audio_path = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio' / 'clip.mp3'
        audio_dur = probe_duration(audio_path) if audio_path.exists() else 0.0

        out_dir.mkdir(parents=True, exist_ok=True)
        output_data = {
            'audio_duration_seconds': round(audio_dur, 3) if audio_dur > 0 else None,
            'timing_source': timing_source,
            'captions': relative,
        }
        save_json(output_data, out_path)

        words_data = {
            'audio_duration_seconds': round(audio_dur, 3) if audio_dur > 0 else None,
            'timing_source': 'whisper_aligned',
            'raw_text': ''.join(w.get('text', '') for w in relative_words),
            'words': relative_words,
        }
        words_out_path = out_dir / 'words.json'
        save_json(words_data, words_out_path)

        if relative:
            durs = [(c['endMs'] - c['startMs']) / 1000 for c in relative]
            total_covered = sum(durs)
            total_audio_ms = relative[-1]['endMs']
            coverage_pct = (total_covered / (total_audio_ms / 1000) * 100) if total_audio_ms > 0 else 0
            dur_str = f', ffprobe={audio_dur:.2f}s' if audio_dur > 0 else ''
            print(f'  H{hid:02d}: {len(relative)} caps ({timing_source}), '
                  f'{total_audio_ms/1000:.1f}s audio{dur_str}, {total_covered:.1f}s covered ({coverage_pct:.1f}%)')
        else:
            print(f'  H{hid:02d}: EMPTY')


def _run_synthetic_mode(args, project_dir: Path):
    """Handle --synthetic-timing mode for TTS-generated audio."""
    highlights = load_json(project_dir / 'highlights' / 'final_highlights.json')
    target_ids = [args.highlight_id] if args.highlight_id else [h['id'] for h in highlights]

    for hid in target_ids:
        hl = next((h for h in highlights if h['id'] == hid), None)
        if not hl:
            print(f'  H{hid:02d}: SKIP (highlight not found)')
            continue

        # Resolve audio path
        if args.audio:
            audio_path = Path(args.audio)
        else:
            audio_path = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio' / 'clip.mp3'
        if not audio_path.exists():
            print(f'  H{hid:02d}: SKIP (audio not found: {audio_path})')
            continue

        # Resolve text: prefer tts_script (matches actual audio), fall back to text
        text = args.text if args.text else hl.get('tts_script') or hl.get('text', '')
        if not text:
            print(f'  H{hid:02d}: SKIP (no text)')
            continue

        # Idempotency check
        out_dir = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio'
        out_path = out_dir / 'timeline_captions.json'
        if not args.force and _is_valid_captions(out_path, [], hl):
            print(f'  H{hid:02d}: SKIP (valid output exists)')
            continue

        audio_dur = probe_duration(audio_path)
        if audio_dur <= 0:
            print(f'  H{hid:02d}: SKIP (audio duration = 0)')
            continue

        captions = generate_synthetic_captions(text, audio_dur * 1000)

        out_dir.mkdir(parents=True, exist_ok=True)
        output_data = {
            'audio_duration_seconds': round(audio_dur, 3),
            'timing_source': 'tts_synthetic',
            'captions': captions,
        }
        save_json(output_data, out_path)

        # Save words.json for AI caption refinement
        words_data = {
            'audio_duration_seconds': round(audio_dur, 3),
            'timing_source': 'tts_synthetic',
            'raw_text': text,
            'words': [{'text': c['text'], 'startMs': c['startMs'], 'endMs': c['endMs']}
                      for c in captions],
        }
        words_out_path = out_dir / 'words.json'
        save_json(words_data, words_out_path)

        total = sum(c['endMs'] - c['startMs'] for c in captions)
        print(f'  H{hid:02d}: {len(captions)} caps (synthetic), '
              f'{audio_dur:.1f}s audio, {total/1000:.1f}s covered '
              f'({total / (audio_dur * 1000) * 100:.1f}%)')


def main():
    setup_windows_encoding()
    parser = argparse.ArgumentParser(description='Generate timeline_captions.json')
    parser.add_argument('--project-dir', required=True, help='Project directory')
    parser.add_argument('--highlight-id', type=int, help='Specific highlight ID, or omit for all')
    parser.add_argument('--max-duration', type=int, default=6000, help='Max caption duration ms')
    parser.add_argument('--gap-threshold', type=int, default=1500, help='Gap threshold ms for splitting')
    parser.add_argument('--clause-split-dur', type=int, default=500, help='Min accumulated ms before splitting at clause punctuation')
    parser.add_argument('--sentence-split-dur', type=int, default=300, help='Min accumulated ms before splitting at sentence punctuation')
    parser.add_argument('--max-ms-per-char', type=int, default=1500,
                        help='Max ms per character before treating word as stretched')
    parser.add_argument('--min-split-chars', type=int, default=4,
                        help='Min chars for a standalone caption after hard-limit split')
    parser.add_argument('--min-merge-chars', type=int, default=4,
                        help='Merge captions with fewer chars than this')
    parser.add_argument('--force', action='store_true',
                        help='Force regeneration even if valid output exists')
    parser.add_argument('--no-tts-script-align', dest='tts_script_align',
                        action='store_false', default=True,
                        help='Disable tts_script punctuation alignment; use algorithmic splitting only')
    parser.add_argument('--max-caption-chars', dest='max_caption_chars',
                        type=int, default=40,
                        help='Max chars per caption before splitting at clause punctuation (default: 40)')
    # Synthetic timing mode (for TTS-generated audio without word-level timestamps)
    parser.add_argument('--synthetic-timing', action='store_true',
                        help='Use synthetic timing from text + audio duration instead of word timestamps')
    # Whisper-aligned mode (for TTS audio with Whisper transcription)
    parser.add_argument('--whisper-json', default=None,
                        help='Path to Whisper segments JSON with word-level timestamps')
    parser.add_argument('--audio', default=None,
                        help='Audio file path (synthetic mode: for duration probing)')
    parser.add_argument('--text', default=None,
                        help='Inline text for caption generation (synthetic mode; falls back to highlight text)')
    parser.add_argument('--padding-ms', type=int, default=100,
                        help='Padding (ms) applied to clip bounds when clips.json lacks clip_start_ms/clip_end_ms. Must match the padding used by the audio cutter (cut-original default 100) to keep audio and captions aligned (default: 100)')
    args = parser.parse_args()

    if args.synthetic_timing and args.whisper_json:
        parser.error('--synthetic-timing and --whisper-json are mutually exclusive')

    project_dir = Path(args.project_dir)

    if args.synthetic_timing:
        _run_synthetic_mode(args, project_dir)
        return

    if args.whisper_json:
        _run_whisper_aligned_mode(args, project_dir)
        return

    project_dir = Path(args.project_dir)
    captions_data = load_json(project_dir / 'captions' / 'captions.json')
    highlights = load_json(project_dir / 'highlights' / 'final_highlights.json')
    clips = load_json(project_dir / 'clips' / 'clips.json')

    # Build clip lookup (support both 'id' and 'highlight_id' field names)
    clip_map = {c.get('id', c.get('highlight_id')): c for c in clips}

    target_ids = [args.highlight_id] if args.highlight_id else [h['id'] for h in highlights]

    for hid in target_ids:
        hl = next((h for h in highlights if h['id'] == hid), None)
        clip = clip_map.get(hid)
        if not hl or not clip:
            print(f'  H{hid:02d}: SKIP (missing data)')
            continue

        # Idempotency check: skip if valid output already exists
        out_dir = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio'
        out_path = out_dir / 'timeline_captions.json'
        if not args.force and _is_valid_captions(out_path, captions_data, hl):
            print(f'  H{hid:02d}: SKIP (valid output exists, use --force to regenerate)')
            continue

        clip_start = clip.get('clip_start_ms', hl.get('start_ms', 0) - args.padding_ms)
        clip_end = clip.get('clip_end_ms', hl.get('end_ms', 0) + args.padding_ms)
        words = get_words_in_range(
            captions_data,
            hl.get('start_ms', 0),
            hl.get('end_ms', 0),
            clip_start,
            clip_end,
        )

        words = smooth_inter_segment_gaps(words)
        words = compress_stretched_words(
            words,
            max_ms_per_char=args.max_ms_per_char,
        )

        if not words:
            print(f'  H{hid:02d}: SKIP (no words found)')
            continue

        # Save word-level data for AI caption refinement
        relative_words = make_relative(
            [{'text': w['word'], 'startMs': w['startMs'], 'endMs': w['endMs']} for w in words],
            clip_start, clip_end,
        )
        words_out_dir = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio'
        words_out_dir.mkdir(parents=True, exist_ok=True)
        words_out_path = words_out_dir / 'words.json'

        captions = split_words_to_captions(
            words,
            max_dur_ms=args.max_duration,
            gap_threshold_ms=args.gap_threshold,
            min_dur_before_split_ms=args.sentence_split_dur,
            clause_split_dur_ms=args.clause_split_dur,
            min_split_chars=args.min_split_chars,
        )

        captions = merge_short_captions(captions, min_dur_ms=500, max_dur_ms=args.max_duration,
                                        min_merge_chars=args.min_merge_chars)

        relative = make_relative(captions, clip_start, clip_end)

        # Probe actual audio duration for accurate data-duration
        audio_path = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio' / 'clip.mp3'
        audio_dur = probe_duration(audio_path) if audio_path.exists() else 0.0

        # Save in new format with audio_duration_seconds
        out_dir = project_dir / 'video' / f'highlight_{hid:03d}' / 'audio'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'timeline_captions.json'
        output_data = {
            'audio_duration_seconds': round(audio_dur, 3) if audio_dur > 0 else None,
            'captions': relative,
        }
        save_json(output_data, out_path)

        # Save words.json for AI caption refinement
        words_data = {
            'audio_duration_seconds': round(audio_dur, 3) if audio_dur > 0 else None,
            'raw_text': ''.join(w.get('text', '') for w in relative_words),
            'words': relative_words,
        }
        save_json(words_data, words_out_path)

        # Stats
        if relative:
            durs = [(c['endMs'] - c['startMs']) / 1000 for c in relative]
            gaps = [(relative[j+1]['startMs'] - relative[j]['endMs']) / 1000
                    for j in range(len(relative) - 1)]
            total_covered = sum(durs)
            total_audio_ms = relative[-1]['endMs']
            coverage_pct = (total_covered / (total_audio_ms / 1000) * 100) if total_audio_ms > 0 else 0
            short_count = sum(1 for d in durs if d < 0.8)
            long_count = sum(1 for d in durs if d > 8)
            max_gap_str = f'{max(gaps):.1f}s' if gaps else 'N/A'
            max_gap_idx = gaps.index(max(gaps)) if gaps else -1
            dur_str = f', ffprobe={audio_dur:.2f}s' if audio_dur > 0 else ''
            print(f'  H{hid:02d}: {len(relative)} caps, '
                  f'{total_audio_ms/1000:.1f}s audio{dur_str}, {total_covered:.1f}s covered ({coverage_pct:.1f}%)')
            print(f'         max_dur={max(durs):.1f}s, max_gap={max_gap_str}'
                  f'{f" (idx {max_gap_idx}→{max_gap_idx+1})" if max_gap_idx >= 0 else ""}, '
                  f'short={short_count}, long={long_count}')
        else:
            print(f'  H{hid:02d}: EMPTY')


if __name__ == '__main__':
    main()

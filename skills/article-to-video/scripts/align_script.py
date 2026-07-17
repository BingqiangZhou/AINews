#!/usr/bin/env python3
"""
align_script.py — 阶段 2：脚本原文对齐 Whisper 时间戳

把播客脚本（_podcast/播客_脚本.txt，**正确文本**）按句切分，
用 caption_align.align_sentences_to_words 对齐到 Phase 1 产出的
whisper_segments.json 的 word-level 时间戳，得到「正确文本 + 精准时间戳」
的 captions，存入 _video/temp/captions_corrected.json。

为什么需要这一步：
  Phase 1 的 timeline_captions.json 是 Whisper 重新转录音频的结果，
  文本带有 ASR 错字（如「月之岸面」应为「月之暗面」）。
  而播客脚本是写作时的权威原文。本步用脚本文本替换 Whisper 文本，
  同时复用 Whisper 的 word-level 时间戳（经字符级 DP 对齐），
  让字幕既正确又跟得上口播。

同时产出 section 时间轴的「正确文本」版本（从脚本里的 [SECTION:xxx]
标记切分，配对到 sections_timeline.json 的 section 时间戳），供 Phase 3
plan_scenes 读取 section 的标题/关键词/起止时间。

Usage:
  python align_script.py --article-dir <文章目录>
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import setup_windows_encoding, read_json, write_json, resolve_podcast_path  # noqa: E402
from lib.caption_align import align_sentences_to_words, verify_coverage, normalize  # noqa: E402

# [SECTION:xxx] 标记，xxx 可以是 OPENING / 数字 / DEEPDIVE / ENDING
SECTION_RE = re.compile(r"^\[SECTION:([^\]]+)\]\s*$", re.MULTILINE)


def split_into_sentences(text: str) -> list[str]:
    """把播客脚本按句切分（中文句号/问号/叹号 + 换行）。

    保留原文标点。空句跳过。[SECTION:xxx] 标记单独返回（不混入句子）。
    """
    # 先剥离 section 标记行（单独处理），避免它们被当句子
    cleaned = SECTION_RE.sub("", text)
    # 按句末标点切分（。！？），保留标点
    parts = re.split(r"(?<=[。！？])", cleaned)
    # 再按换行细分（脚本里一行常是一句口播）
    sentences: list[str] = []
    for part in parts:
        for line in part.split("\n"):
            line = line.strip()
            if not line:
                continue
            sentences.append(line)
    return sentences


def parse_sections(script_text: str) -> list[dict]:
    """解析脚本的 [SECTION:xxx] 结构。

    Returns:
        [{"index": "OPENING"|"1"|...|"DEEPDIVE", "lines": [句子...], "raw": 段落原文}, ...]
    """
    # 找所有标记位置
    marks = list(SECTION_RE.finditer(script_text))
    if not marks:
        return []
    sections = []
    for i, m in enumerate(marks):
        sec_idx = m.group(1).strip()
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(script_text)
        body = script_text[start:end].strip()
        sections.append({
            "index": sec_idx,
            "raw": body,
            "lines": [ln.strip() for ln in body.split("\n") if ln.strip()],
        })
    return sections


def collect_words(whisper_segments: list[dict]) -> list[dict]:
    """把 whisper_segments.json 各 segment 的 words 拼成单一 word 列表。"""
    words: list[dict] = []
    for seg in whisper_segments:
        seg_words = seg.get("words") or []
        for w in seg_words:
            # caption_align 期望 word/startMs/endMs 键
            wt = w.get("word") or w.get("text") or ""
            if not wt:
                continue
            words.append({
                "word": wt,
                "startMs": w.get("startMs", 0),
                "endMs": w.get("endMs", 0),
            })
    return words


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(
        description="阶段 2：脚本原文对齐 Whisper 时间戳 → captions_corrected.json"
    )
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    video_dir = article_dir / "_video"
    temp_dir = video_dir / "temp"

    # 输入校验
    whisper_path = temp_dir / "whisper_segments.json"
    if not whisper_path.exists():
        print("ERROR: whisper_segments.json 不存在，请先运行阶段 1（align_captions.py）",
              file=sys.stderr)
        sys.exit(1)
    script_path = resolve_podcast_path(article_dir, "播客_脚本.txt")
    if not script_path.exists():
        print("ERROR: 播客_脚本.txt 不存在（已查找 _podcast/ 与文章根目录）",
              file=sys.stderr)
        sys.exit(1)

    # 1. 读取 whisper word-level 数据
    whisper_segments = read_json(whisper_path)
    words = collect_words(whisper_segments)
    if not words:
        print("ERROR: whisper_segments.json 无 word-level 数据", file=sys.stderr)
        sys.exit(1)
    print(f"  [align_script] Whisper words: {len(words)} 个")

    # 2. 读播客脚本，按句切分
    script_text = script_path.read_text(encoding="utf-8").replace("\r", "")
    sentences = split_into_sentences(script_text)
    print(f"  [align_script] 脚本句子: {len(sentences)} 句")

    # 3. 字符级 DP 对齐：正确句子文本 → Whisper word 时间戳
    captions = align_sentences_to_words(sentences, words)
    if not captions:
        print("ERROR: 句子对齐失败（脚本文本与 Whisper 转录差异过大）", file=sys.stderr)
        sys.exit(1)
    print(f"  [align_script] 对齐成功: {len(captions)} 条字幕")

    # 4. 覆盖率校验
    coverage = verify_coverage(captions, words)
    print(f"  [align_script] 时间戳覆盖率: {coverage * 100:.1f}%")
    if coverage < 0.85:
        print(f"  [align_script] WARNING: 覆盖率偏低 ({coverage*100:.1f}%)，"
              f"部分句子可能未对齐到时间戳", file=sys.stderr)

    # 5. 解析脚本 section 结构（供 Phase 3 用）
    sections = parse_sections(script_text)

    # 6. 为每个 section 配准时间戳：用 section 首句在 captions_corrected 里查实际口播时间。
    #    【关键】不依赖 Phase 1 的 sections_timeline.json——它的 section char_start 偏移
    #    在 DEEPDIVE/ENDING 等节严重错位（solo_tts 生成 sections.json 时 section 边界
    #    算错，把标记前内容算进了下一节），导致 DEEPDIVE 时间戳早了 150+ 秒（音画不同步）。
    #    captions_corrected 的每句都有经字符级 DP 对齐的精准时间戳，用首句查找更可靠。
    audio_dur_ms = int((read_json(temp_dir / "timeline_captions.json").get(
        "audio_duration_seconds") or 0) * 1000) if (temp_dir / "timeline_captions.json").exists() else 0

    sec_starts: list[tuple[int, str]] = []  # (caption_index, section_list_index)
    for si, sec in enumerate(sections):
        first_line = sec["lines"][0] if sec.get("lines") else ""
        # 用首句前若干字符做归一化锚点匹配
        anchor = normalize(first_line)[:18]
        cap_idx = None
        if anchor:
            for ci, c in enumerate(captions):
                if anchor in normalize(c.get("text", "")):
                    cap_idx = ci
                    break
        # 回退：首句未匹配（如 section 标题是「一、大模型...」口播可能略不同），
        # 用首句更短前缀
        if cap_idx is None and len(first_line) > 4:
            short_anchor = normalize(first_line)[:8]
            for ci, c in enumerate(captions):
                if short_anchor in normalize(c.get("text", "")):
                    cap_idx = ci
                    break
        sec_starts.append((cap_idx, si))

    # 每个 section 的 start_ms = 其首句 caption 的 startMs；
    # end_ms = 下一个 section 的 start_ms（首尾相接）；最后一个 end = 音频结束。
    # 首句未匹配的 section：start = 前一节 end（兜底）。
    sections_with_time = []
    prev_end_ms = 0
    for si, sec in enumerate(sections):
        idx = sec["index"]
        cap_idx = sec_starts[si][0]
        if cap_idx is not None:
            start_ms = int(captions[cap_idx].get("startMs", prev_end_ms))
        else:
            start_ms = prev_end_ms
            print(f"  [align_script] WARNING: section [{idx}] 首句未匹配到字幕，"
                  f"用前节 end {start_ms}ms 兜底", file=sys.stderr)
        # 不倒退（若首句时间早于上节，钳到上节 end）
        if start_ms < prev_end_ms:
            start_ms = prev_end_ms
        # end_ms = 下一节 start（若有），否则音频结束
        if si + 1 < len(sections):
            next_cap_idx = sec_starts[si + 1][0]
            if next_cap_idx is not None:
                end_ms = int(captions[next_cap_idx].get("startMs", start_ms))
            else:
                end_ms = audio_dur_ms
        else:
            end_ms = audio_dur_ms
        if end_ms <= start_ms:
            end_ms = start_ms + 1000
        sections_with_time.append({
            "index": idx,
            "title": sec["lines"][0] if sec["lines"] else idx,
            "raw": sec["raw"],
            "lines": sec["lines"],
            "start_ms": start_ms,
            "end_ms": end_ms,
        })
        prev_end_ms = end_ms

    output = {
        "audio_duration_seconds": read_json(
            temp_dir / "timeline_captions.json"
        ).get("audio_duration_seconds") if (temp_dir / "timeline_captions.json").exists() else None,
        "source": "podcast_script_aligned_to_whisper",
        "coverage": round(coverage, 4),
        "sentence_count": len(sentences),
        "caption_count": len(captions),
        "captions": captions,
        "sections": sections_with_time,
    }

    out_path = temp_dir / "captions_corrected.json"
    write_json(output, out_path)
    print(f"  [align_script] → {out_path.name} "
          f"({len(captions)} 字幕, {len(sections_with_time)} section)")


if __name__ == "__main__":
    main()

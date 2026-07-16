#!/usr/bin/env python3
"""
align_captions.py — 阶段 1：字幕对齐

对播客 TTS 音频做 Whisper word-level 转录，再用 caption_align 库把播客脚本
对齐到 word 时间戳，产出 timeline_captions.json。

复用（只读，不修改）：
  - whisper-transcribe/scripts/transcribe-faster-whisper.py（subprocess）
  - 本 skill scripts/lib/caption_align.py（import，内化自 highlight-render-hyperframes）
  - 本 skill scripts/lib/utils.py（import，内化自 highlight-render-hyperframes）
  - 本 skill scripts/generate-timeline-captions.py 的底层函数（importlib，内化自 highlight-render-hyperframes）

Usage:
  python align_captions.py --article-dir <文章目录> [--force]
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_SKILLS = SKILL_DIR.parent  # skills/
SCRIPTS_DIR = Path(__file__).resolve().parent  # 本 skill scripts/

WHISPER_SCRIPT = REPO_SKILLS / "whisper-transcribe" / "scripts" / "transcribe-faster-whisper.py"
GTC_PATH = SCRIPTS_DIR / "generate-timeline-captions.py"

# lib.* 已内化至本 skill scripts/lib/，加入 sys.path 使其可 import
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import (  # noqa: E402
    setup_windows_encoding,
    read_json,
    write_json,
    probe_duration,
    resolve_podcast_path,
)
from lib.caption_align import align_sentences_to_words, verify_coverage, normalize  # noqa: E402


# ── importlib 加载 generate-timeline-captions.py（文件名带连字符）────────

def _load_gtc_module():
    """用 importlib 从绝对路径加载 generate-timeline-captions.py。"""
    spec = importlib.util.spec_from_file_location("gtc", str(GTC_PATH))
    mod = importlib.util.module_from_spec(spec)
    # 该模块在顶层会执行 import，但 main() 只在 __main__ 下跑，安全
    spec.loader.exec_module(mod)
    return mod


GTC = _load_gtc_module()


# ── 核心逻辑 ──────────────────────────────────────────────────────────────

def run_whisper(audio_path: Path, output_path: Path, config: dict) -> Path:
    """调用 whisper-transcribe 转录音频 → whisper_segments.json。"""
    wh = config.get("whisper", {})
    py = os.environ.get("AINews_PYTHON") or config["environment"]["conda_python"]

    cmd = [
        py, str(WHISPER_SCRIPT),
        str(audio_path),
        "--output", str(output_path),
        "--model", wh.get("model", "large-v3-turbo"),
        "--lang", wh.get("lang", "zh"),
        "--device", wh.get("device", "cuda"),
    ]
    print(f"  [whisper] 转录 {audio_path.name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Whisper 转录失败 (exit {result.returncode})")
    if not output_path.exists():
        raise RuntimeError(f"Whisper 输出文件未生成: {output_path}")
    print(f"  [whisper] 完成 → {output_path.name}")
    return output_path


def align_captions(whisper_json: Path, tts_script_path: Path,
                   audio_path: Path, output_path: Path) -> dict:
    """
    复用 generate-timeline-captions.py 的底层函数，把播客脚本对齐到
    Whisper word 时间戳 → timeline_captions.json。

    不依赖 highlight 项目结构（final_highlights.json / clips.json），
    只调用纯函数。
    """
    # 1. 加载 Whisper segments
    whisper_data = read_json(whisper_json)
    segments = (whisper_data if isinstance(whisper_data, list)
                else whisper_data.get("captions", whisper_data.get("items", [])))
    if not segments:
        raise RuntimeError(f"Whisper segments 为空: {whisper_json}")

    # 2. 扁平化 + 清洗 words（全部是纯函数）
    words = GTC._extract_all_words(segments)
    if not words:
        raise RuntimeError("Whisper 输出中无 word-level 时间戳")
    words = GTC.smooth_inter_segment_gaps(words)
    words = GTC.compress_stretched_words(words, max_ms_per_char=1500)
    print(f"  [align] words: {len(words)} 个")

    # 3. 主路径：用播客脚本（带标点）对齐。
    # 优先读 script_clean.txt（solo_tts 剥离 [SECTION] 标记后的纯文本，与 TTS 音频
    # 完全一致）；无则回退到原始脚本（可能含 [SECTION] 标记，需手工容忍）。
    clean_script_path = tts_script_path.parent / "temp" / "script_clean.txt"
    if clean_script_path.exists():
        tts_script = clean_script_path.read_text(encoding="utf-8").replace("\r", "")
    else:
        tts_script = tts_script_path.read_text(encoding="utf-8").replace("\r", "")
    captions = None
    timing_source = "whisper_aligned"

    if tts_script.strip():
        # min_coverage 放宽到 0.80：中英混读 TTS 的 Whisper 转录有较高字符错误率
        # （英文词 skill→sk+ill、同音字 掌舵→长度 等），0.95 过严会全盘丢弃脚本
        # 对齐结果、回退到无标点的纯算法切分（句中/词中断句）。0.80 让大部分能
        # 对齐的句子保留（DP 对齐本身鲁棒，部分句子失败不等于全失败）。
        captions = GTC.align_tts_script_captions(
            tts_script, words, max_chars=40, max_dur_ms=6000, min_coverage=0.80,
        )
        if captions is not None:
            timing_source = "tts_script_aligned"
            print(f"  [align] tts_script 对齐成功 (coverage ≥ 0.80)")
        else:
            print(f"  [align] tts_script 对齐 coverage 不足，回退算法切分")

    # 4. 回退：纯算法切分
    if captions is None:
        captions = GTC.split_words_to_captions(
            words, max_dur_ms=6000, gap_threshold_ms=1500,
        )
        captions = GTC.merge_short_captions(
            captions, min_dur_ms=500, max_dur_ms=6000, min_merge_chars=4,
        )

    if not captions:
        raise RuntimeError("字幕对齐失败：captions 为空")

    # 5. 整段音频 → clip_start=0（make_relative 仅加 index 字段）
    relative = GTC.make_relative(captions, 0)

    # 6. 量音频时长
    audio_dur = probe_duration(audio_path)

    output_data = {
        "audio_duration_seconds": round(audio_dur, 3) if audio_dur > 0 else None,
        "timing_source": timing_source,
        "captions": relative,
    }
    write_json(output_data, output_path)

    # 统计报告
    total_ms = relative[-1]["endMs"] if relative else 0
    covered_ms = sum(c["endMs"] - c["startMs"] for c in relative)
    print(f"  [align] {len(relative)} 条字幕, {total_ms/1000:.1f}s 音频, "
          f"{covered_ms/1000:.1f}s 覆盖 ({covered_ms/max(total_ms,1)*100:.1f}%), "
          f"source={timing_source}")

    return output_data


# ── Section 时间轴映射（按插图分段）───────────────────────────────────────

def map_sections_to_timeline(
    clean_script: str,
    sections: list[dict],
    words: list[dict],
) -> list[dict]:
    """把 sections 的字符偏移（基于 clean_script）映射成音频时间戳。

    复用 caption_align.build_char_index 构建 word 侧的 normalized char→word 索引，
    再把 clean_script 的 raw 字符偏移转换成 normalized 偏移，查时间戳。

    Args:
        clean_script: 剥离 [SECTION:N] 后的纯文本（TTS 实际合成的内容）
        sections: [{"index": N, "char_start": int, "char_end": int}, ...]
                  字符偏移基于 clean_script
        words: Whisper word-level（[{word, startMs, endMs}, ...]）

    Returns:
        [{"section_index": N, "start_ms": int, "end_ms": int}, ...]
    """
    from lib.caption_align import build_char_index

    # word 侧：normalized 文本 + 每个 norm char 对应的 word dict
    norm_word_text, char_to_word = build_char_index(words)
    if not norm_word_text:
        return []

    # script 侧：把 clean_script 也 normalize，建立 raw_offset → norm_offset 映射
    # norm_offsets[i] = clean_script 第 i 个 norm char 的 raw 偏移
    norm_offsets = []
    for i, ch in enumerate(clean_script):
        nch = normalize(ch)
        if nch:
            norm_offsets.append(i)

    # 字符量应大致匹配（script 与 word 都是同一段音频的文本）
    # 若 script norm 字符数 >> word norm 字符数，说明 script 有 word 没覆盖的内容
    # （正常，开头/结尾可能有不发音内容）；反之 word 多则 ASR 多识别
    n_script_norm = len(norm_offsets)
    n_word_norm = len(norm_word_text)

    result = []
    for sec in sections:
        raw_start = sec["char_start"]
        raw_end = sec["char_end"]
        sec_idx = sec["index"]

        # raw → norm 偏移：找 >= raw_start 的第一个 norm_offset（该节首字符）
        ns = _raw_to_norm_offset(raw_start, norm_offsets)
        # 该节末字符：找 < raw_end 的最后一个 norm_offset
        ne = _raw_to_norm_offset(raw_end, norm_offsets, end=True)

        if ns is None:
            # 该节无 norm 字符（空节或全是标点）→ 跳过或用相邻时间
            result.append({"section_index": sec_idx, "start_ms": None, "end_ms": None})
            continue

        # script norm 偏移 → word norm 偏移（近似 1:1，因为同一段音频）
        # 钳制到 word 索引范围
        w_start = min(ns, n_word_norm - 1)
        w_end = min(ne if ne is not None else ns, n_word_norm - 1)

        start_ms = int(char_to_word[w_start].get("startMs", 0))
        # end_ms: 该节最后一个 norm char 对应 word 的 endMs
        end_ms = int(char_to_word[w_end].get("endMs", start_ms))

        result.append({
            "section_index": sec_idx,
            "start_ms": start_ms,
            "end_ms": end_ms if end_ms > start_ms else start_ms,
        })

    return result


def _raw_to_norm_offset(raw_offset: int, norm_offsets: list[int],
                        end: bool = False) -> int | None:
    """把 clean_script 的 raw 字符偏移转成 normalized 字符索引。

    Args:
        raw_offset: clean_script 中的字符位置
        norm_offsets: clean_script 每个 norm char 的 raw 偏移列表
        end: True 表示取 < raw_offset 的最后一个（该节末字符）；
             False 表示取 >= raw_offset 的第一个（该节首字符）
    """
    if not norm_offsets:
        return None
    if not end:
        # 找 >= raw_offset 的第一个
        for i, ro in enumerate(norm_offsets):
            if ro >= raw_offset:
                return i
        return len(norm_offsets) - 1  # 超界 → 取最后
    else:
        # 找 < raw_offset 的最后一个
        last = None
        for i, ro in enumerate(norm_offsets):
            if ro >= raw_offset:
                break
            last = i
        return last  # 可能为 None（该节在首个 norm char 之前）


def build_sections_timeline(
    whisper_json: Path,
    sections_json_path: Path,
    clean_script_path: Path,
    output_path: Path,
) -> dict | None:
    """读 sections.json + clean script + Whisper words → sections_timeline.json。

    sections.json 由 solo_tts 在 TTS 前剥离 [SECTION:N] 标记时生成。
    无 sections.json 或 sections 为空 → 返回 None（向后兼容，plan_scenes 回退文本匹配）。
    """
    if not sections_json_path.exists() or not clean_script_path.exists():
        return None

    sections_data = read_json(sections_json_path)
    sections = sections_data.get("sections", [])
    if not sections:
        return None

    clean_script = clean_script_path.read_text(encoding="utf-8")

    # Whisper words
    whisper_data = read_json(whisper_json)
    raw_segments = (whisper_data if isinstance(whisper_data, list)
                    else whisper_data.get("captions", whisper_data.get("items", [])))
    words = GTC._extract_all_words(raw_segments)
    if not words:
        print("  [sections] WARNING: Whisper 无 word-level 时间戳，跳过 section 映射")
        return None
    words = GTC.smooth_inter_segment_gaps(words)

    timeline = map_sections_to_timeline(clean_script, sections, words)

    output = {
        "section_count": len(timeline),
        "sections": timeline,
        "source": "podcast_section_markers",
    }
    write_json(output, output_path)

    valid = [t for t in timeline if t["start_ms"] is not None]
    if valid:
        first = valid[0]["start_ms"] / 1000
        last = valid[-1]["end_ms"] / 1000
        print(f"  [sections] {len(valid)} 节映射到时间轴 "
              f"({first:.1f}s - {last:.1f}s) → {output_path.name}")
    return output


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 1：字幕对齐（Whisper + caption_align）")
    ap.add_argument("--article-dir", required=True, help="文章目录（含 播客_TTS.mp3 + 播客_脚本.txt）")
    ap.add_argument("--force", action="store_true", help="强制重新生成")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    config = read_json(SKILL_DIR / "config.json")

    video_dir = article_dir / "_video"
    temp_dir = video_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    audio_path = resolve_podcast_path(article_dir, "播客_TTS.mp3")
    script_path = resolve_podcast_path(article_dir, "播客_脚本.txt")
    whisper_out = temp_dir / "whisper_segments.json"
    timeline_out = temp_dir / "timeline_captions.json"

    # 幂等检查
    if not args.force and timeline_out.exists() and timeline_out.stat().st_size > 0:
        existing = read_json(timeline_out)
        caps = existing.get("captions", [])
        if isinstance(caps, list) and len(caps) > 0:
            print(f"  [align] SKIP（timeline_captions.json 已存在，{len(caps)} 条字幕，--force 重建）")
            return

    # 校验输入
    if not audio_path.exists():
        print(f"ERROR: 播客音频不存在: {audio_path}", file=sys.stderr)
        print("（已查找 _podcast/ 与文章根目录）请先运行 article-to-solo-podcast 生成播客音频。",
              file=sys.stderr)
        sys.exit(1)
    if not script_path.exists():
        print(f"ERROR: 播客脚本不存在: {script_path}", file=sys.stderr)
        print("（已查找 _podcast/ 与文章根目录）请先运行 article-to-solo-podcast 生成播客脚本。",
              file=sys.stderr)
        sys.exit(1)

    # 执行
    run_whisper(audio_path, whisper_out, config)
    align_captions(whisper_out, script_path, audio_path, timeline_out)

    # Section 时间轴映射（若播客脚本带 [SECTION:N] 分节标记）
    # sections.json + script_clean.txt 由 solo_tts 在 TTS 前剥离标记时生成，
    # 落在 _podcast/。无则跳过（plan_scenes 回退文本匹配）。
    podcast_dir = audio_path.parent  # _podcast/ 或根目录
    sections_timeline_out = temp_dir / "sections_timeline.json"
    sec_result = build_sections_timeline(
        whisper_out,
        podcast_dir / "sections.json",
        podcast_dir / "temp" / "script_clean.txt",
        sections_timeline_out,
    )
    if sec_result is None:
        print("  [align] 无 [SECTION:N] 分节标记，plan_scenes 将用文本匹配切场景")

    print(f"  [align] DONE → {timeline_out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
captions_to_ass.py — 阶段 4：字幕转换

把 timeline_captions.json 转成 ASS 字幕文件。
ASS 比 SRT 更适合中文（支持字体/描边/位置/动画）。

Usage:
  python captions_to_ass.py --article-dir <文章目录>
"""

import argparse
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent  # 本 skill scripts/
sys.path.insert(0, str(SCRIPTS_DIR))  # lib.* 已内化至本 skill scripts/lib/

from lib.utils import setup_windows_encoding, read_json  # noqa: E402

# 在这些标点后断行（优先级：句末 > 分句 > 逗号）
BREAK_PUNCT = "。！？；!?;:"


def ms_to_ass_time(ms) -> str:
    """毫秒 → ASS 时间格式 H:MM:SS.cc（兼容 int/float 输入）。"""
    ms = int(ms)  # 统一转 int（caption_align 可能返回 float）
    if ms < 0:
        ms = 0
    total_cs = ms // 10  # 厘秒
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def break_long_line(text: str, max_chars: int) -> str:
    """长字幕在标点处断行（用 ASS 的 \\N 换行符）。

    如果一行超过 max_chars，在最近的标点处断成两行。
    """
    if len(text) <= max_chars:
        return text

    # 找前半段的断点：在 max_chars 附近最近的标点
    best_pos = -1
    for i in range(min(max_chars, len(text) - 1), 0, -1):
        if text[i] in BREAK_PUNCT:
            best_pos = i + 1
            break

    # 没找到标点断点，尝试逗号
    if best_pos < 0:
        for i in range(min(max_chars, len(text) - 1), 0, -1):
            if text[i] in "，,":
                best_pos = i + 1
                break

    if best_pos > 0:
        line1 = text[:best_pos].strip()
        line2 = text[best_pos:].strip()
        return f"{line1}\\N{line2}"

    # 实在找不到断点，硬切
    return text[:max_chars] + "\\N" + text[max_chars:]


def escape_ass_text(text: str) -> str:
    """转义 ASS 特殊字符。"""
    # ASS 中 { } 需要转义
    text = text.replace("{", "\\{").replace("}", "\\}")
    # 换行符处理（ASS 用 \N 表示硬换行）
    text = text.replace("\n", "\\N")
    return text


def build_ass(captions: list[dict], config: dict) -> str:
    """构建完整 ASS 字幕内容。"""
    sub_cfg = config["subtitles"]
    font = sub_cfg["font"]
    fontsize = sub_cfg["fontsize"]
    primary = sub_cfg["primary_color"]
    outline = sub_cfg["outline_color"]
    outline_w = sub_cfg["outline_width"]
    shadow = sub_cfg.get("shadow", 0)
    margin_v = sub_cfg["margin_v"]
    max_chars = sub_cfg["max_chars_per_line"]
    # BorderStyle: 1=描边+阴影（旧默认，浅色图上不清），3=不透明背景框（推荐）。
    # BackColour: 背景框颜色（BorderStyle=3 时生效），ASS BGR+alpha，&H80000000=半透明黑。
    border_style = sub_cfg.get("border_style", 3)
    back_color = sub_cfg.get("back_color", "&H80000000")
    margin_l = sub_cfg.get("margin_l", 60)
    margin_r = sub_cfg.get("margin_r", 60)

    width = config["video"]["width"]
    height = config["video"]["height"]

    lines = []
    # ── Script Info ──
    lines.append("[Script Info]")
    lines.append("ScriptType: v4.00+")
    lines.append(f"PlayResX: {width}")
    lines.append(f"PlayResY: {height}")
    lines.append("WrapStyle: 2")  # 2 = 不自动换行（只在 \\N 处换）
    lines.append("ScaledBorderAndShadow: yes")
    lines.append("")

    # ── V4+ Styles ──
    lines.append("[V4+ Styles]")
    lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                 "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                 "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                 "Alignment, MarginL, MarginR, MarginV, Encoding")
    # Alignment: 2 = 底部居中（ASS numpad 布局）
    lines.append(
        f"Style: Default,{font},{fontsize},{primary},{primary},{outline},"
        f"{back_color},0,0,0,0,100,100,0,0,{border_style},{outline_w},{shadow},"
        f"2,{margin_l},{margin_r},{margin_v},1"
    )
    lines.append("")

    # ── Events ──
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text")

    for cap in captions:
        start_ms = cap.get("startMs", 0)
        end_ms = cap.get("endMs", start_ms)
        text = cap.get("text", "").strip()

        if not text:
            continue
        if end_ms <= start_ms:
            continue

        start_str = ms_to_ass_time(start_ms)
        end_str = ms_to_ass_time(end_ms)

        # 断行 + 转义
        text = break_long_line(text, max_chars)
        text = escape_ass_text(text)

        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,{text}")

    return "\n".join(lines) + "\n"


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 4：字幕转换（timeline_captions.json → ASS）")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    config = read_json(SKILL_DIR / "config.json")

    timeline = read_json(article_dir / "_video" / "temp" / "timeline_captions.json")
    captions = timeline.get("captions", [])
    if not captions:
        print("ERROR: timeline_captions.json 的 captions 为空", file=sys.stderr)
        sys.exit(1)

    # 字幕时间戳偏移：与 compose_video.py 的音频处理对齐。
    # - 有封面时（cover.enabled=true）：compose 用 adelay 给音频垫 cover_offset_ms 静音，
    #   字幕也 +cover_offset_ms 对齐。
    # - 无封面时（cover.enabled=false）：compose 用 atrim 裁掉音频开头 lead_silence_ms 静音，
    #   字幕也 -lead_silence_ms 对齐（人声从 0 秒开始，字幕也从 0 秒附近开始）。
    cover_cfg = config.get("cover", {})
    if cover_cfg.get("enabled"):
        cover_offset_ms = int(cover_cfg.get("duration_sec", 0) * 1000)
        if cover_offset_ms > 0:
            captions = [
                {**c, "startMs": c.get("startMs", 0) + cover_offset_ms,
                 "endMs": c.get("endMs", 0) + cover_offset_ms}
                for c in captions
            ]
            print(f"  [ass] 字幕时间戳 +{cover_offset_ms}ms（对齐封面片头）")
    else:
        # 无封面：裁掉开头静音，字幕时间戳前移
        if captions:
            lead_silence_ms = int(captions[0].get("startMs", 0))
            if lead_silence_ms > 200:
                captions = [
                    {**c,
                     "startMs": max(0, c.get("startMs", 0) - lead_silence_ms),
                     "endMs": max(0, c.get("endMs", 0) - lead_silence_ms)}
                    for c in captions
                ]
                print(f"  [ass] 字幕时间戳 -{lead_silence_ms}ms（对齐裁掉开头静音的音频）")

    ass_content = build_ass(captions, config)

    output_path = article_dir / "_video" / "subtitles.ass"
    output_path.write_text(ass_content, encoding="utf-8")

    # 统计
    dialogue_count = ass_content.count("Dialogue:")
    print(f"  [ass] {dialogue_count} 条字幕 → {output_path.name}")
    print(f"  [ass] 字体: {config['subtitles']['font']} {config['subtitles']['fontsize']}pt")


if __name__ == "__main__":
    main()

"""
extract_sections.py — 从播客脚本剥离 [SECTION:N] 标记，记录每节字符偏移。

播客脚本生成时在每节段首标 `[SECTION:N]`（独占一行，N=0-based 章节序号）。
TTS 不认识这些标记，合成前要剥离。本脚本剥离标记的同时，记录每节在
**剥离后纯文本**中的字符偏移 [char_start, char_end)，供下游（article-to-video）
用 Whisper word-level 时间戳把字符偏移映射成音频时间戳，实现「按插图分段切场景」。

输入：播客_脚本.txt（含 [SECTION:N] 标记，N=整数 body 段或 OPENING/ENDING 片头片尾）
输出：
  - script_clean.txt（剥离标记后的纯文本，给 TTS）
  - sections.json（每节 {index: int|str, char_start, char_end}，偏移基于 clean 文本）

无标记时：clean=原文，sections=[]（向后兼容，不报错）。

Usage:
  python extract_sections.py --input 播客_脚本.txt --output-dir _podcast/temp
  python extract_sections.py --input ... --clean-out script_clean.txt --sections-out sections.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# 匹配独占一行的 [SECTION:N] 标记（允许前后空白）。
# N 可以是整数（body 段，如 [SECTION:0]）或字符串（片头片尾，如 [SECTION:OPENING]）。
SECTION_RE = re.compile(r"^\s*\[SECTION:(\w+)\]\s*$")


def _parse_section_index(raw: str) -> int | str:
    """解析 section 标记内容：整数则转 int，否则保留字符串（OPENING/ENDING）。"""
    try:
        return int(raw)
    except ValueError:
        return raw


def extract_sections(script_text: str) -> tuple[str, list[dict]]:
    """剥离 [SECTION:N] 标记，返回 (clean_text, sections)。

    sections: [{"index": int|str, "char_start": int, "char_end": int}, ...]
    index 是整数（body 段，如 0/1/2）或字符串（片头片尾，"OPENING"/"ENDING"）。
    字符偏移基于 clean_text（剥离标记后）。每节的 char_end 是下一节 char_start
    或文本末尾。标记行整行删除（含其换行符），避免 clean_text 里出现多余空行。

    无标记时返回 (原文, [])。
    """
    lines = script_text.splitlines(keepends=True)
    clean_lines: list[str] = []
    # 记录每个 section 标记在 clean_text 中的起始偏移（即此刻 clean_lines 累计长度）
    section_starts: list[tuple[int | str, int]] = []  # (section_index, char_offset_in_clean)

    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            sec_idx = _parse_section_index(m.group(1))
            # 该 section 的内容从当前 clean_text 累计长度开始
            section_starts.append((sec_idx, sum(len(x) for x in clean_lines)))
        else:
            clean_lines.append(line)

    clean_text = "".join(clean_lines)

    if not section_starts:
        return clean_text, []

    # 按出现顺序（不依赖 section_index 数值连续，但通常连续）
    section_starts.sort(key=lambda x: x[1])
    sections = []
    for i, (sec_idx, start) in enumerate(section_starts):
        end = section_starts[i + 1][1] if i + 1 < len(section_starts) else len(clean_text)
        sections.append({"index": sec_idx, "char_start": start, "char_end": end})

    return clean_text, sections


def main():
    ap = argparse.ArgumentParser(description="剥离 [SECTION:N] 标记 + 记录字符偏移")
    ap.add_argument("--input", required=True, help="播客_脚本.txt（含标记）")
    ap.add_argument("--clean-out", help="剥离后的纯文本输出路径")
    ap.add_argument("--sections-out", help="sections.json 输出路径")
    ap.add_argument("--output-dir", help="便捷项：clean/sections 都写到该目录（script_clean.txt + sections.json）")
    args = ap.parse_args()

    script_text = Path(args.input).read_text(encoding="utf-8")
    clean_text, sections = extract_sections(script_text)

    # 决定输出路径
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_path = out_dir / "script_clean.txt"
        sections_path = out_dir / "sections.json"
    else:
        if not args.clean_out or not args.sections_out:
            sys.exit("需指定 --output-dir 或 (--clean-out + --sections-out)")
        clean_path = Path(args.clean_out)
        sections_path = Path(args.sections_out)

    clean_path.write_text(clean_text, encoding="utf-8")
    sections_path.write_text(
        json.dumps({"sections": sections}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    sys.stderr.write(
        f"[extract_sections] {len(sections)} 节 → {sections_path.name}; "
        f"clean {len(clean_text)} 字符 → {clean_path.name}\n"
    )


if __name__ == "__main__":
    main()

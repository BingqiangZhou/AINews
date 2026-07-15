#!/usr/bin/env python3
"""
Extract plain text from captions.json.

Each line in the output corresponds to one captions.json entry (empty lines for blanks).
This 1:1 line-to-entry mapping is critical for downstream highlight selection,
which uses line numbers to map highlights back to timestamps.

Usage:
    python extract-plain-text.py --input captions.json --output captions_pure.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import read_json, setup_windows_encoding


def extract_plain_text(captions: list[dict]) -> tuple[list[str], int]:
    """Extract plain text lines from captions data.

    Each entry produces exactly one line. Empty entries produce empty lines
    to maintain 1:1 index alignment with captions.json.

    Returns:
        Tuple of (lines, total_chars)
    """
    lines: list[str] = []
    total_chars = 0

    for entry in captions:
        text = entry.get("text", "").strip()
        if text:
            lines.append(text)
            total_chars += len(text)
        else:
            lines.append("")

    return lines, total_chars


def main() -> None:
    setup_windows_encoding()

    parser = argparse.ArgumentParser(description="Extract plain text from captions.json")
    parser.add_argument("--input", required=True, help="Path to captions.json")
    parser.add_argument("--output", required=True, help="Path to output text file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        result = {
            "success": False,
            "data": None,
            "error": f"INPUT_NOT_FOUND: {input_path}",
            "message": f"输入文件不存在: {input_path}",
        }
        print(result)  # noqa: T201
        sys.exit(1)

    captions = read_json(input_path)
    if not isinstance(captions, list) or len(captions) == 0:
        result = {
            "success": False,
            "data": None,
            "error": "EMPTY_CAPTIONS",
            "message": "字幕数据为空或格式不正确",
        }
        print(result)  # noqa: T201
        sys.exit(1)

    lines, total_chars = extract_plain_text(captions)

    # Write output atomically
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".txt.tmp")
    tmp_path.write_text("\n".join(lines), encoding="utf-8")
    os.replace(str(tmp_path), str(output_path))

    result = {
        "success": True,
        "data": {
            "output_path": str(output_path),
            "total_lines": len(captions),
            "total_chars": total_chars,
        },
        "error": None,
        "message": f"纯文本提取完成: {len(captions)} 行, {total_chars} 字符",
    }
    print(result)  # noqa: T201


if __name__ == "__main__":
    main()

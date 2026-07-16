"""
ingest_article.py — 从 Markdown 文章提取干净正文，作为单人播客脚本的源材料。

剥离：YAML frontmatter、HTML 注释、代码块（含内容）、图片语法、行内 code、
Markdown 强调/链接标记、列表符号；保留标题文字（去 #）；折叠多余空行。

Usage:
  python ingest_article.py --input article.md --output source.txt
  python ingest_article.py --input article.md --stdout
"""

import argparse
import re
import sys


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.lstrip("\n")


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def strip_code_fences(text: str) -> str:
    # 移除 ```...``` 代码块（含内容）
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def strip_inline_code(text: str) -> str:
    return re.sub(r"`([^`]*)`", r"\1", text)


def strip_images(text: str) -> str:
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)


def strip_links(text: str) -> str:
    # [text](url) -> text
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)


def strip_emphasis(text: str) -> str:
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"__([^_]*)__", r"\1", text)
    text = re.sub(r"_([^_]*)_", r"\1", text)
    text = re.sub(r"~~([^~]*)~~", r"\1", text)
    return text


def clean_headings_and_lists(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        # 去标题井号
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            stripped = m.group(2)
        # 去无序列表符号
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        # 去有序列表数字
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        # 去引用 >
        stripped = re.sub(r"^>\s?", "", stripped)
        # 去表格分隔线
        if re.match(r"^\|?[\s:|-]+\|?$", stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def collapse_blank(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def ingest(text: str) -> str:
    text = strip_frontmatter(text)
    text = strip_html_comments(text)
    text = strip_code_fences(text)
    text = strip_images(text)
    text = strip_inline_code(text)
    text = strip_links(text)
    text = strip_emphasis(text)
    text = clean_headings_and_lists(text)
    text = collapse_blank(text)
    return text


def main():
    ap = argparse.ArgumentParser(description="Extract clean article body for solo podcast sourcing")
    ap.add_argument("--input", required=True, help="Input Markdown/text article")
    ap.add_argument("--output", help="Output clean text file (omit with --stdout)")
    ap.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing file")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        raw = f.read()

    clean = ingest(raw)
    char_count = len(re.sub(r"\s", "", clean))

    if args.stdout:
        sys.stdout.write(clean)
    else:
        if not args.output:
            sys.exit("--output or --stdout required")
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(clean)

    sys.stderr.write(f"[ingest] clean chars (no whitespace): {char_count}\n")


if __name__ == "__main__":
    main()

"""Markdown to WeChat HTML Converter — xiaohu wrapper.

Delegates to xiaohu-wechat-format (via md-to-wechat-html-xiaohu.py) for full
markdown support including images, tables, code blocks, etc.

Usage:
    python markdown_to_wechat_html.py --input <md_file> --output <html_file> [--theme <theme>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import from the browser-publisher skill's xiaohu adapter
BP_SCRIPT = Path(__file__).resolve().parent.parent.parent / "browser-publisher" / "scripts" / "md-to-wechat-html-xiaohu.py"


def convert_via_xiaohu(md_path: str, theme: str = "github") -> dict:
    """Call xiaohu-based converter and return {title, content, digest}."""
    # Add browser-publisher scripts dir to path, then import
    bp_dir = BP_SCRIPT.parent
    if str(bp_dir) not in sys.path:
        sys.path.insert(0, str(bp_dir))

    # Use importlib to handle the hyphenated module name
    import importlib.util
    spec = importlib.util.spec_from_file_location("md_to_wechat_html_xiaohu", str(BP_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod.md_to_wechat_html_xiaohu(md_path, theme=theme)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown to WeChat-compatible HTML (xiaohu)")
    parser.add_argument("--input", required=True, help="Markdown input path")
    parser.add_argument("--output", required=True, help="HTML output path")
    parser.add_argument("--theme", default="github", help="xiaohu theme name")
    args = parser.parse_args()

    result = convert_via_xiaohu(args.input, theme=args.theme)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result["content"], encoding="utf-8")
    print(f"HTML saved: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        sys.exit(130)

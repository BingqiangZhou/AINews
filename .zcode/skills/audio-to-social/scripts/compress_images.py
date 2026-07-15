"""Compress generated social images and write an optional markdown report."""
from __future__ import annotations

import argparse
import glob
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except ImportError:
    print("错误: 需要 Pillow 库。请运行: pip install Pillow", file=sys.stderr)
    sys.exit(1)


SUPPORTED_INPUTS = {".png", ".jpg", ".jpeg", ".webp"}


def iter_inputs(values: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for value in values:
        path = Path(value)
        # Check literal file/dir FIRST, so a literal filename containing glob
        # metacharacters (e.g. a Chinese filename with a real "[1]") is matched
        # as-is instead of being misread as a character-class pattern and silently
        # skipped. Only fall back to globbing for non-literal patterns.
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUTS:
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_INPUTS)
        elif glob.has_magic(value):
            files.extend(p for p in path.parent.glob(path.name) if p.suffix.lower() in SUPPORTED_INPUTS)
        elif path.exists() and path.suffix.lower() in SUPPORTED_INPUTS:
            files.append(path)
    return sorted(set(files))


def output_path(src: Path, fmt: str, suffix: str) -> Path:
    ext = "jpg" if fmt == "jpeg" else fmt
    effective_suffix = suffix
    if src.suffix.lower().lstrip(".") == ext and not effective_suffix:
        effective_suffix = "_compressed"
    return src.with_name(f"{src.stem}{effective_suffix}.{ext}")


def compress_one(src: Path, fmt: str, quality: int, suffix: str) -> dict:
    before = src.stat().st_size
    dst = output_path(src, fmt, suffix)

    with Image.open(src) as img:
        if fmt in {"jpeg", "webp"} and img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        save_kwargs = {}
        if fmt in {"jpeg", "webp"}:
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif fmt == "png":
            save_kwargs["optimize"] = True
        img.save(dst, fmt.upper() if fmt != "jpeg" else "JPEG", **save_kwargs)

    after = dst.stat().st_size
    ratio = 0 if before == 0 else round((1 - after / before) * 100, 1)
    return {
        "source": str(src),
        "output": str(dst),
        "format": fmt,
        "quality": quality,
        "before": before,
        "after": after,
        "reduction_percent": ratio,
    }


def write_report(rows: list[dict], report: Path) -> None:
    lines = [
        "# 图片压缩报告",
        "",
        "| 原图 | 压缩图 | 格式 | 质量 | 原始大小 | 压缩后 | 压缩率 |",
        "|------|--------|------|------|----------|--------|--------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['source']} | {row['output']} | {row['format']} | {row['quality']} | "
            f"{row['before']} | {row['after']} | {row['reduction_percent']}% |"
        )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compress social media images")
    parser.add_argument("inputs", nargs="+", help="Image files, globs, or directories")
    parser.add_argument("--format", default="webp", choices=["webp", "png", "jpeg"], help="Output format")
    parser.add_argument("--quality", type=int, default=80, help="Quality for webp/jpeg")
    parser.add_argument("--suffix", default="", help="Output suffix before extension")
    parser.add_argument("--report", help="Markdown report path")
    parser.add_argument("--parallel", action="store_true", help="Compress images in parallel using threads")
    args = parser.parse_args()

    if not (1 <= args.quality <= 100):
        raise SystemExit("--quality must be between 1 and 100")

    files = iter_inputs(args.inputs)
    if not files:
        raise SystemExit("No supported image files found")

    rows: list[dict] = []
    errors: list[dict] = []

    if args.parallel and len(files) > 1:
        # Parallel compression: PIL releases GIL during C-level encoding
        with ThreadPoolExecutor(max_workers=min(len(files), 4)) as executor:
            futures = {
                executor.submit(compress_one, f, args.format, args.quality, args.suffix): f
                for f in files
            }
            for future in as_completed(futures):
                f = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    errors.append({"file": str(f), "error": str(exc)})
                    print(f"压缩失败 {f}: {exc}", file=sys.stderr)
        # Preserve original file order in report
        rows.sort(key=lambda r: files.index(Path(r["source"])))
    else:
        for f in files:
            try:
                rows.append(compress_one(f, args.format, args.quality, args.suffix))
            except Exception as exc:
                errors.append({"file": str(f), "error": str(exc)})
                print(f"压缩失败 {f}: {exc}", file=sys.stderr)

    if args.report and rows:
        write_report(rows, Path(args.report))

    for row in rows:
        print(
            f"{row['source']} -> {row['output']} "
            f"({row['before']} -> {row['after']} bytes, {row['reduction_percent']}%)"
        )

    if errors:
        err_path = Path(args.report).with_name("compress_errors.json") if args.report else Path("compress_errors.json")
        err_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{len(errors)} 个文件压缩失败，详情: {err_path}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断，已生成文件保留", file=sys.stderr)
        sys.exit(130)

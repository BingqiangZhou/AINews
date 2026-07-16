"""Reconcile planned, referenced, and generated ai-news-digest images."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


MIN_BYTES = 5 * 1024
DEFAULT_COVER_SIZE = "900x383"
DEFAULT_ILLUSTRATION_SIZE = "1920x1080"
MD_REF_RE = re.compile(r"!\[[^\]]*\]\((imgs/[^)]+\.png)\)")
HTML_REF_RE = re.compile(r"""src=["'](imgs/[^"']+\.png)["']""")
OUTLINE_FILE_RE = re.compile(r"^\*\*Filename\*\*:\s*(.+\.png)\s*$", re.M)
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _load_image_defaults() -> dict:
    """Read cover/illustration sizes from config.json (image section).

    Fault-tolerant: returns {} when config is missing/unreadable so the CLI
    falls back to the DEFAULT_COVER_SIZE / DEFAULT_ILLUSTRATION_SIZE constants.
    """
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(cfg, dict):
        return {}
    image = cfg.get("image") or {}
    return {"cover_size": image.get("cover_size"), "illustration_size": image.get("illustration_size")}


def failure(code: str, message: str, path: Path | None = None) -> dict:
    return {"code": code, "message": message, "path": str(path) if path else None}


def parse_size(s: str) -> tuple[int, int]:
    """Parse WxH size string into (width, height) tuple."""
    parts = s.split("x")
    if len(parts) != 2:
        raise ValueError(f"invalid size format '{s}', expected WxH")
    return (int(parts[0]), int(parts[1]))


def read_text(path: Path, failures: list[dict], code: str) -> str:
    if not path.exists() or path.stat().st_size == 0:
        failures.append(failure(code, f"required file missing or empty: {path}", path))
        return ""
    return path.read_text(encoding="utf-8-sig")


def compute_prompt_hash(path: Path) -> str | None:
    """Compute sha256 hash of a prompt file (first 16 hex chars), or None if file missing."""
    if not path.exists():
        return None
    content = path.read_bytes()
    h = hashlib.sha256(content).hexdigest()[:16]
    return f"sha256:{h}"


def verify_prompt_hashes(
    output_dir: Path,
    state: dict,
    cover_stem: str,
    illustration_stems: list[str],
    failures: list[dict],
) -> None:
    """Compare stored prompt_hash in state.json with current prompt file hashes.

    Supports both v3 (phase6.generate.*) and v4 (stages.media.*) state schemas.
    In v4 (pure-orchestrator), prompt hashes are owned by the downstream
    illustrator skill, so the orchestrator state has none and this is a no-op.
    """
    generate = state.get("phase6", {}).get("generate", {})
    if not generate:
        # v4 orchestrator state: prompt hashes not tracked here -> no-op.
        return

    # Cover
    cover_entry = generate.get("cover", {})
    if not isinstance(cover_entry, dict):
        # cover may be a placeholder string ("pending"/"skipped") before Phase 6
        # generates it; skip hash verification in that case rather than crashing
        # on .get() (state-schema.md documents cover as an object post-Phase-6).
        cover_entry = {}
    stored_hash = cover_entry.get("prompt_hash")
    if stored_hash and cover_entry.get("status") == "completed":
        prompt_file = output_dir / "prompts" / "cover.md"
        current_hash = compute_prompt_hash(prompt_file)
        if current_hash and current_hash != stored_hash:
            failures.append(failure(
                "PROMPT_HASH_MISMATCH",
                f"cover prompt hash changed: stored={stored_hash}, current={current_hash}",
                prompt_file,
            ))

    # Illustrations
    items = generate.get("illustrations", {}).get("items", [])
    for item in items:
        if item.get("status") != "completed":
            continue
        stored = item.get("prompt_hash")
        if not stored:
            continue
        image_id = item.get("image_id", "")
        prompt_file = output_dir / "imgs" / "prompts" / f"{image_id}.md"
        current = compute_prompt_hash(prompt_file)
        if current and current != stored:
            failures.append(failure(
                "PROMPT_HASH_MISMATCH",
                f"illustration prompt hash changed: id={image_id}, stored={stored}, current={current}",
                prompt_file,
            ))


def inspect_png(path: Path, expected_size: tuple[int, int], failures: list[dict]) -> None:
    if not path.exists():
        failures.append(failure("IMAGE_MISSING", f"image does not exist: {path}", path))
        return
    if path.stat().st_size <= MIN_BYTES:
        failures.append(failure("IMAGE_TOO_SMALL", f"image is <= {MIN_BYTES} bytes: {path}", path))
        return
    try:
        with Image.open(path) as image:
            if image.size != expected_size:
                failures.append(
                    failure(
                        "IMAGE_DIMENSIONS_INVALID",
                        f"expected {expected_size[0]}x{expected_size[1]}, got {image.width}x{image.height}",
                        path,
                    )
                )
    except OSError as exc:
        failures.append(failure("IMAGE_INVALID", f"cannot open image: {exc}", path))


def reconcile(
    output_dir: Path,
    require_cover: bool,
    require_illustrations: bool,
    failed_ids: set[str] | None = None,
    cover_size: tuple[int, int] = (900, 383),
    illustration_size: tuple[int, int] = (1920, 1080),
    verify_prompt_hash: bool = False,
) -> dict:
    failures: list[dict] = []
    checked_images: list[str] = []

    if require_cover:
        read_text(output_dir / "prompts" / "cover.md", failures, "COVER_PROMPT_MISSING")
        cover = output_dir / "公众号_封面.png"
        inspect_png(cover, cover_size, failures)
        checked_images.append(str(cover))

    if require_illustrations:
        outline = read_text(output_dir / "imgs" / "outline.md", failures, "OUTLINE_MISSING")
        article = read_text(output_dir / "公众号_文章.md", failures, "ARTICLE_MISSING")
        html = read_text(output_dir / "公众号_文章.html", failures, "HTML_MISSING")
        outline_refs = [f"imgs/{name.strip()}" for name in OUTLINE_FILE_RE.findall(outline)]
        md_refs = MD_REF_RE.findall(article)
        html_refs = HTML_REF_RE.findall(html)

        # In lenient mode, split refs into successful and skipped
        effective_failed_ids = failed_ids if failed_ids else set()
        successful_refs = [r for r in outline_refs if Path(r).stem not in effective_failed_ids]
        skipped_refs = [r for r in outline_refs if Path(r).stem in effective_failed_ids]

        # Check prompt files only for successful refs
        prompt_dir = output_dir / "imgs" / "prompts"
        prompt_refs = []
        for relative_path in successful_refs:
            stem = Path(relative_path).stem
            prompt_file = prompt_dir / f"{stem}.md"
            if prompt_file.exists() and prompt_file.stat().st_size > 0:
                prompt_refs.append(relative_path)
            else:
                failures.append(failure(
                    "PROMPT_MISSING",
                    f"prompt file missing or empty for {relative_path}: {prompt_file}",
                    prompt_file,
                ))

        if not outline_refs:
            failures.append(failure("OUTLINE_EMPTY", "outline declares no illustrations"))

        # In lenient mode, md/html refs must match successful_refs (subset of outline)
        # In strict mode, they must match full outline_refs
        expected_refs = successful_refs if effective_failed_ids else outline_refs
        if expected_refs != md_refs:
            failures.append(failure("MARKDOWN_REFS_MISMATCH", f"outline={expected_refs}, markdown={md_refs}"))
        if expected_refs != html_refs:
            failures.append(failure("HTML_REFS_MISMATCH", f"outline={expected_refs}, html={html_refs}"))

        # Inspect PNG images for successful refs
        for relative_path in successful_refs:
            image = output_dir / relative_path
            inspect_png(image, illustration_size, failures)
            checked_images.append(str(image))

        # Report skipped images
        for relative_path in skipped_refs:
            image = output_dir / relative_path
            checked_images.append(f"{image} (SKIPPED)")

    # Optional prompt hash verification
    if verify_prompt_hash:
        state_path = output_dir / "state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8-sig"))
                cover_stem = "cover"
                illust_stems = [str(r) for r in checked_images]
                verify_prompt_hashes(output_dir, state, cover_stem, illust_stems, failures)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                failures.append(failure(
                    "STATE_JSON_UNREADABLE",
                    f"state.json unreadable, prompt hash verification skipped: {e}",
                    state_path,
                ))

    return {
        "passed": not failures,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checked_images": checked_images,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated cover and illustration media")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--require-cover", action="store_true")
    parser.add_argument("--require-illustrations", action="store_true")
    parser.add_argument("--failed-ids", default="", help="Comma-separated illustration IDs to skip (lenient mode)")
    image_defaults = _load_image_defaults()
    default_cover = image_defaults.get("cover_size") or DEFAULT_COVER_SIZE
    default_illustration = image_defaults.get("illustration_size") or DEFAULT_ILLUSTRATION_SIZE
    parser.add_argument("--cover-size", default=default_cover, help=f"Expected cover size WxH (default: {default_cover}; source: config.image.cover_size)")
    parser.add_argument("--illustration-size", default=default_illustration, help=f"Expected illustration size WxH (default: {default_illustration}; source: config.image.illustration_size)")
    parser.add_argument("--verify-prompt-hash", action="store_true", help="Verify prompt file hashes match state.json records")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    failed_ids_str = args.failed_ids.strip()
    failed_ids = set(failed_ids_str.split(",")) if failed_ids_str else None
    result = reconcile(
        Path(args.output_dir),
        args.require_cover,
        args.require_illustrations,
        failed_ids,
        cover_size=parse_size(args.cover_size),
        illustration_size=parse_size(args.illustration_size),
        verify_prompt_hash=args.verify_prompt_hash,
    )
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()

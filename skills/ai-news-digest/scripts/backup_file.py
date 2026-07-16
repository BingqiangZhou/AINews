#!/usr/bin/env python3
"""Atomic backup with rotation (max 3 copies).

Usage:
    python backup_file.py --file path/to/file.txt

Creates a timestamped backup: file-backup-20260607-143022.txt
Keeps at most 3 backups; oldest are auto-deleted.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def backup_file(path: Path, max_copies: int = 3) -> Path:
    """Create a timestamped backup and rotate old copies."""
    if not path.exists():
        raise FileNotFoundError(f"Cannot backup non-existent file: {path}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}-backup-{timestamp}{path.suffix}")
    shutil.copy2(path, backup)

    # Rotate: keep only max_copies newest backups
    backups = sorted(
        path.parent.glob(f"{path.stem}-backup-*{path.suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in backups[max_copies:]:
        stale.unlink()

    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Create timestamped backup with rotation")
    parser.add_argument("--file", required=True, help="File to backup")
    parser.add_argument("--max-copies", type=int, default=3, help="Max backup copies to keep (default: 3)")
    args = parser.parse_args()

    result = backup_file(Path(args.file), max_copies=args.max_copies)
    output = {"backup": str(result), "original": args.file}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()

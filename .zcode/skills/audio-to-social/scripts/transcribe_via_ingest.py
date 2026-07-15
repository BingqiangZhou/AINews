#!/usr/bin/env python3
"""Thin wrapper that delegates transcription to whisper-transcribe's script
and adapts outputs to audio-to-social's expected directory structure.

Usage:
    python transcribe_via_ingest.py \\
        --audio-file "path/to/audio.m4a" \\
        --output-dir "path/to/output" \\
        --model large-v3-turbo --batch-size 16 --language zh
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_skill_root() -> Path:
    """Locate the .zcode/skills directory relative to this script."""
    # This script lives at .zcode/skills/audio-to-social/scripts/
    return Path(__file__).resolve().parent.parent.parent  # .zcode/skills/


# Backstops against infinite hangs. Transcription of even a multi-hour podcast on
# GPU stays well under TRANSCRIBE_TIMEOUT; extract is a trivial JSON parse.
TRANSCRIBE_TIMEOUT = 3600  # seconds (60 min)
EXTRACT_TIMEOUT = 120      # seconds


def _tail(text: str | bytes | None, label: str = "last output", n: int = 20) -> str:
    """Format the last n lines of captured subprocess output for an error message."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if not text or not text.strip():
        return ""
    lines = text.strip().splitlines()[-n:]
    return f"\n--- {label} (last {len(lines)} lines) ---\n" + "\n".join(lines)


def _run_cmd(cmd: list[str], desc: str, env: dict | None = None, timeout: float | None = None) -> None:
    """Run a command, raising on failure with captured stderr and a hard timeout.

    Captures stdout/stderr so a non-zero exit reports the real error (not just an
    exit code), and enforces a timeout so a hung subprocess can never block the
    pipeline forever — subprocess.run's internal timer fires even when the child
    produces no output. Captured stdout is echoed so progress output is not lost.
    """
    print(f"[transcribe_via_ingest] {desc}...", flush=True)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"{desc} timed out after {timeout}s" + _tail(e.output) + _tail(e.stderr, label="stderr")
        ) from e
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    if result.returncode != 0:
        raise RuntimeError(
            f"{desc} failed with exit code {result.returncode}" + _tail(result.stderr, label="stderr")
        )


def main() -> int:
    # Load defaults from audio-to-social config.json
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    config_defaults: dict = {}
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
            # Support new grouped format (environment section)
            if "environment" in raw:
                config_defaults = raw.get("environment", {})
            else:
                config_defaults = raw
        except (json.JSONDecodeError, OSError):
            pass

    parser = argparse.ArgumentParser(
        description="Delegate transcription to whisper-transcribe and adapt outputs."
    )
    parser.add_argument("--audio-file", required=True, help="Path to input audio file")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--model", default=config_defaults.get("whisper_model", "large-v3-turbo"), help="Whisper model name")
    parser.add_argument("--batch-size", type=int, default=config_defaults.get("whisper_batch_size", 16), help="Batch size")
    parser.add_argument("--language", default=config_defaults.get("whisper_language", "zh"), help="Language code (default: config environment.whisper_language)")
    parser.add_argument("--pipeline", choices=["whisper", "batched"], default="whisper",
                        help="Transcription pipeline: 'whisper' (full coverage) or 'batched' (faster, may drop ~25%% speech)")
    parser.add_argument("--initial-prompt", default=config_defaults.get("whisper_initial_prompt", "以下是普通话的句子。"), help="Initial prompt for Whisper (default: config environment.whisper_initial_prompt)")
    args = parser.parse_args()

    skill_root = _find_skill_root()
    ingest_transcribe = skill_root / "whisper-transcribe" / "scripts" / "transcribe-faster-whisper.py"
    # extract-plain-text.py 已内化至本 skill（原 highlight-extract 归档），
    # 自带 lib.utils，单拿可跑。接口：--input captions.json --output text.txt。
    extract_script = Path(__file__).resolve().parent / "extract-plain-text.py"
    ingest_lib = skill_root / "whisper-transcribe" / "scripts" / "lib"

    if not ingest_transcribe.exists():
        print(f"Error: whisper-transcribe script not found at {ingest_transcribe}", file=sys.stderr)
        return 1
    if not extract_script.exists():
        print(f"Error: extract-plain-text script not found at {extract_script}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    audio_file = Path(args.audio_file)

    temp_dir = output_dir / "temp"
    cache_dir = output_dir / "cache"
    temp_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Run whisper-transcribe's transcription
    # Output captions.json and transcribe_metadata.json to temp/ (staging area)
    captions_path = temp_dir / "captions.json"
    metadata_path = temp_dir / "transcribe_metadata.json"

    py = sys.executable
    transcribe_cmd = [
        py, str(ingest_transcribe),
        str(audio_file),
        "--output", str(captions_path),
        "--metadata", str(metadata_path),
        "--model", args.model,
        "--batch-size", str(args.batch_size),
        "--lang", args.language,
        "--pipeline", args.pipeline,
    ]
    if args.initial_prompt:
        transcribe_cmd.extend(["--initial-prompt", args.initial_prompt])

    # Set up environment for whisper-transcribe scripts
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    # Add whisper-transcribe lib to PYTHONPATH for transcribe script
    env["PYTHONPATH"] = str(ingest_lib) + os.pathsep + env.get("PYTHONPATH", "")

    _run_cmd(transcribe_cmd, "Running Whisper transcription via whisper-transcribe", env=env, timeout=TRANSCRIBE_TIMEOUT)

    # Step 2: Generate 转录文本.txt (plain text) from captions.json
    transcript_path = temp_dir / "转录文本.txt"
    extract_cmd = [
        py, str(extract_script),
        "--input", str(captions_path),
        "--output", str(transcript_path),
    ]
    _run_cmd(extract_cmd, "Generating plain text transcript", env=env, timeout=EXTRACT_TIMEOUT)

    # Step 3: Copy captions.json and transcribe_metadata.json to cache/
    shutil.copy2(str(captions_path), str(cache_dir / "captions.json"))
    shutil.copy2(str(metadata_path), str(cache_dir / "transcribe_metadata.json"))

    # Step 4: Clean up whisper-transcribe outputs that may have been placed next to the audio file
    audio_dir = audio_file.parent
    for name in ("captions.json", "transcribe_metadata.json"):
        sidecar = audio_dir / name
        if sidecar.exists() and sidecar.resolve() != (temp_dir / name).resolve():
            sidecar.unlink()

    # Step 5: Validate outputs
    for required in (captions_path, metadata_path, transcript_path):
        if not required.exists() or required.stat().st_size == 0:
            print(f"Error: required output missing or empty: {required}", file=sys.stderr)
            return 1

    # Report results
    captions = json.loads(captions_path.read_text(encoding="utf-8"))
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    duration = meta.get("duration", 0)

    print(f"[transcribe_via_ingest] Done: {len(captions)} segments, {duration:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

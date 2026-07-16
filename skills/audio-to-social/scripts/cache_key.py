"""Canonical cache_key for audio-to-social transcription cache.

Single source of truth for the cache_key that Phase 0 / audio-engineer use to
key the global transcription cache at
``{storage_root}/.audio-to-social-cache/{cache_key}/``.

The key is a **path-safe hex hash**. Windows paths forbid ``| < > : * ? " \\ /``
among others, so a descriptive key like ``"新录音 39.m4a|60681957|1781285236"``
is NOT usable as a directory name (``Test-Path`` raises "Illegal characters in
path"). Earlier runs also produced a mix of descriptive / hex keys, so cache
reuse across runs was unreliable. This helper fixes both: one algorithm, always
hex, always directory-name-safe.

It hashes normalized absolute path + file size + mtime_ns, so the same audio
file reused across runs hits the cache, and any replace/touch misses.

Usage::

    python cache_key.py <audio_file>          # prints the 16-char hex key

    from cache_key import compute_cache_key
    key = compute_cache_key("path/to/audio.m4a")
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path


def compute_cache_key(audio_path: str | Path) -> str:
    """Return a 16-char hex cache_key for an audio file (path-safe)."""
    p = Path(audio_path)
    st = p.stat()
    norm = os.path.normcase(os.path.abspath(p))
    raw = f"{norm}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compute the canonical audio-to-social transcription cache_key."
    )
    ap.add_argument("audio_file", help="Path to the audio file")
    args = ap.parse_args()
    print(compute_cache_key(args.audio_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

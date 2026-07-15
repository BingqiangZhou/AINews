#!/usr/bin/env python3
"""
Shared utilities for image-generator scripts.

Vendored (intentionally, per the project's skill-independence principle) to keep
image-generator standalone. Holds the API-key resolution, config loading, and
binary-download helpers.

Functions:
    get_api_key(args_api_key)                     — resolve AGNES_API_KEY (arg > env)
    load_config(config_path=None)                 — read skill config.json (single source of truth)
    derive_video_query_base(base_url)             — root origin for the /agnesapi polling endpoint
    download_file(url, output_path, ...)          — streaming download with retries
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def get_api_key(args_api_key: str | None) -> str:
    """Get API key from the --api-key argument or the AGNES_API_KEY env var.

    Exits the process with an error message if neither is provided.
    """
    if args_api_key:
        return args_api_key
    key = os.environ.get("AGNES_API_KEY")
    if not key:
        print("Error: API key required. Use --api-key or set AGNES_API_KEY env var.", file=sys.stderr)
        sys.exit(1)
    return key


def load_config(config_path: str | os.PathLike | None = None) -> dict:
    """Load the skill's ``config.json`` (the single source of truth).

    Per AGENTS.md rule 3, paths / models / endpoints live in
    ``.zcode/skills/image-generator/config.json`` rather than being hardcoded in each
    script. This helper reads it and returns the parsed dict so argparse
    defaults can use it.

    Resilient by design: a missing or malformed file returns ``{}`` instead of
    raising — callers always pass a fallback to ``dict.get(key, default)``, so a
    broken config degrades to the documented defaults rather than crashing the
    CLI. This keeps scripts runnable standalone (e.g. ``--help``) before any
    config exists.

    Args:
        config_path: Override path to the config file. Defaults to
            ``<this file's dir>/../../config.json`` (i.e. the skill root).

    Returns:
        Parsed config dict, or ``{}`` on any read/parse failure.
    """
    path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / "config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def derive_video_query_base(base_url: str) -> str:
    """Derive the root origin used by the irregular ``/agnesapi`` poll endpoint.

    The Agnes video API has one endpoint that does NOT sit under ``/v1``: the
    task-status query is ``GET {root}/agnesapi?video_id=...`` (see
    references/api.md §3). All other endpoints are ``{base_url}/...`` where
    ``base_url`` ends in ``/v1``. Without this derivation, ``--base-url`` would
    steer creation/download to a custom host but leave polling pinned to the
    hardcoded production URL, splitting the flow across two hosts.

    Rules (in order):
      1. Strip a trailing slash, then strip a trailing ``/v1``.
      2. If the result still contains a path (e.g. ``https://host/api``),
         fall back to the bare origin ``scheme://host[:port]`` — the polling
         endpoint lives at the host root.

    Examples:
      >>> derive_video_query_base("https://apihub.agnes-ai.com/v1")
      'https://apihub.agnes-ai.com'
      >>> derive_video_query_base("https://apihub.agnes-ai.com/v1/")
      'https://apihub.agnes-ai.com'
      >>> derive_video_query_base("https://custom.example.com/v1")
      'https://custom.example.com'
      >>> derive_video_query_base("https://host/api")
      'https://host'
    """
    from urllib.parse import urlsplit

    url = base_url.rstrip("/")
    if url.endswith("/v1"):
        return url[:-3]
    parts = urlsplit(base_url)
    host = parts.hostname or ""
    port_part = f":{parts.port}" if parts.port is not None else ""
    return f"{parts.scheme}://{host}{port_part}"


def download_file(
    url: str,
    output_path: str,
    retries: int = 3,
    timeout: int = 120,
    min_size: int = 1000,
) -> None:
    """Download a binary file from ``url`` to ``output_path`` with retries.

    Streams to disk in 8KB chunks. After writing, guards against a truncated /
    corrupted response by raising if the result is smaller than ``min_size`` bytes.

    Args:
        url: Source URL.
        output_path: Destination file path.
        retries: Number of attempts before re-raising the last error.
        timeout: Per-request timeout in seconds (videos need a larger value).
        min_size: Minimum acceptable file size in bytes (images ~1KB, videos ~10KB).

    ``requests`` is imported lazily so importing this module has no hard
    dependency if a caller only wants ``get_api_key``.
    """
    import requests  # lazy: keep module importable without requests installed

    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size = os.path.getsize(output_path)
            if file_size < min_size:
                raise ValueError(f"Downloaded file too small ({file_size} bytes), likely corrupted")
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"Download retry {attempt + 1}/{retries} after {wait}s: {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                raise

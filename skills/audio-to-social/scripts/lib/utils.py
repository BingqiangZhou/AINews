#!/usr/bin/env python3
"""
Cross-skill shared pipeline utilities (canonical source).

This module is the single source of the pipeline utility surface. It lives in
`audio-to-social` (the de-facto shared-scripts hub; see AGENTS.md "Config reuse
points at audio-to-social") and is imported read-only by other skills:

  - whisper-transcribe/scripts/transcribe-faster-whisper.py
  - article-to-video/scripts/align_captions.py

Sibling skills MUST NOT keep their own copy; they `sys.path.insert` to this
script dir and `from lib.utils import ...` (same pattern as
article-to-solo-podcast/scripts/solo_tts.py importing tts-generation).

Provides common functions for:
- Audio duration probing (ffprobe wrapper)
- JSON file operations (atomic write support)
- Configuration loading (unified cache)
- Network retry with exponential backoff
- Streaming download
- Disk space checking
- Logging setup
- Pipeline exception hierarchy
- Text normalization
- Podcast artifact path resolution (shared with article-to-video)
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar


# ---------------------------------------------------------------------------
# Windows encoding
# ---------------------------------------------------------------------------

def setup_windows_encoding() -> None:
    """
    Fix Windows console encoding for Chinese characters.

    On Windows, the default console encoding is often GBK/CP936,
    which cannot handle many Chinese characters. This function
    reconfigures stdout/stderr to use UTF-8 encoding.

    Call this at the start of any script that outputs Chinese text.
    """
    if sys.platform == "win32":
        # Set PYTHONIOENCODING environment variable
        os.environ["PYTHONIOENCODING"] = "utf-8"

        # Reconfigure stdout/stderr to UTF-8 regardless of TTY
        # When running as a subprocess, stdout/stderr are pipes that
        # still default to cp1252 on Windows, which can't encode Chinese.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMMON_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300
DEFAULT_BITRATE = "192k"
DEFAULT_FADE_SECONDS = 0.4
DEFAULT_PAD_SECONDS = 0.25
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0

T = TypeVar("T")

# __file__ = scripts/lib/utils.py
# .parent = scripts/lib/  ->  .parent.parent = scripts/  ->  .parent.parent.parent = skill root
_UTILS_FILE = Path(__file__).resolve()
SCRIPT_DIR = str(_UTILS_FILE.parent.parent)       # scripts/
SKILL_DIR = str(_UTILS_FILE.parent.parent.parent)  # skill root (where config.json lives)

_config_cache: Optional[Dict[str, Any]] = None
_config_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_config_path() -> Path:
    """Get the path to config.json in the skill root."""
    return Path(SKILL_DIR) / "config.json"


def _resolve_skill_config_dir() -> Optional[Path]:
    """Resolve skill-specific config directory from CLI args or env var."""
    # 1. Check --config-dir CLI argument
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--config-dir" and i < len(sys.argv) - 1:
            return Path(sys.argv[i + 1])
        if arg.startswith("--config-dir="):
            return Path(arg.split("=", 1)[1])

    # 2. Check SKILL_CONFIG_DIR environment variable
    env_dir = os.environ.get("SKILL_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)

    return None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration with layered merging.

    Layer order (later layers override earlier):
    1. skill config.json (base defaults)
    2. Skill-specific config.json (from --config-dir or SKILL_CONFIG_DIR env)

    Returns cached config if available, unless force_reload is True.
    Thread-safe: uses a lock to prevent concurrent cache corruption.
    """
    global _config_cache

    with _config_lock:
        if _config_cache is not None and not force_reload:
            return _config_cache

        # Start with hardcoded defaults
        merged: Dict[str, Any] = {
            "python_executable": "python",
            "ffmpeg_path": "ffmpeg",
            "ffprobe_path": "ffprobe",
            "default_timeout": COMMON_TIMEOUT,
            "download_timeout": DOWNLOAD_TIMEOUT,
            "max_retries": MAX_RETRIES,
            "default_whisper_model": "large-v3-turbo",
            "default_bitrate": DEFAULT_BITRATE,
            "default_fade_seconds": DEFAULT_FADE_SECONDS,
            "default_pad_before": DEFAULT_PAD_SECONDS,
            "default_pad_after": DEFAULT_PAD_SECONDS,
        }

        # Layer 1: skill config.json (in the skill root directory)
        shared_config_path = Path(SKILL_DIR) / "config.json"
        if shared_config_path.exists():
            try:
                shared = json.loads(shared_config_path.read_text(encoding="utf-8"))
                _deep_merge(merged, shared)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: skill config.json unreadable: {e}", file=sys.stderr)

        # Layer 2: Skill-specific config.json (from --config-dir)
        skill_config_dir = _resolve_skill_config_dir()
        if skill_config_dir:
            skill_config_path = skill_config_dir / "config.json"
            if skill_config_path.exists():
                try:
                    skill_config = json.loads(skill_config_path.read_text(encoding="utf-8"))
                    _deep_merge(merged, skill_config)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Warning: skill config.json unreadable: {e}", file=sys.stderr)

        _config_cache = merged
        return _config_cache


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override into base (mutates base). Dict values are merged recursively."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_config() -> Dict[str, Any]:
    """Alias for load_config() for backward compatibility."""
    return load_config()


def get_ffprobe_path() -> str:
    """Get ffprobe executable path: env var AINews_FFPROBE > config > 'ffprobe' on PATH.

    Reads either the legacy flat key ``ffprobe_path`` or the canonical nested
    key ``environment.ffprobe`` (AGENTS.md convention), so config.json can use
    either naming without breaking path resolution.
    """
    env = os.environ.get("AINews_FFPROBE")
    if env:
        return env
    config = load_config()
    env_block = config.get("environment", {})
    if isinstance(env_block, dict) and env_block.get("ffprobe"):
        return env_block["ffprobe"]
    return config.get("ffprobe_path", "ffprobe")


def get_ffmpeg_path() -> str:
    """Get ffmpeg executable path: env var AINews_FFMPEG > config > 'ffmpeg' on PATH.

    Reads either the legacy flat key ``ffmpeg_path`` or the canonical nested
    key ``environment.ffmpeg`` (AGENTS.md convention), so config.json can use
    either naming without breaking path resolution.
    """
    env = os.environ.get("AINews_FFMPEG")
    if env:
        return env
    config = load_config()
    env_block = config.get("environment", {})
    if isinstance(env_block, dict) and env_block.get("ffmpeg"):
        return env_block["ffmpeg"]
    return config.get("ffmpeg_path", "ffmpeg")


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------

def write_json(data: object, output_path: Path | str, atomic: bool = True) -> None:
    """
    Write data to JSON file with optional atomic write.

    Args:
        data: Data to serialize
        output_path: Output file path
        atomic: If True, write to temp file then rename for atomicity
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(data, ensure_ascii=False, indent=2)

    if atomic:
        # Write to temp file, then rename atomically
        fd, temp_path = tempfile.mkstemp(
            dir=output_path.parent,
            prefix=output_path.stem,
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(temp_path, output_path)
        except Exception:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise
    else:
        output_path.write_text(content, encoding="utf-8")


# Alias for pipeline compatibility
save_json = write_json


def read_json(input_path: Path | str) -> Any:
    """
    Read JSON file.

    Args:
        input_path: Input file path

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise json.JSONDecodeError("File is empty", content, 0)
    return json.loads(content)


# Alias for pipeline compatibility
load_json = read_json


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def _build_normalize_re():
    """Build normalization regex safely to avoid char class escaping issues."""
    # Characters to strip: whitespace + CJK/English punctuation
    chars_to_strip = [
        " \u3000\u00a0",          # spaces
        ",\uff0c\u3002\uff01\uff1f\u3001\uff1b\uff1a",  # CJK punctuation
        "\u201c\u201d\u2018\u2019\u300c\u300d\u300e\u300f",  # curly + corner quotes
        '"',                       # double quote
        "'",                       # single quote
        "()\uff08\uff09",          # parentheses
        "[]\u3010\u3011{}",          # brackets
        "\u00b7\u2026\u2014\u2013",  # special
        "-_/\\",                   # dashes, slashes, backslash
    ]
    all_chars = "".join(chars_to_strip)
    escaped = "".join(re.escape(c) for c in all_chars)
    return re.compile(r"[\s" + escaped + r"]+")


_NORMALIZE_RE = _build_normalize_re()


def normalize_for_match(text: str) -> str:
    """Normalize text for fuzzy matching by stripping whitespace and punctuation."""
    return _NORMALIZE_RE.sub("", text)


# ---------------------------------------------------------------------------
# Podcast artifact path resolution
# ---------------------------------------------------------------------------

def resolve_podcast_path(article_dir: Path | str, filename: str) -> Path:
    """Resolve a podcast artifact (播客_TTS.mp3 / 播客_脚本.txt) under an article dir.

    article-to-solo-podcast writes its outputs to `<文章目录>/_podcast/` (its
    SKILL.md rule 6), while article-to-video historically expected them at the
    article root. This resolver bridges both layouts.

    Lookup priority:
      1. `_podcast/<filename>` (canonical, current article-to-solo-podcast output)
      2. `<filename>` at the article root (backward compatibility)
      3. If neither exists, return the `_podcast/<filename>` path so that the
         caller's "file not found" error points at the canonical location.

    Returns:
        Absolute Path to the resolved artifact.
    """
    article = Path(article_dir).resolve()
    podcast_subdir = article / "_podcast" / filename
    if podcast_subdir.exists():
        return podcast_subdir
    root_path = article / filename
    if root_path.exists():
        return root_path
    return podcast_subdir


# ---------------------------------------------------------------------------
# Audio / FFmpeg
# ---------------------------------------------------------------------------

def probe_duration(audio_path: Path | str, timeout: int = 30) -> float:
    """
    Probe audio duration using ffprobe.

    Args:
        audio_path: Path to audio file
        timeout: Subprocess timeout in seconds

    Returns:
        Duration in seconds, or 0.0 on error
    """
    ffprobe_path = get_ffprobe_path()
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            timeout=timeout,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError,
            subprocess.TimeoutExpired):
        return 0.0


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
        exceptions: Tuple of exception types to catch
        on_retry: Optional callback(attempt, exception) before retry

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        if on_retry:
                            on_retry(attempt + 1, exc)
                        time.sleep(delay)
                    else:
                        raise
            raise last_exception  # type: ignore
        return wrapper
    return decorator


def check_disk_space(path: Path | str, required_bytes: int) -> bool:
    """
    Check if there's enough disk space at the given path.

    Args:
        path: Path to check (uses parent if file doesn't exist)
        required_bytes: Required space in bytes

    Returns:
        True if enough space, False otherwise
    """
    path = Path(path)
    check_path = path.parent if path.exists() else path
    while not check_path.exists():
        check_path = check_path.parent

    try:
        stat = shutil.disk_usage(check_path)
        return stat.free >= required_bytes
    except OSError:
        return True  # Assume OK if we can't check


def format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PipelineError(Exception):
    """Recoverable pipeline error."""
    def __init__(self, step: str, highlight_id: Optional[int], message: str,
                 recoverable: bool = True):
        self.step = step
        self.highlight_id = highlight_id
        self.recoverable = recoverable
        super().__init__(f"[{step}] highlight={highlight_id}: {message}")


class FatalPipelineError(PipelineError):
    """Unrecoverable error — stops the entire pipeline."""
    def __init__(self, step: str, message: str):
        super().__init__(step, None, message, recoverable=False)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Optional[str] = None, name: str = "pipeline") -> logging.Logger:
    """Initialize logging system."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(log_dir, "pipeline.log"), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def setup_highlight_logging(highlight_dir: str) -> logging.Logger:
    """Set up independent logging for a single highlight."""
    log_path = os.path.join(highlight_dir, "render.log")
    logger = logging.getLogger(os.path.basename(highlight_dir))
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

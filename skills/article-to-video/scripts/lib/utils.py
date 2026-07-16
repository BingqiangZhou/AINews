"""Re-export shim for the cross-skill shared utils.

The canonical implementation lives at
``whisper-transcribe/scripts/lib/utils.py`` (its canonical home). This shim
lets the 5 sequential CLI scripts in ``article-to-video/scripts/`` keep doing
``from lib.utils import ...`` while sharing a single source of truth with
whisper-transcribe.

NOTE: ``article-to-video`` also keeps its own ``lib/caption_align.py``
(vendored from the archived highlight-render-hyperframes skill) — that module
is *not* shared, so it stays as a real local file. Two same-named ``lib``
packages can't both win ``sys.path``, so utils is loaded via importlib by
absolute path and re-exported here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# skills/whisper-transcribe/scripts/lib/utils.py — resolve relative to this file.
# _THIS_DIR = .../article-to-video/scripts/lib → parent×3 = skills/
_THIS_DIR = Path(__file__).resolve().parent
_WT_UTILS = (
    _THIS_DIR.parent.parent.parent  # skills/
    / "whisper-transcribe" / "scripts" / "lib" / "utils.py"
)

_spec = importlib.util.spec_from_file_location("_wt_lib_utils", str(_WT_UTILS))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export the full public surface so `from lib.utils import X` keeps working.
setup_windows_encoding = _mod.setup_windows_encoding
load_config = _mod.load_config
get_config = _mod.get_config
get_ffprobe_path = _mod.get_ffprobe_path
get_ffmpeg_path = _mod.get_ffmpeg_path
write_json = _mod.write_json
save_json = _mod.save_json
read_json = _mod.read_json
probe_duration = _mod.probe_duration
retry_with_backoff = _mod.retry_with_backoff
check_disk_space = _mod.check_disk_space
format_size = _mod.format_size
PipelineError = _mod.PipelineError
FatalPipelineError = _mod.FatalPipelineError
setup_logging = _mod.setup_logging
setup_highlight_logging = _mod.setup_highlight_logging
normalize_for_match = _mod.normalize_for_match
resolve_podcast_path = _mod.resolve_podcast_path

__all__ = [name for name in dir(_mod) if not name.startswith("_")]

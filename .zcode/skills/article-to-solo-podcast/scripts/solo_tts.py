"""
solo_tts.py — 单人播客 TTS。

**单次合成**：全文一次性丢给 mimo，不拆段、不拼接。整段音色/语气最一致，
没有分段边界处的漂移和节奏断裂——单人独白最该避免的就是拼接缝。

复用：from tts-generation/scripts/mimo_tts.py import synthesize

Usage:
  python solo_tts.py --input 播客_脚本.txt --output 播客_TTS.mp3
  python solo_tts.py --input ... --output ... --no-loudnorm
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# --- 定位 tts-generation/scripts 以 import synthesize ---
SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = Path(__file__).resolve().parents[2]  # .zcode/skills
TTS_SCRIPTS = SKILLS_DIR / "tts-generation" / "scripts"
sys.path.insert(0, str(TTS_SCRIPTS))
try:
    from mimo_tts import synthesize  # noqa: E402
except ImportError as e:
    sys.stderr.write(f"[solo_tts] 无法 import synthesize from {TTS_SCRIPTS}: {e}\n")
    sys.exit(1)

# 同目录的 extract_sections（剥离 [SECTION:N] 标记 + 记录偏移）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_sections import extract_sections  # noqa: E402


def load_config():
    with open(SKILL_ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def nonws_len(text):
    return len(re.sub(r"\s", "", text))


def resolve_ref(ref):
    p = Path(ref)
    if not p.is_absolute():
        p = (SKILL_ROOT / ref).resolve()
    return p


def run_ffmpeg(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {r.returncode}):\n{' '.join(cmd)}\n"
            f"stderr:\n{r.stderr.decode('utf-8', errors='replace')}"
        )
    return r


def report_duration(path):
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    ).stdout.strip()
    size_mb = os.path.getsize(path) / 1024 / 1024
    sys.stderr.write(
        f"[solo_tts] DONE: {path}\n"
        f"  duration={float(dur):.1f}s  size={size_mb:.1f}MB\n"
    )


def synth_single(text, output_mp3, tts, api_key, loudnorm=True):
    """全文一次合成 → wav → (loudnorm) → mp3。全在无中文 temp 目录，避开 ffmpeg 中文路径坑。"""
    tmpdir = tempfile.mkdtemp(prefix="solo_tts_")
    try:
        wav = os.path.join(tmpdir, "full.wav")
        t0 = time.time()
        sys.stderr.write(
            f"[solo_tts] single-shot: {nonws_len(text)} chars, "
            f"timeout={tts.get('per_chunk_timeout', 300)}s\n"
        )
        synthesize(
            text, wav,
            voice=tts["voice"], clone=tts.get("clone", True),
            ref_audio=str(resolve_ref(tts["ref_audio"])),
            model=tts["model"], api_key=api_key, fmt="wav",
            timeout=tts.get("per_chunk_timeout", 300),
        )
        sys.stderr.write(f"[solo_tts] synth done in {time.time() - t0:.0f}s\n")

        raw_mp3 = os.path.join(tmpdir, "out.mp3")
        af = [] if not loudnorm else ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
        run_ffmpeg(["ffmpeg", "-y", "-i", wav] + af +
                   ["-c:a", "libmp3lame", "-b:a", tts.get("bitrate", "320k"),
                    "-ar", "48000", "-f", "mp3", raw_mp3])

        os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)
        shutil.copy(raw_mp3, output_mp3)
        report_duration(output_mp3)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Solo podcast TTS (single-shot)")
    ap.add_argument("--input", required=True, help="播客_脚本.txt")
    ap.add_argument("--output", required=True, help="输出 MP3（可为中文路径）")
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-loudnorm", action="store_true", help="跳过 -16 LUFS 响度归一化")
    args = ap.parse_args()

    cfg = load_config() if not args.config else json.loads(Path(args.config).read_text(encoding="utf-8"))
    tts = cfg["tts"]
    env = cfg["environment"]
    api_key = os.environ.get(env["mimo_api_key_env"])
    if not api_key:
        sys.stderr.write(f"[solo_tts] {env['mimo_api_key_env']} 未设置\n")
        sys.exit(1)

    text = Path(args.input).read_text(encoding="utf-8").strip()

    # 剥离 [SECTION:N] 标记（TTS 不认识），同时落盘 sections.json + script_clean.txt
    # 供 article-to-video 按插图分段切场景。无标记时 clean=原文，sections=[]。
    clean_text, sections = extract_sections(text)
    if sections:
        script_dir = Path(args.input).parent
        sections_path = script_dir / "sections.json"
        sections_path.write_text(
            json.dumps({"sections": sections}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        # clean script 落 temp/（sections.json 的 char 偏移基于此文本）
        clean_path = script_dir / "temp" / "script_clean.txt"
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        clean_path.write_text(clean_text, encoding="utf-8")
        sys.stderr.write(
            f"[solo_tts] {len(sections)} 节标记 → {sections_path.name} + {clean_path.name}\n"
        )
    text = clean_text
    loudnorm = not args.no_loudnorm

    try:
        synth_single(text, args.output, tts, api_key, loudnorm)
    except Exception as e:
        sys.stderr.write(f"[solo_tts] 单次合成失败（{e}）\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

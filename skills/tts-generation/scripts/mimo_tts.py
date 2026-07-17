"""
MiMo-V2.5-TTS wrapper for the tts-generation skill.

Usage:
  # Built-in voice mode (default)
  python mimo_tts.py --input text.txt --output audio.mp3

  # Inline text mode (no file needed)
  python mimo_tts.py --text "要合成的文本" --output audio.mp3

  # Voice clone mode (use project reference audio)
  python mimo_tts.py --input text.txt --output audio.mp3 --clone

  # Voice clone with custom reference audio
  python mimo_tts.py --input text.txt --output audio.mp3 --clone --ref my_voice.wav

Options:
  --input      Input text file path (mutually exclusive with --text)
  --text       Inline text to synthesize (mutually exclusive with --input)
  --voice      MiMo built-in voice name (default: 苏打)
  --clone      Use voice cloning instead of built-in voice
  --ref        Reference audio file for cloning (default: voice_ref.wav in same dir)
  --model      MiMo model ID (auto-selected if omitted)
  --style      Style instruction for user message (optional)
  --api-key    API key (or set MIMO_API_KEY env var)
  --format     Output audio format (default: mp3)
"""

import argparse
import base64
import os
import subprocess
import sys
import tempfile

from openai import OpenAI

API_BASE = "https://api.xiaomimimo.com/v1"
MODEL_BUILTIN = "mimo-v2.5-tts"
MODEL_CLONE = "mimo-v2.5-tts-voiceclone"
DEFAULT_VOICE = "苏打"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# voice_ref.wav 的单一权威源就在本 skill scripts/ 下（TTS 克隆参考音频）。
# 其它 skill（article-to-solo-podcast）通过相对路径引用本文件。
DEFAULT_REF_AUDIO = os.path.join(SCRIPT_DIR, "voice_ref.wav")


def synthesize(text: str, output_path: str, *, voice: str = DEFAULT_VOICE,
               clone: bool = False, ref_audio: str | None = None,
               model: str | None = None,
               style: str | None = None, api_key: str = "",
               fmt: str = "mp3", timeout: float = 120.0) -> str:
    # timeout + max_retries on the client so transient network/API errors are
    # retried automatically instead of surfacing as opaque unrecoverable failures.
    client = OpenAI(
        api_key=api_key,
        base_url=API_BASE,
        timeout=timeout,
        max_retries=3,
    )

    # MiMo TTS 的非标准约定（见官方文档 speech-synthesis-v2.5）：目标文本必须放在
    # role=assistant 的 content 里，user 消息携带风格指令。user 消息本身是可选参数，
    # 但官方 voiceclone 示例在无风格时仍发空串 user 消息——这里与之保持一致，发空串
    # 而非省略，避免某些 OpenAI 兼容层对"仅 assistant 消息"或"无 user 消息"的行为不一致。
    messages = []
    if style:
        messages.append({"role": "user", "content": style})
    else:
        messages.append({"role": "user", "content": ""})
    messages.append({"role": "assistant", "content": text})

    if clone:
        ref_path = ref_audio or DEFAULT_REF_AUDIO
        with open(ref_path, "rb") as f:
            voice_bytes = f.read()
        voice_b64 = base64.b64encode(voice_bytes).decode("utf-8")
        voice_param = f"data:audio/wav;base64,{voice_b64}"
        selected_model = model or MODEL_CLONE
    else:
        voice_param = voice
        selected_model = model or MODEL_BUILTIN

    completion = client.chat.completions.create(
        model=selected_model,
        messages=messages,
        audio={"format": "wav", "voice": voice_param},
    )

    audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)

    # Atomic write: render to a sibling .tmp file, then os.replace into place so a
    # crash or ffmpeg failure never leaves a half-written / corrupt output behind.
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if fmt == "wav":
        tmp_path = output_path + ".tmp"
        try:
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)
            os.replace(tmp_path, output_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        return output_path

    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_mp3 = output_path + ".tmp"
    try:
        tmp_wav.write(audio_bytes)
        tmp_wav.close()
        # -f mp3 forces the output muxer explicitly: tmp_mp3 ends in ".tmp" (atomic-write
        # suffix), and ffmpeg infers the container from the file extension, so without
        # -f it can't pick a muxer and fails with "Invalid argument" (returncode -22).
        cmd = ["ffmpeg", "-y", "-i", tmp_wav.name, "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "320k", "-f", "mp3", tmp_mp3]
        # Surface ffmpeg's stderr on failure instead of swallowing it: check=True with
        # capture_output=True hides the real reason behind an opaque returncode.
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ffmpeg WAV->MP3 conversion failed (exit {result.returncode}). "
                f"API returned {len(audio_bytes)} audio bytes. ffmpeg stderr:\n{stderr}"
            )
        os.replace(tmp_mp3, output_path)
    except Exception:
        if os.path.exists(tmp_mp3):
            os.unlink(tmp_mp3)
        raise
    finally:
        if os.path.exists(tmp_wav.name):
            os.unlink(tmp_wav.name)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="MiMo-V2.5-TTS synthesis")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Input text file path")
    input_group.add_argument("--text", help="Inline text to synthesize")
    parser.add_argument("--output", required=True, help="Output audio file path")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Built-in voice name (default: {DEFAULT_VOICE})")
    parser.add_argument("--clone", action="store_true", help="Use voice cloning mode")
    parser.add_argument("--ref", default=None, help="Reference audio for cloning (default: voice_ref.wav in same dir)")
    parser.add_argument("--model", default=None, help="Model ID (auto-selected if omitted)")
    parser.add_argument("--style", default=None, help="Style instruction")
    parser.add_argument("--api-key", default=None, help="API key (or set MIMO_API_KEY)")
    parser.add_argument("--format", default="mp3", choices=["mp3", "wav"], help="Output format")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("MIMO_API_KEY")
    if not api_key:
        print("Error: MIMO_API_KEY not set. Use --api-key or set env var.", file=sys.stderr)
        sys.exit(1)

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text.strip()
    if not text:
        print("Error: input text is empty.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    synthesize(text, args.output, voice=args.voice, clone=args.clone,
               ref_audio=args.ref, model=args.model, style=args.style,
               api_key=api_key, fmt=args.format)
    mode = "clone" if args.clone else "builtin"
    print(f"Saved ({mode}): {args.output}")


if __name__ == "__main__":
    main()

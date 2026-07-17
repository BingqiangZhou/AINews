"""
duo_tts.py — 双人对话播客 TTS。

**双音色分段合成**：双主持（A=苏打、B=冰糖）无法一次合成两种音色，必须按角色标注
（`A：`/`B：`）切段 → 每 turn 用对应 MiMo 内置音色合成 → ffmpeg 拼接（turn 间插静音）
→ 全局一次 loudnorm。turn 级合成 + 拼接是双人播客的唯一可行路径。

复用：from tts-generation/scripts/mimo_tts.py import synthesize

脚本格式（输入 播客_脚本.txt）：
    [SECTION:0]            ← 分节标记（独占一行，TTS 前剥离）
    A：这里是主播A的台词    ← 角色标注（A=苏打音色）
    B：这里是主播B的台词    ← 角色标注（B=冰糖音色）

输出：
    播客_TTS.mp3          ← 拼接后的完整音频（loudnorm -16 LUFS）
    sections.json        ← 每节在 clean 文本的字符偏移（供 article-to-video）
    temp/script_clean.txt ← 剥离 [SECTION:N] + 角色标注的纯文本（给 Whisper 字幕对齐）

关键：sections.json 的字符偏移基于 script_clean.txt（剥了 section 标记 + 角色标注），
保证下游 article-to-video 的 Whisper 字幕对齐正确（转录文本 = clean 文本，无标注干扰）。

Usage:
  python duo_tts.py --input 播客_脚本.txt --output 播客_TTS.mp3
  python duo_tts.py --input ... --output ... --no-loudnorm
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
SKILLS_DIR = Path(__file__).resolve().parents[2]  # skills/
TTS_SCRIPTS = SKILLS_DIR / "tts-generation" / "scripts"
sys.path.insert(0, str(TTS_SCRIPTS))
try:
    from mimo_tts import synthesize  # noqa: E402
except ImportError as e:
    sys.stderr.write(f"[duo_tts] 无法 import synthesize from {TTS_SCRIPTS}: {e}\n")
    sys.exit(1)

# 同目录的 extract_sections（剥离 [SECTION:N] 标记 + 记录偏移）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_sections import extract_sections  # noqa: E402


def load_config():
    with open(SKILL_ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def nonws_len(text):
    return len(re.sub(r"\s", "", text))


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
        f"[duo_tts] DONE: {path}\n"
        f"  duration={float(dur):.1f}s  size={size_mb:.1f}MB\n"
    )


# --- 角色标注解析 ---

# 角色标注行：行首 A：/B：/a：/b：（全角冒号），冒号后即台词。
# 允许前置少量空白。冒号用全角 ：(\uff1a)。
ROLE_LINE_RE = re.compile(r"^\s*([AaＢbBｂ])\s*[\uff1a:]\s?(.*)$")

# 兼容全角字母 A(a Ａａ) B(b Ｂｂ) —— 实际脚本应统一用半角 A/B，但容忍常见变体。
ROLE_CANONICAL = {
    "A": "a", "a": "a", "Ａ": "a", "ａ": "a",
    "B": "b", "b": "b", "Ｂ": "b", "ｂ": "b",
}


def parse_turns(text):
    """把含角色标注的脚本解析成 turn 列表 + clean 文本（给 Whisper 字幕对齐）。

    输入文本已剥 [SECTION:N] 标记（extract_sections 产出的 clean_text）。
    但 extract_sections 不剥角色标注——这里在 clean_text 基础上再剥角色标注，
    产出**最终给 TTS 合成的 turn 序列** + **给字幕对齐的纯文本**。

    一个 turn = 同一角色的连续台词段（同角色连续多段合成一次，音色最一致；
    角色切换即 turn 边界）。空行不切 turn（同角色跨空行仍属同一 turn）。

    Returns:
        turns: [{"role": "a"|"b", "text": str}, ...]
        clean_for_align: str  # 剥了角色标注的纯文本（== 各 turn text 用换行拼接，
                              #   与合成音频内容一致，供 Whisper 字幕对齐）
    """
    turns = []
    cur_role = None
    cur_lines = []

    def flush():
        nonlocal cur_role, cur_lines
        if cur_role is not None and cur_lines:
            text = "\n".join(cur_lines).strip()
            if text:
                turns.append({"role": cur_role, "text": text})
        cur_role = None
        cur_lines = []

    for raw_line in text.splitlines():
        m = ROLE_LINE_RE.match(raw_line)
        if m:
            role_char = m.group(1)
            role = ROLE_CANONICAL.get(role_char)
            if role is None:
                # 未知角色标注（如 C：），当作普通文本并入当前 turn（容错）
                cur_lines.append(raw_line.strip())
                continue
            content = m.group(2)
            if role != cur_role:
                flush()
                cur_role = role
            cur_lines.append(content.strip())
        else:
            stripped = raw_line.strip()
            if not stripped:
                # 空行：不切 turn，但也不并入（避免 turn 内多余空行）
                continue
            # 非角色标注的实质行（理论上 validate_duo_script 已拦截，
            # 此处容错：并入当前 turn，否则作为无角色旁白单独成 turn）
            if cur_role is not None:
                cur_lines.append(stripped)
            else:
                # 无当前角色（开头无标注）——作为 'a' 兜底（极少见）
                cur_role = "a"
                cur_lines.append(stripped)
    flush()

    # clean_for_align：与合成音频内容完全一致（各 turn text 换行拼接，无角色标注）
    clean_for_align = "\n".join(t["text"] for t in turns)
    return turns, clean_for_align


# --- 双音色分段合成 + 拼接 ---

def synth_turn(turn, voices, api_key, out_wav, model, per_turn_timeout):
    """单 turn 合成：role→对应内置音色，clone=False，输出 wav。"""
    voice = voices[turn["role"]]
    synthesize(
        turn["text"], out_wav,
        voice=voice, clone=False,
        model=model, api_key=api_key, fmt="wav",
        timeout=per_turn_timeout,
    )


def make_silence(duration_s, out_wav):
    """生成指定时长的静音 wav（与 turn wav 同参数：44100 单声道 16bit）。"""
    run_ffmpeg([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=44100",
        "-t", str(duration_s), "-c:a", "pcm_s16le", out_wav,
    ])


def synth_and_concat(turns, voices, api_key, model, output_mp3,
                     turn_gap_ms, loudnorm, bitrate, per_turn_timeout):
    """逐 turn 合成 wav → ffmpeg concat（turn 间插静音）→ loudnorm → mp3。

    全在无中文 temp 目录，避开 ffmpeg 中文路径坑。
    """
    tmpdir = tempfile.mkdtemp(prefix="duo_tts_")
    try:
        # 1. 逐 turn 合成（串行，失败重试 2 次）
        turn_wavs = []
        t0 = time.time()
        sys.stderr.write(
            f"[duo_tts] 合成 {len(turns)} turns (A={voices['a']}, B={voices['b']}), "
            f"gap={turn_gap_ms}ms, timeout={per_turn_timeout}s\n"
        )
        for i, turn in enumerate(turns):
            wav = os.path.join(tmpdir, f"turn_{i:04d}_{turn['role']}.wav")
            last_err = None
            for attempt in range(3):
                try:
                    synth_turn(turn, voices, api_key, wav, model, per_turn_timeout)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    sys.stderr.write(
                        f"[duo_tts] turn {i} ({turn['role']}) attempt {attempt+1} 失败: {e}\n"
                    )
                    time.sleep(2)
            if last_err is not None:
                raise RuntimeError(f"turn {i} ({turn['role']}) 合成失败（重试3次）: {last_err}")
            turn_wavs.append(wav)
        sys.stderr.write(f"[duo_tts] {len(turn_wavs)} turns synth done in {time.time()-t0:.0f}s\n")

        # 2. 生成静音片段
        gap_s = turn_gap_ms / 1000.0
        silence_wav = os.path.join(tmpdir, "silence.wav")
        make_silence(gap_s, silence_wav)

        # 3. 生成 concat 列表（turn 间插静音）：turn0 silence turn1 silence turn2 ...
        concat_list = os.path.join(tmpdir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for i, wav in enumerate(turn_wavs):
                # Windows 路径在 concat 列表里需转义反斜杠或用正斜杠；用正斜杠最稳
                f.write(f"file '{wav.replace(os.sep, '/')}'\n")
                if i < len(turn_wavs) - 1:
                    f.write(f"file '{silence_wav.replace(os.sep, '/')}'\n")

        # 4. concat → 一个 wav
        full_wav = os.path.join(tmpdir, "full.wav")
        run_ffmpeg([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:a", "pcm_s16le", full_wav,
        ])

        # 5. loudnorm（全局一次）+ 转 mp3
        raw_mp3 = os.path.join(tmpdir, "out.mp3")
        af = [] if not loudnorm else ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
        run_ffmpeg(["ffmpeg", "-y", "-i", full_wav] + af +
                   ["-c:a", "libmp3lame", "-b:a", bitrate,
                    "-ar", "48000", "-f", "mp3", raw_mp3])

        os.makedirs(os.path.dirname(os.path.abspath(output_mp3)), exist_ok=True)
        shutil.copy(raw_mp3, output_mp3)
        report_duration(output_mp3)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Duo podcast TTS (per-turn dual-voice + concat)")
    ap.add_argument("--input", required=True, help="播客_脚本.txt（含 A：/B： 角色标注 + [SECTION:N]）")
    ap.add_argument("--output", required=True, help="输出 MP3（可为中文路径）")
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-loudnorm", action="store_true", help="跳过 -16 LUFS 响度归一化")
    args = ap.parse_args()

    cfg = load_config() if not args.config else json.loads(Path(args.config).read_text(encoding="utf-8"))
    tts = cfg["tts"]
    env = cfg["environment"]
    voices = tts["voices"]
    api_key = os.environ.get(env["mimo_api_key_env"])
    if not api_key:
        sys.stderr.write(f"[duo_tts] {env['mimo_api_key_env']} 未设置\n")
        sys.exit(1)

    text = Path(args.input).read_text(encoding="utf-8").strip()

    # 1. 剥离 [SECTION:N] 标记（TTS 不认识），落盘 sections.json（基于 clean 文本）
    #    + script_clean.txt。extract_sections 返回的 clean_text 仍含角色标注。
    clean_with_roles, sections = extract_sections(text)
    script_dir = Path(args.input).parent
    temp_dir = script_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 2. 解析角色标注 → turns + 最终纯文本（无角色标注，给 Whisper 字幕对齐）
    turns, clean_for_align = parse_turns(clean_with_roles)

    if not turns:
        sys.stderr.write("[duo_tts] 未解析出任何 turn（脚本无 A：/B： 角色标注？）\n")
        sys.exit(1)

    # 3. sections.json 的字符偏移必须基于 clean_for_align（剥了 section 标记 + 角色标注）。
    #    extract_sections 产出的偏移基于 clean_with_roles（含角色标注），与 clean_for_align
    #    不一致——需要重算偏移。方法：以 clean_with_roles 的 section 边界文本，
    #    在 clean_for_align 里重新定位。
    sections_clean = _recompute_section_offsets(sections, clean_with_roles, clean_for_align)

    if sections_clean:
        sections_path = script_dir / "sections.json"
        sections_path.write_text(
            json.dumps({"sections": sections_clean}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        sys.stderr.write(
            f"[duo_tts] {len(sections_clean)} 节 → {sections_path.name}（偏移基于 script_clean.txt）\n"
        )

    # 4. clean script（无 section 标记、无角色标注）落 temp/script_clean.txt
    clean_path = temp_dir / "script_clean.txt"
    clean_path.write_text(clean_for_align, encoding="utf-8")
    sys.stderr.write(
        f"[duo_tts] {len(turns)} turns, clean {nonws_len(clean_for_align)} 字 → {clean_path.name}\n"
    )

    # 5. 双音色分段合成 + 拼接
    loudnorm = not args.no_loudnorm
    try:
        synth_and_concat(
            turns, voices, api_key, tts["model"], args.output,
            tts.get("turn_gap_ms", 250), loudnorm,
            tts.get("bitrate", "320k"),
            tts.get("per_turn_timeout", 300),
        )
    except Exception as e:
        sys.stderr.write(f"[duo_tts] 合成/拼接失败（{e}）\n")
        sys.exit(1)


def _recompute_section_offsets(sections, clean_with_roles, clean_for_align):
    """重算 sections 偏移，使其基于 clean_for_align（无角色标注）。

    extract_sections 的偏移基于 clean_with_roles（剥了 section 标记但含角色标注）。
    我们需要偏移基于 clean_for_align（剥了 section 标记 + 角色标注），这样下游
    article-to-video 用 Whisper 转录 clean_for_align 文本时，偏移才对得上。

    方法：对每个 section，取它在 clean_with_roles 里的 [char_start, char_end) 文本，
    剥掉角色标注后，在 clean_for_align 里顺序查找其位置（section 文本唯一且按序出现）。
    """
    if not sections:
        return []
    # 角色标注在 clean_for_align 里已剥除，剥一段含标注文本的函数
    def strip_roles(s):
        out = []
        for line in s.splitlines():
            m = ROLE_LINE_RE.match(line)
            out.append(m.group(2).strip() if m else line.strip())
        return "\n".join(out).strip()

    result = []
    search_from = 0
    for sec in sections:
        seg_text_with_roles = clean_with_roles[sec["char_start"]:sec["char_end"]]
        seg_text_clean = strip_roles(seg_text_with_roles)
        if not seg_text_clean:
            # 空 section（如纯标记），用上一个搜索位置
            result.append({"index": sec["index"], "char_start": search_from, "char_end": search_from})
            continue
        pos = clean_for_align.find(seg_text_clean, search_from)
        if pos == -1:
            # 兜底：容错失败（角色标注剥离导致文本微差），用 search_from 起始占位
            sys.stderr.write(
                f"[duo_tts] WARNING: section {sec['index']} 偏移重算未匹配，用顺序占位\n"
            )
            result.append({"index": sec["index"], "char_start": search_from, "char_end": search_from})
            continue
        end = pos + len(seg_text_clean)
        result.append({"index": sec["index"], "char_start": pos, "char_end": end})
        search_from = end
    return result


if __name__ == "__main__":
    main()

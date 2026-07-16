#!/usr/bin/env python3
"""
compose_video.py — 阶段 5：合成

拼接封面 + 各场景片段，叠加播客音频和字幕，产出最终视频。

流程:
  1. concat 封面 + 各场景片段 → 无声视频
  2. 叠加播客音频 + ASS 字幕烧录 → 最终视频
  3. ffprobe 校验

Usage:
  python compose_video.py --article-dir <文章目录>
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent  # 本 skill scripts/
sys.path.insert(0, str(SCRIPTS_DIR))  # lib.* 已内化至本 skill scripts/lib/

from lib.utils import setup_windows_encoding, read_json, resolve_podcast_path  # noqa: E402


def run_ffmpeg(cmd: list[str], ffmpeg_bin: str, timeout: int = 600) -> str:
    """运行 ffmpeg 命令，失败抛异常。"""
    print(f"  [compose] $ {ffmpeg_bin} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if result.returncode != 0:
        print(f"  [compose] ffmpeg stdout: {result.stdout[-500:]}", file=sys.stderr)
        print(f"  [compose] ffmpeg stderr: {result.stderr[-1000:]}", file=sys.stderr)
        raise RuntimeError(f"ffmpeg 失败 (exit {result.returncode})")
    return result.stdout


def probe_streams(video_path: Path, ffprobe_bin: str) -> dict:
    """ffprobe 查询视频流信息。"""
    cmd = [
        ffprobe_bin, "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
    return json.loads(result.stdout)


def compose(article_dir: Path, config: dict):
    """主合成逻辑。"""
    video_dir = article_dir / "_video"
    segments_dir = video_dir / "segments"
    ffmpeg_bin = os.environ.get("AINews_FFMPEG") or config["environment"]["ffmpeg"]
    ffprobe_bin = os.environ.get("AINews_FFPROBE") or config["environment"]["ffprobe"]

    scenes_data = read_json(video_dir / "scenes.json")
    # 播客音频：优先用 scenes.json 记录的相对路径；缺失/旧 scenes.json 则 resolver 兜底
    audio_rel = scenes_data.get("audio_path", "播客_TTS.mp3")
    audio_path = article_dir / audio_rel
    if not audio_path.exists():
        audio_path = resolve_podcast_path(article_dir, "播客_TTS.mp3")

    if not audio_path.exists():
        raise RuntimeError(f"播客音频不存在: {audio_path}（已查找 _podcast/ 与文章根目录）")

    # ── 1. 收集要拼接的片段（按顺序）──
    segments_to_concat = []

    # 封面
    cover = scenes_data.get("cover_scene")
    if cover and config["cover"]["enabled"]:
        cover_mp4 = segments_dir / "cover.mp4"
        if cover_mp4.exists():
            segments_to_concat.append(cover_mp4)
        else:
            print(f"  [compose] WARNING: 封面片段不存在 {cover_mp4}，跳过")

    # 各场景
    scenes = scenes_data.get("scenes", [])
    for scene in scenes:
        seg_path = segments_dir / f"scene_{scene['id']:03d}.mp4"
        if seg_path.exists():
            segments_to_concat.append(seg_path)
        else:
            print(f"  [compose] WARNING: 场景片段不存在 {seg_path}，跳过场景 {scene['id']}")

    if not segments_to_concat:
        raise RuntimeError("无可用视频片段（segments/ 为空）")

    # ── 2. concat 拼接（stream copy，快）──
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                     encoding="utf-8", dir=str(video_dir / "temp")) as f:
        for seg in segments_to_concat:
            # ffmpeg concat 要求正斜杠
            seg_str = str(seg.resolve()).replace("\\", "/")
            f.write(f"file '{seg_str}'\n")
        concat_list = Path(f.name)

    video_silent = video_dir / "temp" / "video_silent.mp4"
    print(f"  [compose] 拼接 {len(segments_to_concat)} 个片段 ...")
    run_ffmpeg([
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(video_silent),
    ], ffmpeg_bin)

    # ── 3. 叠加音频 + 字幕烧录 ──
    ass_path = video_dir / "subtitles.ass"
    output_path = video_dir / "公众号_视频.mp4"

    # subtitles 滤镜需要 ass 文件路径，Windows 路径要转义反斜杠和冒号
    # ffmpeg subtitles 滤镜的路径需要用正斜杠，且特殊字符要转义
    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{ass_filter_path}'"

    # 音频处理：
    # - 无封面时（cover.enabled=false）：裁掉 TTS 音频开头的静音段（由 Whisper 检测的第一条字幕 startMs 决定），
    #   使人声从视频第 0 秒开始，避免开头一大段无声。
    # - 有封面时（cover.enabled=true）：保持旧逻辑，在音频开头垫等量静音对齐封面片头。
    af = None
    if cover and config["cover"]["enabled"]:
        # 有封面：adelay 垫静音对齐封面
        cover_offset_ms = int(cover.get("duration_ms", 0))
        if cover_offset_ms > 0:
            af = f"adelay=delays={cover_offset_ms}:all=1"
    else:
        # 无封面：裁掉音频开头静音（TTS 自带的开头空白）
        timeline_path = video_dir / "temp" / "timeline_captions.json"
        if timeline_path.exists():
            timeline = read_json(timeline_path)
            captions = timeline.get("captions", [])
            if captions:
                lead_silence_ms = int(captions[0].get("startMs", 0))
                if lead_silence_ms > 200:  # 超过 200ms 才裁（避免微小偏移）
                    lead_silence_s = lead_silence_ms / 1000
                    af = f"atrim=start={lead_silence_s},asetpts=PTS-STARTPTS"
                    print(f"  [compose] 裁掉音频开头静音 {lead_silence_ms}ms")

    print(f"  [compose] 叠加音频 + 字幕烧录 ...")
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(video_silent),
        "-i", str(audio_path),
        "-vf", vf,
    ]
    if af:
        cmd += ["-af", af]
    cmd += [
        "-c:v", config["video"]["codec"],
        "-preset", config["video"]["preset"],
        "-crf", str(config["video"]["crf"]),
        "-pix_fmt", config["video"]["pix_fmt"],
        "-c:a", "aac",
        "-b:a", config["video"]["audio_bitrate"],
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, ffmpeg_bin, timeout=1800)  # 长视频给 30 分钟

    # ── 4. ffprobe 校验 ──
    info = probe_streams(output_path, ffprobe_bin)
    streams = info.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(info.get("format", {}).get("duration", 0))
    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"  [compose] 校验: video={has_video}, audio={has_audio}, "
          f"duration={duration:.1f}s, size={size_mb:.1f}MB")

    if not has_video or not has_audio:
        raise RuntimeError(f"输出校验失败: video={has_video}, audio={has_audio}")

    # 清理中间文件
    concat_list.unlink(missing_ok=True)
    video_silent.unlink(missing_ok=True)

    return output_path, duration, size_mb


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 5：合成（concat + 音轨 + 字幕 → 最终视频）")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    config = read_json(SKILL_DIR / "config.json")

    # 校验输入
    if not (article_dir / "_video" / "scenes.json").exists():
        print("ERROR: scenes.json 不存在，请先运行阶段 2-3", file=sys.stderr)
        sys.exit(1)
    if not (article_dir / "_video" / "subtitles.ass").exists():
        print("ERROR: subtitles.ass 不存在，请先运行阶段 4", file=sys.stderr)
        sys.exit(1)

    output, duration, size_mb = compose(article_dir, config)
    print(f"\n  ✅ 视频生成完成: {output}")
    print(f"     时长: {duration:.1f}s | 大小: {size_mb:.1f}MB")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
render_kenburns.py — 阶段 3：Ken Burns 渲染

遍历 scenes.json，每张图用 ffmpeg zoompan 滤镜生成对应时长的视频片段。
图片先 PIL 预处理（center-crop + 模糊背景填充到 16:9），再喂给 ffmpeg。

Usage:
  python render_kenburns.py --article-dir <文章目录>
"""

import argparse
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent  # 本 skill scripts/
sys.path.insert(0, str(SCRIPTS_DIR))  # lib.* 已内化至本 skill scripts/lib/

from lib.utils import setup_windows_encoding, read_json  # noqa: E402

try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def preprocess_image(img_path: Path, out_path: Path, width: int, height: int):
    """把图片预处理成目标尺寸（16:9）。

    策略：如果图片比例和目标一致，直接 resize；否则：
      1. 把原图放大到覆盖目标尺寸 → center-crop
      2. 额外存一份模糊放大版做背景（上下黑边替换为模糊背景）

    这里用简单方案：直接 center-crop（放大覆盖 + 裁剪），不搞模糊背景，
    避免 Ken Burns 平移时露出边缘。zoompan 内部的 scale+crop 会处理。
    """
    if not HAS_PIL:
        return img_path  # 无 PIL 则不预处理，交给 ffmpeg

    with Image.open(img_path) as img:
        img = img.convert("RGB")
        src_w, src_h = img.size
        target_ratio = width / height
        src_ratio = src_w / src_h

        if abs(src_ratio - target_ratio) < 0.01:
            # 比例一致，直接 resize
            resized = img.resize((width, height), Image.LANCZOS)
            resized.save(out_path, "PNG")
        else:
            # center-crop：放大覆盖目标比例后裁剪
            if src_ratio > target_ratio:
                # 原图更宽 → 按高度放大，裁两侧
                new_h = height
                new_w = int(height * src_ratio)
            else:
                # 原图更高 → 按宽度放大，裁上下
                new_w = width
                new_h = int(width / src_ratio)
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - width) // 2
            top = (new_h - height) // 2
            cropped = resized.crop((left, top, left + width, top + height))
            cropped.save(out_path, "PNG")

    return out_path


def build_zoompan_filter(kb_type: str, duration_frames: int, width: int,
                         height: int, config: dict) -> str:
    """根据 Ken Burns 类型构造 ffmpeg zoompan 滤镜链。

    zoompan 语法: z=缩放表达式:x=平移x:y=平移y:d=总帧数:s=输出尺寸:fps
    """
    max_zoom = config["ken_burns"]["max_zoom"]
    min_zoom = config["ken_burns"]["min_zoom"]
    pan_range = config["ken_burns"]["pan_range"]

    # zoom 从 min_zoom 线性增到 max_zoom，每帧增量
    zoom_step = (max_zoom - min_zoom) / max(duration_frames - 1, 1)

    # 各类型的 x/y 表达式（基于输入图 iw/ih 和当前 zoom）
    # 注意：zoompan 的 x/y 是输出画面左上角在输入图上的坐标
    # 居中：x = (iw - iw/zoom) / 2

    center_x = "iw/2-(iw/zoom)/2"
    center_y = "ih/2-(ih/zoom)/2"

    if kb_type == "zoom_in":
        # 缩放放大，居中
        z_expr = f"min(zoom+{zoom_step:.6f},{max_zoom})"
        x_expr = center_x
        y_expr = center_y

    elif kb_type == "zoom_out":
        # 从大缩小到 min_zoom
        z_expr = f"if(eq(on,0),{max_zoom},max(zoom-{zoom_step:.6f},{min_zoom}))"
        x_expr = center_x
        y_expr = center_y

    elif kb_type == "pan_left":
        # 固定缩放，从右往左平移
        z_expr = f"{max_zoom}"
        pan_pixels = f"iw*{pan_range}"
        x_expr = f"({pan_pixels})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "pan_right":
        # 固定缩放，从左往右平移
        z_expr = f"{max_zoom}"
        pan_pixels = f"iw*{pan_range}"
        x_expr = f"(iw-iw/zoom)-({pan_pixels})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "zoom_in_pan_right":
        # 放大 + 从左往右平移
        z_expr = f"min(zoom+{zoom_step:.6f},{max_zoom})"
        start_x = "0"
        end_x = "iw/2-(iw/zoom)/2"
        x_expr = f"{start_x}+({end_x}-{start_x})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "zoom_out_pan_left":
        z_expr = f"if(eq(on,0),{max_zoom},max(zoom-{zoom_step:.6f},{min_zoom}))"
        start_x = "iw/2-(iw/zoom)/2"
        end_x = "iw-iw/zoom"
        x_expr = f"{start_x}+({end_x}-{start_x})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "zoom_in_pan_up":
        z_expr = f"min(zoom+{zoom_step:.6f},{max_zoom})"
        x_expr = center_x
        start_y = "0"
        end_y = "ih/2-(ih/zoom)/2"
        y_expr = f"{start_y}+({end_y}-{start_y})*on/{max(duration_frames-1,1)}"

    elif kb_type == "zoom_in_pan_left":
        z_expr = f"min(zoom+{zoom_step:.6f},{max_zoom})"
        start_x = "iw/2-(iw/zoom)/2"
        end_x = "0"
        x_expr = f"{start_x}+({end_x}-{start_x})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "zoom_out_pan_right":
        z_expr = f"if(eq(on,0),{max_zoom},max(zoom-{zoom_step:.6f},{min_zoom}))"
        start_x = "iw-iw/zoom"
        end_x = "iw/2-(iw/zoom)/2"
        x_expr = f"{start_x}+({end_x}-{start_x})*on/{max(duration_frames-1,1)}"
        y_expr = center_y

    elif kb_type == "zoom_in_slow":
        # 封面用：缓慢放大
        slow_step = (max_zoom - 1.0) / max(duration_frames - 1, 1) * 0.5
        z_expr = f"min(zoom+{slow_step:.6f},{max_zoom})"
        x_expr = center_x
        y_expr = center_y

    elif kb_type == "static":
        # PPT 静态展示：完全不动，固定居中、无缩放无平移
        z_expr = "1"
        x_expr = center_x
        y_expr = center_y

    else:
        # 默认：zoom_in
        z_expr = f"min(zoom+{zoom_step:.6f},{max_zoom})"
        x_expr = center_x
        y_expr = center_y

    # zoompan 滤镜：先 scale 到足够大的尺寸（给 zoom 留余量），再 zoompan
    # scale 到 2 倍目标尺寸，避免 zoompan 放大时画质损失
    scale_w = width * 2
    scale_h = height * 2
    vf = (
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
        f"crop={scale_w}:{scale_h},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={duration_frames}:s={width}x{height}:fps={config['video']['fps']}"
    )
    return vf


def render_segment(img_path: Path, out_path: Path, duration_sec: float,
                   kb_type: str, config: dict, ffmpeg_bin: str):
    """用 ffmpeg 把单张图渲染成视频片段。static 类型完全静止（PPT 展示）。"""
    fps = config["video"]["fps"]
    duration_frames = int(duration_sec * fps)
    if duration_frames < 1:
        duration_frames = 1

    cmd = [
        ffmpeg_bin, "-y",
        "-loop", "1", "-i", str(img_path),
    ]

    if kb_type == "static":
        # PPT 静态展示：图片已由 PIL 预处理到目标尺寸（1920x1080），
        # 不用任何 vf（zoompan 即使 z=1 也会逐帧重采样产生抖动）。
        # 只设 fps + 时长，输出逐帧完全相同的静态画面。
        cmd += ["-r", str(fps)]
    else:
        vf = build_zoompan_filter(kb_type, duration_frames,
                                  config["video"]["width"], config["video"]["height"], config)
        cmd += ["-vf", vf]

    cmd += [
        "-c:v", config["video"]["codec"],
        "-preset", config["video"]["preset"],
        "-crf", str(config["video"]["crf"]),
        "-pix_fmt", config["video"]["pix_fmt"],
        "-t", f"{duration_sec:.3f}",
        "-an",
        "-movflags", "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"  [render] ffmpeg stderr: {result.stderr[-500:]}", file=sys.stderr)
        raise RuntimeError(f"ffmpeg 渲染失败: {out_path.name}")


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 3：Ken Burns 渲染")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    config = read_json(SKILL_DIR / "config.json")
    ffmpeg_bin = config["environment"]["ffmpeg"]

    scenes_data = read_json(article_dir / "_video" / "scenes.json")
    segments_dir = article_dir / "_video" / "segments"
    temp_dir = article_dir / "_video" / "temp" / "preprocessed"
    segments_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    width = config["video"]["width"]
    height = config["video"]["height"]

    # 渲染封面
    cover = scenes_data.get("cover_scene")
    if cover:
        cover_img = article_dir / cover["image"]
        if cover_img.exists():
            cover_out = segments_dir / "cover.mp4"
            # 预处理封面
            if HAS_PIL:
                pp_cover = temp_dir / "cover_pp.png"
                preprocess_image(cover_img, pp_cover, width, height)
                cover_img = pp_cover
            dur_sec = cover["duration_ms"] / 1000
            print(f"  [render] 封面 ({dur_sec:.1f}s, {cover['ken_burns']})")
            render_segment(cover_img, cover_out, dur_sec,
                           cover["ken_burns"], config, ffmpeg_bin)
        else:
            print(f"  [render] WARNING: 封面不存在 {cover_img}，跳过封面")

    # 渲染各场景
    scenes = scenes_data.get("scenes", [])
    for scene in scenes:
        img_path = article_dir / scene["image"]
        if not img_path.exists():
            print(f"  [render] WARNING: 图片不存在 {img_path}，跳过场景 {scene['id']}")
            continue

        # 预处理图片
        if HAS_PIL:
            pp_img = temp_dir / f"scene_{scene['id']:03d}_pp.png"
            preprocess_image(img_path, pp_img, width, height)
            img_path = pp_img

        out_path = segments_dir / f"scene_{scene['id']:03d}.mp4"
        dur_sec = (scene["end_ms"] - scene["start_ms"]) / 1000
        print(f"  [render] 场景 {scene['id']:03d} ({dur_sec:.1f}s, {scene['ken_burns']}, "
              f"{Path(scene['image']).name})")
        render_segment(img_path, out_path, dur_sec,
                       scene["ken_burns"], config, ffmpeg_bin)

    print(f"  [render] DONE → {segments_dir}")


if __name__ == "__main__":
    main()

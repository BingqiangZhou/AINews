#!/usr-id/env python3
"""
plan_scenes.py — 阶段 2：分镜规划

从文章 MD 提取插图引用，与 timeline_captions.json 的字幕时间轴对齐，
规划出每个场景的画面（哪张图）、时间范围、Ken Burns 运动类型。

策略：
  1. 正则提取文章 MD 中的 ![](imgs/NN-xxx.png) 引用（按出现顺序）
  2. 读取播客脚本，按空行分段
  3. 把口播稿按"插图数量"切成 N+1 段
  4. 用文本归一化匹配，在 captions 时间轴里找到每段首句/末句的时间戳
  5. 每段配对应插图，封面作片头，Ken Burns 类型轮换

Usage:
  python plan_scenes.py --article-dir <文章目录>
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent  # 本 skill scripts/
sys.path.insert(0, str(SCRIPTS_DIR))  # lib.* 已内化至本 skill scripts/lib/

from lib.utils import setup_windows_encoding, read_json, write_json, resolve_podcast_path  # noqa: E402
from lib.caption_align import normalize  # noqa: E402

# 插图引用正则：![alt](imgs/NN-xxx.png)
IMG_REF_RE = re.compile(r"!\[([^\]]*)\]\((imgs/[^)]+\.png)\)")

# Ken Burns 运动类型轮换池（避免连续两张同向）
# 默认 static（PPT 静态展示）；如需动态可改回轮换池
KB_ROTATION = [
    "static",
]


def extract_illustrations(article_md_path: Path) -> list[dict]:
    """从文章 MD 提取插图引用列表（按出现顺序）。

    Returns:
        [{"alt": str, "path": str}, ...]  path 相对文章目录
    """
    text = article_md_path.read_text(encoding="utf-8")
    result = []
    for m in IMG_REF_RE.finditer(text):
        result.append({"alt": m.group(1).strip(), "path": m.group(2)})
    return result


def load_podcast_paragraphs(script_path: Path) -> list[str]:
    """读取播客脚本，按空行分段。"""
    text = script_path.read_text(encoding="utf-8").replace("\r", "")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs


def find_caption_time(captions: list[dict], paragraph_text: str,
                      search_from: int = 0) -> tuple[int, int, int]:
    """在 captions 时间轴中找到与口播段落最匹配的字幕区间。

    用归一化文本（去标点空格）做子串匹配。

    Returns:
        (start_ms, end_ms, next_search_index)
        匹配失败时返回 (None, None, search_from)
    """
    norm_para = normalize(paragraph_text)
    if not norm_para:
        return (None, None, search_from)

    # 取段落前 20 字和后 20 字作为搜索锚点（首句和末句）
    head = norm_para[:20]
    tail = norm_para[-20:] if len(norm_para) > 20 else norm_para

    head_idx = None
    tail_idx = None

    # 从 search_from 开始搜索首句
    for i in range(search_from, len(captions)):
        norm_cap = normalize(captions[i].get("text", ""))
        if head and head in norm_cap:
            head_idx = i
            break
        # 也尝试段落更长的前缀匹配（caption 可能包含段落开头的一部分）
        if norm_cap and norm_cap[:10] == norm_para[:10]:
            head_idx = i
            break

    if head_idx is None:
        # 放宽：只匹配前 8 字
        head8 = norm_para[:8]
        for i in range(search_from, len(captions)):
            norm_cap = normalize(captions[i].get("text", ""))
            if head8 and head8 in norm_cap:
                head_idx = i
                break

    if head_idx is None:
        return (None, None, search_from)

    # 从 head_idx 开始搜索末句
    for i in range(head_idx, len(captions)):
        norm_cap = normalize(captions[i].get("text", ""))
        if tail and tail in norm_cap:
            tail_idx = i
            break
        # 如果 caption 的归一化文本是段落的子串的结尾
        if norm_cap and norm_para.endswith(norm_cap[-10:]):
            tail_idx = i
            break

    if tail_idx is None:
        # 末句没匹配到，用 head_idx 所在 caption 的 endMs
        tail_idx = head_idx

    start_ms = captions[head_idx].get("startMs", 0)
    end_ms = captions[tail_idx].get("endMs", 0)
    return (start_ms, end_ms, tail_idx + 1)


def _plan_scenes_from_sections(
    sec_sections: list[dict],
    illustrations: list[dict],
    audio_dur_ms: int,
    config: dict,
    article_dir: Path,
) -> dict | None:
    """从 [SECTION:N] 分节时间轴直接构建场景（跳过脆弱的文本匹配）。

    每个 section = 一个场景，配对应插图（section_index → illustrations 同序）。
    section_index 可能不连续（如 0,1,2,3,4,5），按出现顺序配图。

    Returns:
        plan_scenes 同结构的 dict；失败返回 None。
    """
    if not sec_sections:
        return None
    if not illustrations:
        print("  [plan] WARNING: 文章无插图，section 切场景无法配图")
        return None

    # 优先用 imgs/segments.json 的 illustrations 字段精确配对（section_index → 插图列表）；
    # 无 segments.json 时回退 ordinal 配对（illustrations[i]，假设 section 与插图同序）。
    # 支持一段多图：illustrations 数组有多张时，section 时间段内均分给每张图。
    seg_illustrations_map: dict[int, list[str]] = {}
    segments_json_path = article_dir / "imgs" / "segments.json"
    if segments_json_path.exists():
        try:
            seg_data = read_json(segments_json_path)
            for seg in seg_data.get("segments", []):
                # 优先读 illustrations（数组），回退 illustration（单值，兼容旧数据）
                imgs = seg.get("illustrations")
                if imgs:
                    seg_illustrations_map[seg["index"]] = imgs
                elif seg.get("illustration"):
                    seg_illustrations_map[seg["index"]] = [seg["illustration"]]
            print(f"  [plan] 用 imgs/segments.json 精确配对 "
                  f"({len(seg_illustrations_map)} segment 有插图)")
        except Exception:
            pass  # 读取失败 → 回退 ordinal

    # alt_text 查找辅助：按 path 从 illustrations 找 alt
    alt_by_path = {x["path"]: x["alt"] for x in illustrations}

    # section 按出现顺序（已由 align_captions 保证），配对应插图。
    # 一段多图时：section 的时间段内均分给 N 张图，产 N 个 scene。
    scenes = []
    for i, sec in enumerate(sec_sections):
        sec_idx = sec.get("section_index", i)
        sec_start = sec["start_ms"]
        sec_end = sec["end_ms"]
        # 配图组：优先 segments.json 精确映射（数组）；否则 ordinal（section i → 第 i 张）
        if sec_idx in seg_illustrations_map:
            img_paths = seg_illustrations_map[sec_idx]
        else:
            fallback = illustrations[i] if i < len(illustrations) else illustrations[-1]
            img_paths = [fallback["path"]]

        # 一段 N 张图 → 时间段均分 → N 个 scene
        n = len(img_paths)
        sub_dur = (sec_end - sec_start) / n if n > 0 else 0
        for k, img_path in enumerate(img_paths):
            scene_id = len(scenes)  # 连续编号
            kb_type = KB_ROTATION[scene_id % len(KB_ROTATION)]
            scenes.append({
                "id": scene_id,
                "start_ms": int(sec_start + k * sub_dur),
                "end_ms": int(sec_start + (k + 1) * sub_dur),
                "image": img_path,
                "alt_text": alt_by_path.get(img_path, ""),
                "ken_burns": kb_type,
            })

    if not scenes:
        return None

    # 确保最后一个场景的 end_ms = 音频结束
    scenes[-1]["end_ms"] = audio_dur_ms

    # 时间轴连续化（section 时间戳可能有间隙，同文本匹配路径）
    if len(scenes) >= 2:
        total_scene_ms = sum(s["end_ms"] - s["start_ms"] for s in scenes)
        if total_scene_ms > 0:
            cursor = 0
            for i, sc in enumerate(scenes):
                orig_dur = sc["end_ms"] - sc["start_ms"]
                if i < len(scenes) - 1:
                    scaled = int(orig_dur * audio_dur_ms / total_scene_ms)
                    sc["start_ms"] = cursor
                    sc["end_ms"] = cursor + scaled
                    cursor += scaled
                else:
                    sc["start_ms"] = cursor
                    sc["end_ms"] = audio_dur_ms
            print(f"  [plan] 时间轴连续化: {len(scenes)} 个 section 场景铺满 "
                  f"{audio_dur_ms/1000:.1f}s 音频")

    # 封面场景
    cover_scene = None
    if config["cover"]["enabled"]:
        cover_scene = {
            "duration_ms": int(config["cover"]["duration_sec"] * 1000),
            "image": "公众号_封面.png",
            "ken_burns": config["cover"].get("ken_burns", "zoom_in_slow"),
        }

    # 播客音频相对路径（同主 plan_scenes 逻辑）
    audio_abs = resolve_podcast_path(article_dir, "播客_TTS.mp3")
    try:
        audio_rel = str(audio_abs.relative_to(article_dir.resolve())).replace("\\", "/")
    except ValueError:
        audio_rel = str(audio_abs)

    return {
        "cover_scene": cover_scene,
        "scenes": scenes,
        "audio_path": audio_rel,
        "total_duration_ms": audio_dur_ms + (cover_scene["duration_ms"] if cover_scene else 0),
        "audio_duration_ms": audio_dur_ms,
        "scene_source": "section_markers",
    }


def plan_scenes(article_dir: Path, config: dict) -> dict:
    """主逻辑：规划分镜。"""
    video_dir = article_dir / "_video"
    timeline = read_json(video_dir / "temp" / "timeline_captions.json")
    captions = timeline.get("captions", [])
    if not captions:
        raise RuntimeError("timeline_captions.json 的 captions 为空")

    audio_dur_ms = int((timeline.get("audio_duration_seconds") or 0) * 1000)
    if audio_dur_ms <= 0:
        audio_dur_ms = captions[-1].get("endMs", 0)

    # 无封面时：compose 会用 atrim 裁掉音频开头静音（TTS 自带的 lead silence），
    # 场景时间轴也需同步偏移（所有时间戳 -lead_silence_ms），否则场景与裁后音频错位。
    if not config.get("cover", {}).get("enabled", False):
        lead_silence_ms = int(captions[0].get("startMs", 0)) if captions else 0
        if lead_silence_ms > 200:
            print(f"  [plan] 无封面模式：时间轴 -{lead_silence_ms}ms（对齐裁后音频）")
            audio_dur_ms -= lead_silence_ms
            # captions 时间戳偏移（给后续 find_caption_time / section 映射用）
            captions = [
                {**c,
                 "startMs": max(0, c.get("startMs", 0) - lead_silence_ms),
                 "endMs": max(0, c.get("endMs", 0) - lead_silence_ms)}
                for c in captions
            ]
            # sections_timeline.json 的时间戳也要偏移（如果存在）
            sections_timeline_path = video_dir / "temp" / "sections_timeline.json"
            if sections_timeline_path.exists():
                sec_tl = read_json(sections_timeline_path)
                for sec in sec_tl.get("sections", []):
                    if sec.get("start_ms") is not None:
                        sec["start_ms"] = max(0, sec["start_ms"] - lead_silence_ms)
                    if sec.get("end_ms") is not None:
                        sec["end_ms"] = max(0, sec["end_ms"] - lead_silence_ms)
                write_json(sec_tl, sections_timeline_path)

    # 1. 提取插图
    illustrations = extract_illustrations(article_dir / "公众号_文章.md")
    print(f"  [plan] 文章插图: {len(illustrations)} 张")

    # 1b. 优先用 [SECTION:N] 分节时间轴切场景（播客脚本带分节标记时）
    #     sections_timeline.json 由 align_captions 从 sections.json + Whisper 映射得来。
    #     每个 section = 一个场景，配对应插图（section N → 第 N 张）。
    #     无则回退下面的文本匹配路径（向后兼容）。
    sections_timeline_path = video_dir / "temp" / "sections_timeline.json"
    if sections_timeline_path.exists():
        sec_tl = read_json(sections_timeline_path)
        sec_sections = [s for s in sec_tl.get("sections", [])
                        if s.get("start_ms") is not None]
        if sec_sections:
            print(f"  [plan] 用 [SECTION:N] 分节时间轴切 {len(sec_sections)} 个场景"
                  f"（源: {sec_tl.get('source', '?')}）")
            result = _plan_scenes_from_sections(
                sec_sections, illustrations, audio_dur_ms, config, article_dir
            )
            if result is not None:
                return result
            print("  [plan] section 切场景失败，回退文本匹配")

    # 2. 口播段落
    script_path = resolve_podcast_path(article_dir, "播客_脚本.txt")
    paragraphs = load_podcast_paragraphs(script_path)
    print(f"  [plan] 口播段落: {len(paragraphs)} 段")

    # 3. 对齐：把口播稿按插图数量切成 N+1 段
    #    第 k 张插图之前的内容 = 场景 k（配第 k 张图）
    #    最后一段（所有插图之后的内容）= 场景 N（沿用最后一张图）
    num_imgs = len(illustrations)

    # 把口播段落分成 num_imgs + 1 组
    # 用简单的等分策略：每组 ceil(len(paragraphs) / (num_imgs + 1)) 段
    # 但如果插图数量和段落数量接近，就 1:1
    if num_imgs == 0:
        # 无插图：整个视频用一张占位图（封面或纯色）
        print(f"  [plan] WARNING: 文章无插图，整个视频用封面图")
        groups = [paragraphs]
        scene_images = [{"alt": "封面", "path": "公众号_封面.png"}]
    else:
        # 按比例分组：每组的段落数 ≈ 总段落 / (图数+1)
        # 但更自然的是：每组段落数 ≈ 总段落 / 图数（最后多出来的归最后一组）
        if num_imgs >= len(paragraphs):
            # 插图比段落多：每段配一张图，多余的图分配到最后
            groups = [[p] for p in paragraphs]
            # 补齐到 num_imgs 组
            while len(groups) < num_imgs:
                groups.append([paragraphs[-1]] if paragraphs else [""])
        else:
            # 正常情况：把段落均匀分到 num_imgs 组
            per_group = max(1, len(paragraphs) // num_imgs)
            groups = []
            for i in range(num_imgs):
                start = i * per_group
                # 最后一组吃剩余全部
                end = len(paragraphs) if i == num_imgs - 1 else start + per_group
                groups.append(paragraphs[start:end])
        scene_images = illustrations

    # 4. 为每组找到时间范围
    scenes = []
    search_idx = 0
    prev_end_ms = 0

    for i, group in enumerate(groups):
        group_text = "\n".join(group)
        start_ms, end_ms, search_idx = find_caption_time(captions, group_text, search_idx)

        if start_ms is None:
            # 匹配失败：用前一个场景的结束时间 + 均分剩余时间
            start_ms = prev_end_ms
            remaining = audio_dur_ms - prev_end_ms
            scenes_left = len(groups) - i
            end_ms = prev_end_ms + int(remaining / scenes_left)
            print(f"  [plan] 场景 {i}: 文本匹配失败，均分时间 {start_ms/1000:.1f}s-{end_ms/1000:.1f}s")
        else:
            print(f"  [plan] 场景 {i}: {start_ms/1000:.1f}s-{end_ms/1000:.1f}s "
                  f"({group_text[:20]}...)")

        # 钳制最短场景时长
        min_scene_ms = config["ken_burns"]["min_scene_sec"] * 1000
        max_scene_ms = config["ken_burns"]["max_scene_sec"] * 1000
        dur = end_ms - start_ms
        if dur < min_scene_ms and i < len(groups) - 1:
            # 太短，往后扩
            end_ms = start_ms + min_scene_ms
        if dur > max_scene_ms:
            # 太长，不裁（保持原样，长场景可接受）
            pass

        img = scene_images[i] if i < len(scene_images) else scene_images[-1]
        kb_type = KB_ROTATION[i % len(KB_ROTATION)]

        scenes.append({
            "id": i,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "image": img["path"],
            "alt_text": img["alt"],
            "ken_burns": kb_type,
        })
        prev_end_ms = end_ms

    # 确保最后一个场景的 end_ms = 音频结束
    if scenes:
        scenes[-1]["end_ms"] = audio_dur_ms

    # ── 场景时间轴连续化 ──
    # find_caption_time 的文本匹配可能留下间隙（画面短于音频，合成 -shortest 会截断
    # 末尾旁白）或重叠。这里在保留各场景时长的前提下，把场景首尾相接铺满整条音频：
    # 第一个场景从 0 开始，每个场景 start = 上一个 end，最后一个场景 end = 音频结束。
    if len(scenes) >= 2:
        total_scene_ms = sum(s["end_ms"] - s["start_ms"] for s in scenes)
        audio_avail = audio_dur_ms  # 可用时长（不含封面，封面在音频前单独拼接）
        if total_scene_ms > 0:
            cursor = 0
            for i, sc in enumerate(scenes):
                orig_dur = sc["end_ms"] - sc["start_ms"]
                # 按原时长占比分摊，最后一个吃掉舍入尾巴
                if i < len(scenes) - 1:
                    scaled = int(orig_dur * audio_avail / total_scene_ms)
                    sc["start_ms"] = cursor
                    sc["end_ms"] = cursor + scaled
                    cursor += scaled
                else:
                    sc["start_ms"] = cursor
                    sc["end_ms"] = audio_dur_ms
            print(f"  [plan] 时间轴连续化: {len(scenes)} 个场景无间隙铺满 "
                  f"{audio_dur_ms/1000:.1f}s 音频")

    # 封面场景
    cover_scene = None
    if config["cover"]["enabled"]:
        cover_scene = {
            "duration_ms": int(config["cover"]["duration_sec"] * 1000),
            "image": "公众号_封面.png",
            "ken_burns": config["cover"].get("ken_burns", "zoom_in_slow"),
        }

    # 播客音频路径：解析到实际位置（_podcast/ 或根目录），存相对 article_dir 的 POSIX 路径
    audio_abs = resolve_podcast_path(article_dir, "播客_TTS.mp3")
    try:
        audio_rel = str(audio_abs.relative_to(article_dir)).replace("\\", "/")
    except ValueError:
        audio_rel = str(audio_abs)

    result = {
        "cover_scene": cover_scene,
        "scenes": scenes,
        "audio_path": audio_rel,
        "total_duration_ms": audio_dur_ms + (cover_scene["duration_ms"] if cover_scene else 0),
        "audio_duration_ms": audio_dur_ms,
    }

    return result


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 2：分镜规划")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    config = read_json(SKILL_DIR / "config.json")

    # 校验输入
    timeline_path = article_dir / "_video" / "temp" / "timeline_captions.json"
    if not timeline_path.exists():
        print(f"ERROR: timeline_captions.json 不存在，请先运行阶段 1", file=sys.stderr)
        sys.exit(1)
    if not (article_dir / "公众号_文章.md").exists():
        print(f"ERROR: 公众号_文章.md 不存在", file=sys.stderr)
        sys.exit(1)
    if not resolve_podcast_path(article_dir, "播客_脚本.txt").exists():
        print(f"ERROR: 播客_脚本.txt 不存在（已查找 _podcast/ 与文章根目录）", file=sys.stderr)
        sys.exit(1)

    scenes = plan_scenes(article_dir, config)

    output_path = article_dir / "_video" / "scenes.json"
    write_json(scenes, output_path)

    print(f"  [plan] {len(scenes['scenes'])} 个场景"
          f"{' + 封面' if scenes['cover_scene'] else ''} → {output_path.name}")
    print(f"  [plan] 总时长: {scenes['total_duration_ms']/1000:.1f}s")


if __name__ == "__main__":
    main()

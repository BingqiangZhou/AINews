#!/usr/bin/env python3
"""
build_composition.py — 阶段 3：构建 hyperframes HTML composition（数据可视化式）

读 scenes_visual.json（每个 section 的视觉元素：关键数字/关键词/要点列表/数据网格，
由 design_scenes.py + 主 agent 生成）+ captions_corrected.json（逐句字幕 + 时间戳）+
播客音频，生成 hyperframes HTML 项目。

视觉由文案内容驱动（hyperframes 原生），不复用文章插图：
  - hero_number：大数字 count-up 动效 + 一句话说明
  - stat_grid：数据卡片网格（对比数据）
  - keypoints：要点列表逐条入场
  - keywords：关键词 chips 网格

composition 结构（单一 GSAP paused timeline，window.__timelines["ainews-daily"]）：
  - 背景层（track 0）：每个 section 一个全屏渐变背景 clip（section 主题色），section 间硬切。
  - 视觉层（track 2）：每个 section 的数据可视化内容（大数字/卡片/列表）。
  - 字幕层（track 1）：逐句字幕（正确文本）按时间戳显示。
  - 水印层（track 3）：AINews 角标 + 日期，全程。
  - 音频：播客 TTS <audio>。

Usage:
  python build_composition.py --article-dir <文章目录>
"""

import argparse
import datetime
import json
import shutil
import sys
from html import escape
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import setup_windows_encoding, read_json, write_json, resolve_podcast_path  # noqa: E402


# ── 项目模板 ──────────────────────────────────────────────────────────────

HYPERFRAMES_JSON = {
    "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
    "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    "media": {"autoProxy": True},
}


def make_meta(name: str) -> dict:
    return {"id": name, "name": name, "createdAt": datetime.datetime.utcnow().isoformat() + "Z"}


def make_package(name: str) -> dict:
    return {
        "name": name, "private": True, "type": "module",
        "scripts": {
            "dev": "npx --yes hyperframes preview",
            "check": "npx --yes hyperframes check",
            "render": "npx --yes hyperframes render",
        },
    }


# ── section 主题色板（每个 section 一个主色，用于背景渐变 + 强调色）────────
# 深色系背景 + 高饱和强调色，保证白字可读
SECTION_PALETTES = [
    {"bg_from": "#0f1830", "bg_to": "#1a1040", "accent": "#7c5cff", "accent_rgb": "124,92,255"},  # 紫蓝
    {"bg_from": "#0d2030", "bg_to": "#102a1a", "accent": "#4dd0e1", "accent_rgb": "77,208,225"},   # 青绿
    {"bg_from": "#2a1020", "bg_to": "#3a0f2a", "accent": "#ff5c8a", "accent_rgb": "255,92,138"},   # 品红
    {"bg_from": "#1f1505", "bg_to": "#2a1a08", "accent": "#ffb04d", "accent_rgb": "255,176,77"},   # 琥珀
    {"bg_from": "#0a1a2a", "bg_to": "#0f2840", "accent": "#5cb8ff", "accent_rgb": "92,184,255"},   # 天蓝
    {"bg_from": "#1a0a2a", "bg_to": "#2a1040", "accent": "#b05cff", "accent_rgb": "176,92,255"},   # 紫
    {"bg_from": "#0a1a15", "bg_to": "#0f2a20", "accent": "#5cffaa", "accent_rgb": "92,255,170"},   # 翠绿
]


def palette_for(idx: int) -> dict:
    return SECTION_PALETTES[idx % len(SECTION_PALETTES)]


# ── CSS（全部视觉用纯 CSS，无外部图片）────────────────────────────────────

def build_css() -> str:
    return """
/* 系统中文字体声明（lint 要求 font-family 有 @font-face） */
@font-face { font-family: "PingFang SC"; src: local("PingFang SC"), local("苹方-简"); }
@font-face { font-family: "Microsoft YaHei"; src: local("Microsoft YaHei"), local("微软雅黑"); }
@font-face { font-family: "Noto Sans SC"; src: local("Noto Sans SC"); }

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  width: 1920px; height: 1080px; overflow: hidden; background: #06080c;
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}
#root { position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #06080c; }

/* ── 背景层：每个 section 一个全屏渐变（section 主题色）── */
.bg-scene {
  position: absolute; inset: 0; width: 100%; height: 100%;
}
.bg-gradient {
  position: absolute; inset: 0;
}
/* 装饰性发光：radial-gradient 模拟（不用 filter:blur 避免 heavy overlay 黑屏）。
   两个发光球分居右上 + 左下，错开主文字区，营造氛围。*/
.bg-glow {
  position: absolute; border-radius: 50%;
}
.bg-glow-1 { width: 1300px; height: 1300px; top: -400px; right: -300px; opacity: 0.7; }
.bg-glow-2 { width: 1100px; height: 1100px; bottom: -380px; left: -280px; opacity: 0.45; }
/* 细网格底纹（科技感）*/
.bg-grid {
  position: absolute; inset: 0; opacity: 0.05;
  background-image:
    linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px);
  background-size: 60px 60px;
}

/* ── 视觉内容层 ── */
.visual {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 140px 160px 220px;
}
/* section 标题（kicker + title，顶部）*/
.v-kicker {
  font-size: 30px; font-weight: 700; letter-spacing: 10px;
  padding: 10px 28px; border-radius: 999px;
  border: 2px solid; text-transform: uppercase;
  margin-bottom: 60px;
}
.v-title {
  font-size: 64px; font-weight: 800; color: #ffffff;
  text-align: center; line-height: 1.2; max-width: 1400px;
  margin-bottom: 70px;
  text-shadow: 0 4px 24px rgba(0,0,0,0.4);
}

/* hero_number：超大数字（垂直堆叠：数字行 → 单位 → 说明，更聚焦）*/
.hero-number {
  font-size: 300px; font-weight: 900; line-height: 0.95;
  color: #ffffff; letter-spacing: -6px;
  text-shadow: 0 8px 56px rgba(0,0,0,0.55);
  display: flex; align-items: baseline; justify-content: center; gap: 18px;
}
.hero-unit {
  font-size: 72px; font-weight: 800; color: #ffffff;
  opacity: 0.95; letter-spacing: 1px;
}
.hero-label {
  font-size: 42px; font-weight: 500; color: rgba(255,255,255,0.88);
  margin-top: 40px; text-align: center; max-width: 1200px; line-height: 1.4;
}

/* keypoints：要点列表 */
.keypoints {
  display: flex; flex-direction: column; gap: 24px; max-width: 1300px; width: 100%;
}
.keypoint {
  display: flex; align-items: center; gap: 28px;
  padding: 26px 40px; border-radius: 20px;
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.14);
}
.keypoint-dot {
  width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 16px currentColor;
}
.keypoint-text {
  font-size: 40px; font-weight: 600; color: #ffffff; line-height: 1.35;
}

/* stat_grid：数据卡片网格 */
.stat-grid {
  display: flex; gap: 48px; justify-content: center; flex-wrap: wrap;
}
.stat-card {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  padding: 48px 56px; border-radius: 24px; min-width: 320px;
  background: rgba(255,255,255,0.14);
  border: 2px solid rgba(255,255,255,0.16);
}
.stat-value {
  font-size: 96px; font-weight: 900; line-height: 1; color: #ffffff;
  letter-spacing: -2px;
}
.stat-label {
  font-size: 32px; font-weight: 500; color: rgba(255,255,255,0.8);
  text-align: center;
}

/* keywords：关键词 chips 网格 */
.kw-grid {
  display: flex; flex-wrap: wrap; gap: 28px; justify-content: center; max-width: 1300px;
}
.kw-chip {
  font-size: 52px; font-weight: 700; color: #ffffff;
  padding: 24px 48px; border-radius: 999px;
  background: rgba(255,255,255,0.1);
  border: 2px solid rgba(255,255,255,0.2);
}

/* ── 逐句字幕 ── */
.caption {
  position: absolute; left: 50%; bottom: 80px; transform: translateX(-50%);
  max-width: 1600px; padding: 24px 48px;
  font-size: 46px; font-weight: 700; line-height: 1.45; color: #ffffff;
  text-align: center;
  background: rgba(6, 8, 12, 0.82);
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.14);
  text-shadow: 0 2px 10px rgba(0,0,0,0.6);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

/* ── 品牌水印 ── */
.brand-wrap { position: absolute; inset: 0; pointer-events: none; }
.brand {
  position: absolute; left: 56px; top: 48px;
  display: flex; align-items: center; gap: 14px;
  font-size: 32px; font-weight: 800; color: #ffffff; letter-spacing: 2px;
}
.brand-dot {
  width: 18px; height: 18px; border-radius: 50%;
  background: #4dd0e1;
  box-shadow: 0 0 20px rgba(77, 208, 225, 0.9);
}
.brand-date {
  position: absolute; right: 56px; top: 54px;
  font-size: 28px; font-weight: 500; color: rgba(255,255,255,0.75); letter-spacing: 1px;
}
"""


# ── HTML 片段生成 ─────────────────────────────────────────────────────────

def _bg_scene_html(idx: int, start_s: float, dur_s: float, palette: dict) -> str:
    """全屏渐变背景 clip（section 主题色 + radial-gradient 发光 + 网格）。

    发光用 radial-gradient（rgba 中心→透明边缘）模拟，不用 filter:blur
    （大量 blur overlay 会导致渲染前半段黑屏，见 lint warning）。
    """
    accent_rgb = palette["accent_rgb"]
    return f'''      <div id="bg-{idx}" class="clip bg-scene" data-start="{start_s:.3f}" data-duration="{dur_s:.3f}" data-track-index="0" style="z-index:{10 + idx}">
        <div class="bg-gradient" style="background: linear-gradient(135deg, {palette["bg_from"]} 0%, {palette["bg_to"]} 100%);"></div>
        <div id="bg-glow1-{idx}" class="bg-glow bg-glow-1" data-layout-allow-overflow style="background: radial-gradient(circle, rgba({accent_rgb},0.65) 0%, rgba({accent_rgb},0.2) 42%, transparent 70%);"></div>
        <div id="bg-glow2-{idx}" class="bg-glow bg-glow-2" data-layout-allow-overflow style="background: radial-gradient(circle, rgba({accent_rgb},0.45) 0%, rgba({accent_rgb},0.12) 42%, transparent 70%);"></div>
        <div class="bg-grid"></div>
      </div>'''


def _visual_html(idx: int, start_s: float, dur_s: float, scene: dict, palette: dict) -> str:
    """section 的视觉内容 clip（根据 visual_type 渲染不同布局）。"""
    accent = palette["accent"]
    accent_rgb = palette["accent_rgb"]
    kicker = escape(scene.get("kicker", ""))
    title = escape(scene.get("title", ""))
    vtype = scene.get("visual_type", "keywords")

    # 视觉主体（根据 vtype）
    body = ""
    if vtype == "hero_number" and scene.get("hero_number"):
        hn = scene["hero_number"]
        body += f'''      <div id="hero-{idx}" class="hero-number" style="color:{accent};">
        <span id="hero-val-{idx}">{escape(str(hn.get("value", "")))}</span>
        <span class="hero-unit">{escape(hn.get("unit", ""))}</span>
      </div>
      <div id="hero-label-{idx}" class="hero-label">{escape(hn.get("label", ""))}</div>
'''
    elif vtype == "stat_grid" and scene.get("stat_grid"):
        cards = ""
        for j, st in enumerate(scene["stat_grid"]):
            cards += f'''        <div id="stat-{idx}-{j}" class="stat-card" style="border-color: rgba({accent_rgb},0.5);">
          <div class="stat-value" style="color:{accent};">{escape(str(st.get("value", "")))}</div>
          <div class="stat-label">{escape(st.get("label", ""))}</div>
        </div>
'''
        body += f'      <div id="statgrid-{idx}" class="stat-grid">\n{cards}      </div>\n'
    elif vtype == "keypoints" and scene.get("keypoints"):
        kps = ""
        for j, kp in enumerate(scene["keypoints"]):
            kps += f'''        <div id="kp-{idx}-{j}" class="keypoint">
          <div class="keypoint-dot" style="background:{accent};color:{accent};"></div>
          <div class="keypoint-text">{escape(kp)}</div>
        </div>
'''
        body += f'      <div id="kps-{idx}" class="keypoints">\n{kps}      </div>\n'
    else:  # keywords（兜底）
        kws = ""
        for j, kw in enumerate(scene.get("keywords", [])):
            kws += f'        <div id="kw-{idx}-{j}" class="kw-chip" style="border-color: rgba({accent_rgb},0.5);">{escape(kw)}</div>\n'
        body += f'      <div id="kwgrid-{idx}" class="kw-grid">\n{kws}      </div>\n'

    return f'''      <div id="vis-{idx}" class="clip visual" data-start="{start_s:.3f}" data-duration="{dur_s:.3f}" data-track-index="2" style="z-index:30">
        <div id="vk-{idx}" class="v-kicker" style="color:{accent}; border-color: rgba({accent_rgb},0.6); background: rgba({accent_rgb},0.12);">{kicker}</div>
        <div id="vt-{idx}" class="v-title">{title}</div>
{body}      </div>'''


def _caption_html(i: int, start_s: float, dur_s: float, text: str) -> str:
    return (f'      <div id="cap-{i}" class="clip caption" data-start="{start_s:.3f}" '
            f'data-duration="{dur_s:.3f}" data-track-index="1" style="z-index:20">'
            f'{escape(text)}</div>')


# ── 时间轴规划 ────────────────────────────────────────────────────────────

def plan_scenes(sections_visual: list[dict], sections_time: list[dict],
                total_duration_ms: int, title_card_lead: float = 0.4) -> list[dict]:
    """合并视觉设计 + 时间戳，输出 scene 列表。

    sections_visual: scenes_visual.json 的 sections（视觉元素）
    sections_time: captions_corrected.json 的 sections（时间戳）
    """
    # 时间戳连续化（避免同轨重叠）
    time_by_idx = {}
    prev_end = 0
    for i, st in enumerate(sections_time):
        idx = str(st.get("index"))
        s = st.get("start_ms")
        if s is None:
            s = prev_end
        s = max(s, prev_end)
        if i == len(sections_time) - 1:
            e = total_duration_ms
        else:
            next_s = sections_time[i + 1].get("start_ms")
            e = next_s if (next_s is not None and next_s > s) else s + 30000
        e = max(e, s + 2000)
        time_by_idx[idx] = (s, e)
        prev_end = e

    scenes = []
    for i, sv in enumerate(sections_visual):
        idx = str(sv.get("section_index"))
        # 时间戳：优先匹配，否则按顺序
        if idx in time_by_idx:
            start_ms, end_ms = time_by_idx[idx]
        elif i < len(sections_time):
            # 顺序兜底
            keys = list(time_by_idx.keys())
            start_ms, end_ms = time_by_idx[keys[i]]
        else:
            start_ms, end_ms = prev_end, total_duration_ms

        start_s = start_ms / 1000.0
        dur_s = max(1.0, (end_ms - start_ms) / 1000.0)
        # 视觉内容比背景短一点（留出入场余量），背景铺满
        vis_start = start_s + title_card_lead
        vis_dur = max(1.0, dur_s - title_card_lead - 0.2)

        scenes.append({
            "scene_idx": i,
            "section_index": idx,
            "start_s": start_s,
            "dur_s": dur_s,
            "vis_start_s": vis_start,
            "vis_dur_s": vis_dur,
            "palette_idx": i,
            "visual": sv,
        })
    return scenes


def plan_captions(captions_raw: list[dict], total_duration_s: float) -> list[dict]:
    """字幕 clip（同轨不重叠）。"""
    out = []
    for c in captions_raw:
        s = c.get("startMs", 0) / 1000.0
        e = c.get("endMs", s + 2) / 1000.0
        if e - s < 0.8:
            e = s + 0.8
        e = min(e, total_duration_s)
        if s >= total_duration_s:
            continue
        out.append({"start_s": round(s, 3), "dur_s": round(max(0.3, e - s), 3),
                    "text": c.get("text", "").strip()})
    # 连续化：确保相邻不重叠
    for i in range(len(out) - 1):
        gap = out[i + 1]["start_s"] - out[i]["start_s"]
        if out[i]["dur_s"] > gap:
            out[i]["dur_s"] = round(max(0.2, gap - 0.02), 3)
    return out


# ── GSAP timeline 生成 ────────────────────────────────────────────────────

def build_tweens(scenes: list[dict]) -> list[str]:
    """生成所有 GSAP tween（入场动效，无出场——clip 到点自动隐藏）。"""
    tweens = []
    for sc in scenes:
        idx = sc["scene_idx"]
        bg_s = sc["start_s"]
        vis_s = sc["vis_start_s"]
        vis_d = sc["vis_dur_s"]
        sv = sc["visual"]
        vtype = sv.get("visual_type", "keywords")

        # 背景入场：发光球缓慢漂移（贯穿整个 clip）+ 淡入
        tweens.append(
            f'  tl.fromTo("#bg-{idx}", {{opacity: 0}}, {{opacity: 1, duration: 0.6, ease: "power2.out"}}, {bg_s:.3f});'
        )
        # 发光球缓慢漂移（呼吸感，2 个对称漂移）
        tweens.append(
            f'  tl.fromTo("#bg-glow1-{idx}", {{x: 0, y: 0, scale: 1}}, '
            f'{{x: -60, y: 50, scale: 1.15, duration: {sc["dur_s"]:.3f}, ease: "sine.inOut"}}, {bg_s:.3f});'
        )
        tweens.append(
            f'  tl.fromTo("#bg-glow2-{idx}", {{x: 0, y: 0, scale: 1}}, '
            f'{{x: 55, y: -40, scale: 1.12, duration: {sc["dur_s"]:.3f}, ease: "sine.inOut"}}, {bg_s:.3f});'
        )

        # 视觉内容入场：kicker → title → 主体
        tweens.append(
            f'  tl.fromTo("#vis-{idx}", {{opacity: 0}}, {{opacity: 1, duration: 0.4, ease: "power2.out"}}, {vis_s:.3f});'
        )
        tweens.append(
            f'  tl.fromTo("#vk-{idx}", {{opacity: 0, y: -20, scale: 0.9}}, '
            f'{{opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.4)"}}, {vis_s:.3f});'
        )
        tweens.append(
            f'  tl.fromTo("#vt-{idx}", {{opacity: 0, y: 30}}, '
            f'{{opacity: 1, y: 0, duration: 0.5, ease: "power3.out"}}, {vis_s + 0.2:.3f});'
        )

        # 主体内容入场（按 vtype）
        main_delay = vis_s + 0.5
        if vtype == "hero_number":
            # 大数字冲击入场：从 0.2 弹性放大（back.out），模拟 count-up 的冲击感
            tweens.append(
                f'  tl.fromTo("#hero-{idx}", {{opacity: 0, scale: 0.2}}, '
                f'{{opacity: 1, scale: 1, duration: 0.8, ease: "back.out(1.8)"}}, {main_delay:.3f});'
            )
            tweens.append(
                f'  tl.fromTo("#hero-label-{idx}", {{opacity: 0, y: 24}}, '
                f'{{opacity: 1, y: 0, duration: 0.5, ease: "power2.out"}}, {main_delay + 0.45:.3f});'
            )
        elif vtype == "stat_grid":
            # 数据卡片错峰入场
            for j in range(len(sv.get("stat_grid", []))):
                tweens.append(
                    f'  tl.fromTo("#stat-{idx}-{j}", {{opacity: 0, y: 40, scale: 0.8}}, '
                    f'{{opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.4)"}}, '
                    f'{main_delay + j * 0.18:.3f});'
                )
        elif vtype == "keypoints":
            # 要点逐条滑入
            for j in range(len(sv.get("keypoints", []))):
                tweens.append(
                    f'  tl.fromTo("#kp-{idx}-{j}", {{opacity: 0, x: -50}}, '
                    f'{{opacity: 1, x: 0, duration: 0.4, ease: "power2.out"}}, '
                    f'{main_delay + j * 0.22:.3f});'
                )
        else:  # keywords
            for j in range(len(sv.get("keywords", []))):
                tweens.append(
                    f'  tl.fromTo("#kw-{idx}-{j}", {{opacity: 0, y: 30, scale: 0.7}}, '
                    f'{{opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(1.5)"}}, '
                    f'{main_delay + j * 0.12:.3f});'
                )
    return tweens


# ── 主流程 ────────────────────────────────────────────────────────────────

def build_index_html(total_duration_s, audio_filename, scenes, captions,
                     brand_name, date_str, title_main) -> str:
    bg_clips = []
    vis_clips = []
    for sc in scenes:
        pal = palette_for(sc["palette_idx"])
        bg_clips.append(_bg_scene_html(sc["scene_idx"], sc["start_s"], sc["dur_s"], pal))
        vis_clips.append(_visual_html(sc["scene_idx"], sc["vis_start_s"], sc["vis_dur_s"],
                                       sc["visual"], pal))

    cap_clips = [_caption_html(i, c["start_s"], c["dur_s"], c["text"])
                 for i, c in enumerate(captions)]

    bg_tweens = build_tweens(scenes)
    cap_tweens = [
        f'  tl.fromTo("#cap-{i}", {{opacity: 0, y: 16}}, '
        f'{{opacity: 1, y: 0, duration: 0.12, ease: "power2.out"}}, {c["start_s"]:.3f});'
        for i, c in enumerate(captions)
    ]

    return f'''<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>{escape(title_main)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
{build_css()}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="ainews-daily" data-start="0" data-duration="{total_duration_s:.3f}" data-width="1920" data-height="1080">

      <!-- 背景层（track 0）：每个 section 一个渐变背景 -->
{chr(10).join(bg_clips)}

      <!-- 字幕层（track 1） -->
{chr(10).join(cap_clips)}

      <!-- 视觉内容层（track 2）：大数字/卡片/列表/关键词 -->
{chr(10).join(vis_clips)}

      <!-- 水印层（track 3，全程） -->
      <div id="brand" class="clip" data-start="0" data-duration="{total_duration_s:.3f}" data-track-index="3" style="z-index:40">
        <div class="brand-wrap">
          <div class="brand">
            <span class="brand-dot"></span>
            <span>{escape(brand_name)}</span>
          </div>
          <div class="brand-date">{escape(date_str)}</div>
        </div>
      </div>

      <!-- 旁白音频 -->
      <audio id="narration" data-start="0" data-track-index="10" src="assets/{audio_filename}"></audio>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(bg_tweens)}
{chr(10).join(cap_tweens)}
      window.__timelines["ainews-daily"] = tl;
    </script>
  </body>
</html>
'''


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 3：构建 hyperframes HTML composition（数据可视化式）")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    video_dir = article_dir / "_video"
    temp_dir = video_dir / "temp"

    # 输入校验
    sv_path = temp_dir / "scenes_visual.json"
    cc_path = temp_dir / "captions_corrected.json"
    if not sv_path.exists():
        print("ERROR: scenes_visual.json 不存在。请先运行 design_scenes.py 并由主 agent 填充。",
              file=sys.stderr)
        sys.exit(1)
    if not cc_path.exists():
        print("ERROR: captions_corrected.json 不存在，请先运行 align_script.py", file=sys.stderr)
        sys.exit(1)
    audio_path = resolve_podcast_path(article_dir, "播客_TTS.mp3")
    if not audio_path.exists():
        print("ERROR: 播客_TTS.mp3 不存在", file=sys.stderr)
        sys.exit(1)

    sv = read_json(sv_path)
    cc = read_json(cc_path)
    total_duration_s = float(cc.get("audio_duration_seconds") or 0)
    if total_duration_s <= 0 and cc.get("captions"):
        total_duration_s = cc["captions"][-1].get("endMs", 0) / 1000.0
    print(f"  [build] 总时长: {total_duration_s:.1f}s")

    # 规划
    scenes = plan_scenes(sv.get("sections", []), cc.get("sections", []),
                         int(total_duration_s * 1000))
    captions = plan_captions(cc.get("captions", []), total_duration_s)
    print(f"  [build] 场景: {len(scenes)} 个, 字幕: {len(captions)} 条")

    # 组装项目
    project_dir = video_dir / "hyperframes_project"
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = project_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # copy 音频（本项目无需插图——视觉纯 CSS 生成）
    audio_filename = "narration.mp3"
    shutil.copy2(audio_path, assets_dir / audio_filename)

    # 元数据
    article_md = article_dir / "公众号_文章.md"
    title_main = "AI 日报"
    if article_md.exists():
        title_main = article_md.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip() or "AI 日报"
    date_str = ""
    state_path = article_dir / "state.json"
    if state_path.exists():
        date_str = read_json(state_path).get("date", "")
    if not date_str:
        date_str = datetime.date.today().isoformat()

    html = build_index_html(total_duration_s, audio_filename, scenes, captions,
                            "AINews", date_str, title_main)
    (project_dir / "index.html").write_text(html, encoding="utf-8")
    write_json(HYPERFRAMES_JSON, project_dir / "hyperframes.json")
    write_json(make_meta("ainews-daily"), project_dir / "meta.json")
    write_json(make_package("ainews-daily"), project_dir / "package.json")

    write_json({"total_duration_s": total_duration_s, "scene_count": len(scenes),
                "caption_count": len(captions), "scenes": scenes},
               temp_dir / "hf_scenes.json")

    print(f"  [build] → {project_dir}")
    print(f"  [build] index.html ({len(html)} bytes) — 视觉由文案驱动（纯 CSS/GSAP，无插图）")


if __name__ == "__main__":
    main()

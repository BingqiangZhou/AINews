#!/usr/bin/env python3
"""
design_scenes.py — 阶段 2.5：为每个 section 设计数据可视化视觉

读 captions_corrected.json（section + 字幕原文 + 时间戳），生成一个 prompt 文件
temp/design_scenes_prompt.md，主对话 agent 读它后，按 schema 为每个 section
提取视觉元素（关键数字、关键词、要点列表），输出 temp/scenes_visual.json。
build_composition.py 读 scenes_visual.json 生成 hyperframes HTML。

为什么需要这一步：
  旧流程复用文章插图（imgs/*.png）做背景，与旧 Ken Burns 无本质区别。
  hyperframes 的价值在于根据文案内容生成原生动态视觉——大数字 count-up、
  关键词卡片错峰入场、要点列表、对比图。本步用 LLM 从文案提取这些视觉元素。

工作模式（与 Phase 3 打分一致）：
  1. 本脚本生成 prompt（含每个 section 的字幕原文 + 输出 schema）
  2. 主 agent 读 prompt，按 schema 输出 JSON 到 scenes_visual.json
  3. build_composition.py 读 scenes_visual.json → HTML

Usage:
  python design_scenes.py --article-dir <文章目录>
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import setup_windows_encoding, read_json, write_json  # noqa: E402


SCHEMA_DOC = """\
# scenes_visual.json schema

输出一个 JSON 对象，`sections` 数组，每个 section 一个对象。字段：

```json
{
  "sections": [
    {
      "section_index": "<原 section index，如 OPENING / 1 / DEEPDIVE / ENDING>",
      "kicker": "<短标签，2-6 字，如「第 1 组」「今日深读」>",
      "title": "<section 标题，<=20 字，去掉「一、」前缀>",
      "visual_type": "<hero_number | keywords | keypoints | stat_grid 之一>",
      "hero_number": {           // 仅 visual_type=hero_number 时填
        "value": "<关键数字字符串，如「10万」「2」「80%」>",
        "unit": "<单位/后缀，如「小时」「个开源模型」「token 空转」，可空>",
        "label": "<一句话说明这个数字的意义，<=24 字>"
      },
      "keypoints": [              // visual_type=keypoints 或 stat_grid 时填，3-5 条
        "<要点，<=20 字，结论先行>"
      ],
      "keywords": [               // 所有点都填，3-6 个关键词，用于 chips 展示
        "<关键词，<=8 字>"
      ],
      "stat_grid": [              // 仅 visual_type=stat_grid 时填，2-4 个对比数据
        {"value": "<数字>", "label": "<说明，<=10 字>"}
      ]
    }
  ]
}
```

## visual_type 选择规则

- **hero_number**：section 有一个压倒性的关键数字（如「小米 10 万小时」「A16Z 80% token 空转」）。
  画面：大数字 count-up 动效 + 一句话说明。
- **keypoints**：section 是多条并列要闻（如「大模型发布」组有 Kimi K3 / Inkling / GPT-5.6 三条）。
  画面：要点列表逐条入场。
- **stat_grid**：section 有多个可对比的数据（如「15分钟 vs 6小时」）。
  画面：数据卡片网格。
- **keywords**：兜底，无明确数字/要点，只有主题词。
  画面：关键词 chips 网格。

## 提取原则

- **只从该 section 的字幕原文提取**，不编造文案外的信息（反虚构）。
- 数字用原文的表述（「十万小时」→ value="10万" unit="小时"；「百分之八十」→ value="80%"）。
- keypoints 每条是一个独立要闻/观点，结论先行，<=20 字。
- keywords 是可独立展示的名词/短语，<=8 字。
- DEEPDIVE section 用 hero_number（深读通常聚焦一个关键数据）。
- OPENING 用 keywords（总览四个方向）。
- ENDING 用 keypoints（总结两三件事）。
"""


def build_prompt(cc: dict, article_dir: Path) -> str:
    """生成给主 agent 的 prompt。"""
    sections = cc.get("sections", [])
    total_dur = cc.get("audio_duration_seconds", 0)

    # 每个 section 的字幕原文预览
    section_blocks = []
    for sec in sections:
        idx = sec["index"]
        ss = (sec.get("start_ms") or 0) / 1000
        ee = (sec.get("end_ms") or total_dur) / 1000
        caps = [c["text"] for c in cc.get("captions", [])
                if ss <= c.get("startMs", 0) / 1000 < ee]
        # 也纳入 section 的 raw（完整原文段落，更可靠）
        raw = sec.get("raw", "")
        block = f"""### Section [{idx}] — {sec.get('title','')[:40]}
时间: {ss:.0f}s - {ee:.0f}s (时长 {ee-ss:.0f}s)
原文段落:
{raw}
"""
        if caps:
            block += "\n字幕时间轴预览:\n" + "\n".join(f"  {c[:70]}" for c in caps[:8])
        section_blocks.append(block)

    # 文章标题
    article_md = article_dir / "公众号_文章.md"
    article_title = ""
    if article_md.exists():
        article_title = article_md.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()

    prompt = f"""# 任务：为 AI 日报视频的每个 section 设计数据可视化视觉

你是 AINews 视频的视觉设计师。请根据下面每个 section 的**播客文案原文**，为它设计一个
hyperframes 原生动态视觉（大数字 / 关键词卡片 / 要点列表 / 数据网格），提取该段最具表现力
的视觉元素。

## 视频信息
- 标题: {article_title}
- 总时长: {total_dur:.0f}s
- section 数: {len(sections)}

## 各 section 文案

{chr(10).join(section_blocks)}

---

{SCHEMA_DOC}

## 输出要求

直接输出**纯 JSON**（不要 markdown 代码块包裹，不要解释），写入文件：
`{article_dir}/_video/temp/scenes_visual.json`

为每个 section 都生成一个对象（共 {len(sections)} 个），section_index 与上面一致。
选择最能体现该段内容的 visual_type。DEEPDIVE 优先 hero_number。
"""
    return prompt


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(
        description="阶段 2.5：生成 section 视觉设计 prompt（主 agent 填充 scenes_visual.json）"
    )
    ap.add_argument("--article-dir", required=True, help="文章目录")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    temp_dir = article_dir / "_video" / "temp"

    cc_path = temp_dir / "captions_corrected.json"
    if not cc_path.exists():
        print("ERROR: captions_corrected.json 不存在，请先运行 align_script.py",
              file=sys.stderr)
        sys.exit(1)

    cc = read_json(cc_path)
    prompt = build_prompt(cc, article_dir)

    prompt_path = temp_dir / "design_scenes_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    print(f"  [design_scenes] → {prompt_path.name} ({len(prompt)} bytes)")
    print(f"  [design_scenes] {len(cc.get('sections', []))} 个 section 待设计")
    print(f"  [design_scenes] 下一步：主 agent 读 prompt，按 schema 输出 scenes_visual.json")


if __name__ == "__main__":
    main()

"""ai-news-digest Phase 5: 把打分排序后的资讯整理成 article-studio transcript 模式期望的
事实素材文件 `_research/事实素材与来源.md`。

这是衔接采集层与 article-studio 的关键胶水。article-studio transcript 模式把传入文件
当作唯一权威事实源（零外部事实），因此本文件的内容质量直接决定日报文章的质量。

输出格式（对齐 article-studio references/phase0-research.md 的模板）:
- 顶部声明：RSS 采集于 {日期} + 文章类型说明（news 资讯/盘点）+ AI 小周人设
- 按 source_category 自动分 `##` 主题节（无分类的归入"其它"）
- 每条事实独立 bullet：AI 摘要 + 来源名 + 原文链接 + 事件日期 + 采集日期
- 文末 `## 写作立场/素材` 区：AI 小周人设声明 + news 盘点视角锚点 + 反虚构硬约束提醒

反虚构硬约束（本脚本只搬运，不改写事实）：
- 要点用 ranked.json 的 ai_summary（AI 打分时生成的一句话摘要），不改写
- 信源 URL 原样保留（不截断、不替换）
- 事件日期用 candidate.published（缺失则留空，由 article-studio writer 标注）

用法:
  <py> <scripts>/build_research_md.py --ranked <digest_ranked.json> --output <_research/事实素材与来源.md>
       [--persona AI小周]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


def log(msg: str) -> None:
    print(f"[research] {msg}", flush=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def today_cn() -> str:
    """北京时间今天的日期（UTC+8）。"""
    cn = timezone(timedelta(hours=8))
    return datetime.now(cn).strftime("%Y-%m-%d")


def normalize_category(cat: str) -> str:
    """把 source_category 映射成中文主题名；未知分类归入"其它动态"。"""
    mapping = {
        "人工智能": "AI 前沿",
        "Artificial_Intelligence": "AI 前沿",
        "软件编程": "开发者动态",
        "Software_Development": "开发者动态",
        "媒体资讯": "行业资讯",
        "Media": "行业资讯",
        "商业科技": "商业与科技",
        "Business": "商业与科技",
        "投资财经": "资本与市场",
        "Finance": "资本与市场",
        "产品设计": "产品与设计",
        "Product_Design": "产品与设计",
    }
    if not cat:
        return "其它动态"
    return mapping.get(cat, cat)


def build_research_md(data: dict, persona: str, date: str) -> str:
    items = data.get("items", [])
    # 按 source_category 分组（保持每组内的打分降序，因为 items 已排好序）
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        cat = normalize_category(it.get("source_category", ""))
        groups[cat].append(it)

    lines: list[str] = []
    # 顶部声明
    lines.append(f"# 事实素材与来源（RSS 采集于 {date}）")
    lines.append("")
    lines.append(
        f"> 本文是 **news（资讯/盘点）** 类公众号文章（AI 日报）。以下是从 AI 资讯信源 RSS "
        f"采集、AI 打分排序后的真实资讯条目，每条带信源链接与事件日期。写作时只引用下列事实，"
        f"不杜撰素材外信息。"
    )
    lines.append("")
    lines.append(f"> 人设：{persona}（AI 日报主播口吻，区别于个人随笔的第一人称）。")
    lines.append("")

    # 主题分节
    for cat, group_items in groups.items():
        lines.append(f"## 一、{cat}（{len(group_items)} 条）")
        lines.append("")
        for it in group_items:
            summary = (it.get("ai_summary") or it.get("summary") or "（无摘要）").strip()
            title = (it.get("title") or "").strip()
            src_name = (it.get("source_name") or "").strip()
            link = (it.get("link") or "").strip()
            published = (it.get("published") or "").strip()
            # 取 published 的日期部分（ISO 或字符串前 10 位）
            event_date = published[:10] if published else ""
            # 要点：用 AI 摘要作为事实描述，标题作为补充
            point = summary if summary and summary != "（无摘要）" else title
            lines.append(f"- **{point}**")
            if title and title != point:
                lines.append(f"  - 原标题：{title}")
            lines.append(f"  - {src_name}：{link}")
            if event_date:
                lines.append(f"  - 事件/发布日期：{event_date}")
            lines.append(f"  - 采集日期：{date}")
            lines.append("")
        lines.append("")

    # 写作立场/素材区
    lines.append("## 写作立场/素材（来自日报编排，非检索事实）")
    lines.append("")
    lines.append("### 作者意图/写作锚点")
    lines.append(f"- 人设：{persona}。AI 日报主播口吻——极简播报传递事实，克制点评或省略，不堆形容词、不写散文。")
    lines.append("- 文章类型：news（资讯/盘点）。核心是信息密度与时效标注。")
    lines.append('- 排版要求：**轻包装清单格式**（article-studio transcript 模式 news 清单分支）。把下列资讯条目排成可扫读清单：`##` 主题组 + `###` 条目标题 + 一句话事实 + 信源链接 + 日期 + 可选点评。不写散文钩子/趋势归纳。详见 article-studio/references/transcript-mode.md「news 清单分支」。')
    lines.append("- 时间范围：近 24 小时 RSS 采集窗口内的新条目。")
    lines.append("")
    lines.append("### 时间线要点（防自相矛盾）")
    lines.append("- 同一事件可能被多个信源报道，写作时合并为一条，取最早的事件日期为准。")
    lines.append('- 若两条资讯描述同一事件的不同阶段（如「发布」与「价格公布」），按事件日期先后排列。')
    lines.append("")
    lines.append("### news 类型红线提醒（article-studio 双主编会按此审查）")
    lines.append("- 红线 1（区分事实/观点）：点评部分必须明示是观点，不能写成事实。")
    lines.append('- 红线 2（限定词）：避免绝对化措辞（「最」「第一」「革命性」等需有据）。')
    lines.append("- 红线 6（AI 声明+时效）：**news 文此条最重**——每条事实必须带日期与信源，过时信息要标注。")
    lines.append("")
    lines.append("### 反虚构硬约束（写手必守）")
    lines.append("- 只能引用本文件内的资讯条目，不编造榜单外的新闻。")
    lines.append("- 信源 URL 原样引用，不改写。")
    lines.append('- 事件日期缺失的条目，写作时标注「（具体日期未公布）」而非编造日期。')
    lines.append("")
    lines.append("### 结构硬约束（下游兼容）")
    lines.append("- 清单主体必须用 `##` 分主题组（本文件的 `## 一、xxx` 分组可直接保留/重命名）。")
    lines.append("- 原因：article-image-studio 的 build_segments.py 用 `^##\\s+` 正则切分插图 segment，播客 conductor 按 `##` 分 `[SECTION:N]`，视频 plan_scenes 继承 segment。降级为纯 bullet 无 `##` 会断下游。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest 事实素材文件生成")
    ap.add_argument("--ranked", required=True, help="digest_ranked.json 路径")
    ap.add_argument("--output", required=True, help="输出 _research/事实素材与来源.md 路径")
    ap.add_argument("--persona", default="AI小周", help="人设名（默认 AI小周）")
    args = ap.parse_args()

    data = load_json(Path(args.ranked))
    date = data.get("date") or today_cn()
    md = build_research_md(data, args.persona, date)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    item_count = len(data.get("items", []))
    log(f"事实素材写入: {out_path}（{item_count} 条资讯，人设 {args.persona}，日期 {date}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

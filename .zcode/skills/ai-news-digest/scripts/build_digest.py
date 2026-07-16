"""ai-news-digest: 把打分后的候选列表渲染成 Markdown 日报 + AI 打分 prompt。

两种产物:
1. 日报 Markdown（人类可读榜单）— 来自 ranked 候选
2. AI 打分 prompt 片段（喂给主对话模型做跨文章排序）— 来自 prefilter 候选

相对 daily-digest 版的改动:
- prompt 子命令：候选列表带上 summary 片段（截断到 200 字），让 AI 打分能看到正文，
  不再只能凭标题判断（原版对标题党/翻译型标题打分有损）

用法:
  # 渲染日报
  <py> <scripts>/build_digest.py digest --ranked <path> --output <md path>
  # 生成打分 prompt
  <py> <scripts>/build_digest.py prompt --candidates <path> --output <prompt path> [--top 50]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(x) -> str:
    if x is None:
        return ""
    return str(x).replace("|", "\\|").replace("\n", " ").strip()


def truncate(text: str, limit: int = 200) -> str:
    """截断 summary 给 prompt 用（去 HTML 标签残留 + 限长）。"""
    if not text:
        return ""
    import re
    t = re.sub(r"<[^>]+>", " ", text)  # 去 HTML 标签残留
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit] + ("…" if len(t) > limit else "")


def cmd_digest(args) -> int:
    data = load_json(Path(args.ranked))
    items = data.get("items", [])
    out_path = Path(args.output)
    lines = [
        f"# AI 日报 · {data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))}",
        "",
        f"> 抓取时间: {data.get('fetched_at', '')}",
        f"> 候选总数: {data.get('input_count', '-')} → 精选: {len(items)}",
        "",
        "| # | 标题 | 来源 | 分类 | AI分 | 信源分 | 链接 |",
        "|---|------|------|------|------|--------|------|",
    ]
    for i, it in enumerate(items, 1):
        title = esc(it.get("title"))
        src = esc(it.get("source_name"))
        cat = esc(it.get("source_category"))
        ai_score = it.get("ai_score", "-")
        src_score = it.get("source_score", "-")
        link = it.get("link", "")
        link_md = f"[原文]({link})" if link else "—"
        lines.append(f"| {i} | {title} | {src} | {cat} | {ai_score} | {src_score} | {link_md} |")
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"日报写入: {out_path} ({len(items)} 条)")
    return 0


def cmd_prompt(args) -> int:
    data = load_json(Path(args.candidates))
    cands = data.get("candidates", [])[: args.top]
    out_path = Path(args.output)
    lines = [
        "请对以下今日 AI 资讯候选逐条打分（1-10，10 最值得收录），并给出一句中文摘要。",
        "评分维度: 时效性 / 重要性 / 与 AI 主题相关度 / 信息增量。",
        "",
        "**AI 相关度硬判定**：每条必须标 `ai_related`（true/false）。判定标准——条目主题是否与人工智能/大模型/机器学习/LLM/AI 应用/AI 行业动态直接相关。",
        "与 AI 无关的条目（如纯生活随笔、非 AI 的通用技术、产品推广、与 AI 无关的行业新闻）：`ai_related: false`，score 一律给 1。",
        "信源虽是 AI 类博客，但该条目本身与 AI 无关的，仍标 false。",
        "",
        "输出 JSON 数组，每项: {\"index\": <序号>, \"score\": <1-10>, \"ai_related\": <true|false>, \"summary\": \"<一句话摘要>\"}。",
        "仅输出 JSON，不要其他文字。",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(cands, 1):
        title = c.get("title", "").strip()
        src = c.get("source_name", "").strip()
        cat = c.get("source_category", "").strip()
        pub = c.get("published", "")
        summary = truncate(c.get("summary", ""))
        line = f"{i}. 【{src}｜{cat}】{title}（{pub}）"
        if summary:
            line += f"\n   摘要：{summary}"
        lines.append(line)
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"打分 prompt 写入: {out_path} ({len(cands)} 条)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest 日报/prompt 生成")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("digest", help="渲染 Markdown 日报")
    d.add_argument("--ranked", required=True)
    d.add_argument("--output", required=True)
    d.set_defaults(func=cmd_digest)
    p = sub.add_parser("prompt", help="生成 AI 打分 prompt")
    p.add_argument("--candidates", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--top", type=int, default=50)
    p.set_defaults(func=cmd_prompt)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""ai-news-digest Phase 2: 候选预筛（去重 + 源质量加权 + 截断）。

读 poll_feeds.py 的候选列表，按源质量（subscriberCount）加权打分并排序，截取 top-N。

打分逻辑（纯规则，无 AI 调用，零成本）:
- 基础分 = 源的 subscriberCount（归一化到 0-100）
- 标题长度奖励：标题信息量更足的轻微加分
- 标题含推广关键词的剔除（关键词从 config.json 读，避免硬编码）
- 同一源的条目数封顶（避免单源刷屏）

相对 daily-digest 版的改动:
- PENALTY_KEYWORDS / MAX_PER_SOURCE 从 config.json 读（去硬编码，便于按主题调）
- 默认关键词列表移除"招聘"（AI 公司招聘常是新闻而非推广）

用法:
  <py> <scripts>/prefilter.py --candidates <path> --sources <path> --output <path>
       [--config config.json] [--top 80]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 默认降权/剔除关键词（标题含这些视为低质/推广）；config.json 的 scoring.penalty_keywords 优先
DEFAULT_PENALTY_KEYWORDS = ["广告", "推广", "赞助", "福利", "抽奖", "限时", "秒杀", "优惠券"]
# 默认同一源最多保留的条目数（防止头部源刷屏）；config.json 的 scoring.max_per_source 优先
DEFAULT_MAX_PER_SOURCE = 5


def log(msg: str) -> None:
    print(f"[prefilter] {msg}", flush=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_source_scores(sources_data: dict) -> dict[str, dict]:
    """从 sources.json 构建源质量分数：归一化 subscriberCount 到 0-100。"""
    srcs = sources_data["sources"]
    max_sub = max((s.get("subscriberCount", 0) or 0) for s in srcs) or 1
    out: dict[str, dict] = {}
    for s in srcs:
        sub = s.get("subscriberCount", 0) or 0
        out[s["id"]] = {
            "name": s.get("name", ""),
            "score": round(sub / max_sub * 100, 2),
            "subscriber_count": sub,
            "category_desc": s.get("categoryDesc", ""),
            "type": s.get("type", ""),
        }
    return out


def title_bonus(title: str) -> float:
    """标题信息量加分：长度适中给轻微加分。"""
    n = len(title)
    if 12 <= n <= 50:
        return 5.0
    if n < 8 or n > 80:
        return -5.0
    return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest 候选预筛")
    ap.add_argument("--candidates", required=True, help="poll_feeds 输出的候选 JSON")
    ap.add_argument("--sources", required=True, help="sources.json 路径")
    ap.add_argument("--output", required=True, help="预筛结果输出 JSON")
    ap.add_argument("--config", default="", help="ai-news-digest config.json（读 scoring 段，可选）")
    ap.add_argument("--top", type=int, default=0, help="截取 top-N 候选（0=用 config 的 prefilter_top）")
    args = ap.parse_args()

    # 读 config（可选）：penalty_keywords / max_per_source / prefilter_top
    penalty_keywords = DEFAULT_PENALTY_KEYWORDS
    max_per_source = DEFAULT_MAX_PER_SOURCE
    cfg_top = 80
    if args.config:
        cfg = load_json(Path(args.config))
        scoring = cfg.get("scoring", {})
        penalty_keywords = scoring.get("penalty_keywords", penalty_keywords)
        max_per_source = scoring.get("max_per_source", max_per_source)
        cfg_top = scoring.get("prefilter_top", cfg_top)
    top_n = args.top or cfg_top

    def has_penalty(title: str) -> bool:
        t = title.lower()
        return any(k in t for k in penalty_keywords)

    cand_data = load_json(Path(args.candidates))
    sources_data = load_json(Path(args.sources))
    src_scores = build_source_scores(sources_data)

    candidates = cand_data.get("candidates", [])
    log(f"输入候选: {len(candidates)} 条（推广词表 {len(penalty_keywords)} 个，同源封顶 {max_per_source}）")

    scored: list[dict] = []
    dropped_penalty = 0
    for c in candidates:
        title = c.get("title", "")
        if has_penalty(title):
            dropped_penalty += 1
            continue
        src = src_scores.get(c["source_id"], {})
        base = src.get("score", 0)
        bonus = title_bonus(title)
        total = round(base + bonus, 2)
        out = dict(c)
        out["source_score"] = base
        out["title_bonus"] = bonus
        out["total_score"] = total
        out["source_category"] = src.get("category_desc", "")
        out["source_subscribers"] = src.get("subscriber_count", 0)
        scored.append(out)

    # 按总分降序
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    # 同源封顶：每个源最多 max_per_source 条
    per_source: dict[str, int] = {}
    capped: list[dict] = []
    dropped_cap = 0
    for c in scored:
        sid = c["source_id"]
        n = per_source.get(sid, 0)
        if n >= max_per_source:
            dropped_cap += 1
            continue
        per_source[sid] = n + 1
        capped.append(c)

    top = capped[:top_n]

    out = {
        "fetched_at": cand_data.get("fetched_at"),
        "input_count": len(candidates),
        "after_penalty_filter": len(scored),
        "after_per_source_cap": len(capped),
        "dropped_penalty": dropped_penalty,
        "dropped_per_source_cap": dropped_cap,
        "top": top_n,
        "final_count": len(top),
        "candidates": top,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"预筛结果: {len(candidates)} → {len(top)}（剔除推广{dropped_penalty}，同源封顶{dropped_cap}）")
    log(f"写入: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""ai-news-digest Phase 3: 把 AI 打分结果合并回候选，按分排序取 top，产出 ranked JSON。

相对 daily-digest 版的改动:
- 加 index 边界检查（AI 输出 index 越界时跳过并告警，不静默丢条目）
- 参数名统一为 --candidates / --scores（与其它脚本一致）
- 缺失 index 的候选记录为 unmatched，便于诊断

用法:
  <py> <scripts>/merge_scores.py --candidates <prefiltered json> --scores <scoring result json>
       --output <ranked json> [--top 20]
"""
import argparse
import json
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[merge] {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest 打分合并")
    ap.add_argument("--candidates", required=True, help="prefilter 输出的候选 JSON")
    ap.add_argument("--scores", required=True, help="AI 打分结果 JSON（[{index,score,summary}]）")
    ap.add_argument("--output", required=True, help="ranked 输出 JSON")
    ap.add_argument("--top", type=int, default=20, help="截取 top-N")
    args = ap.parse_args()

    pre = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = pre["candidates"]
    scores_raw = json.loads(Path(args.scores).read_text(encoding="utf-8"))

    # index 是 1-based，对应 cands 顺序。只对前 len(scores) 条候选打分。
    valid_scores = []
    out_of_range = 0
    for s in scores_raw:
        idx = s.get("index")
        if not isinstance(idx, int) or idx < 1 or idx > len(cands):
            out_of_range += 1
            continue
        valid_scores.append(s)
    if out_of_range:
        log(f"警告: {out_of_range} 条打分 index 越界（候选共 {len(cands)} 条），已跳过")

    smap = {s["index"]: s for s in valid_scores}
    scored_n = len(valid_scores)

    ranked = []
    unmatched = 0
    for i, c in enumerate(cands[:scored_n], 1):
        s = smap.get(i)
        if not s:
            unmatched += 1
            continue
        out = dict(c)
        out["ai_score"] = s["score"]
        out["ai_summary"] = s["summary"]
        ranked.append(out)
    if unmatched:
        log(f"警告: {unmatched} 条候选无对应打分，已跳过")

    ranked.sort(key=lambda x: (-x["ai_score"], -x.get("total_score", 0)))
    top = ranked[: args.top]

    out = {
        "date": (pre.get("fetched_at") or "")[:10],
        "fetched_at": pre.get("fetched_at"),
        "input_count": pre.get("input_count"),
        "scored_count": scored_n,
        "final_count": len(top),
        "items": top,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"{len(cands)} 候选 → AI打分 {scored_n} 合并 → top {len(top)} 写入 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""ai-news-digest Phase 4.5: 把榜单审核产出的修正指令应用到 digest_ranked.json。

审核 agent（见 agents/digest-reviewer.md）对榜单做 4 维度语义判断后，把确定性可执行的
修正写成 review_actions.json；本脚本负责把指令落地——删条目 / 降分重排，并同步重生成
digest.md 榜单，保证 ranked JSON 与给人看的榜单一致。

为什么单独成脚本（不直接让 agent 改 JSON）：
- 修正必须幂等可断点续跑（state.json review stage 崩溃后重跑需安全）
- 统计字段（final_count 等）必须与条目数同步，脚本集中保证
- 榜单 digest.md 必须与 ranked 同步重生成，避免两份数据漂移

输入 actions 格式（JSON 数组，每项二选一）：
  [
    {"action": "drop",   "title": "...", "link": "...", "reason": "..."},
    {"action": "demote", "title": "...", "link": "...", "new_score": 6, "reason": "..."}
  ]
定位键为 (title, link) 双键——title 可能重复，link 唯一；任一缺失则按另一键宽松匹配，
匹配不到的指令告警跳过（不静默丢，便于诊断 agent 误判）。

用法:
  <py> <scripts>/apply_review.py --ranked <digest_ranked.json> --actions <review_actions.json>
       --digest-md <digest.md>
"""
import argparse
import json
import sys
from pathlib import Path

# 复用同目录 build_digest.py 的榜单渲染逻辑（重生成 digest.md）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_digest import cmd_digest as render_digest  # noqa: E402


def log(msg: str) -> None:
    print(f"[review-apply] {msg}", flush=True)


def match_item(items, title: str, link: str):
    """按 (title, link) 定位条目，幂等安全优先。

    定位规则（按可靠性）：
    1. 严格双键（title AND link 都符）
    2. 单 link（link 唯一可靠，即使 title 写错也能命中）
    3. 仅当 action 没提供 link（空）时，才用 title 唯一命中兜底

    幂等关键：当 action 同时带 title+link 且 link 已不存在（说明条目已删，重跑场景），
    绝不回退到 title 匹配——否则会误删同标题的幸存条目。此时返回 (None, None) 由调用方
    作为"已删跳过"处理。
    """
    # 1. 严格双键
    for i, it in enumerate(items):
        if it.get("title") == title and it.get("link") == link:
            return i, it
    # 2. 单 link（agent 可能写错 title，但 link 唯一可靠）
    if link:
        for i, it in enumerate(items):
            if it.get("link") == link:
                log(f"宽松匹配（仅 link 命中，title 不符）：link='{link}'")
                return i, it
        # link 给定但找不到 → 幂等跳过（条目已删），不回退 title，避免误伤同标题条目
        return None, None
    # 3. action 没给 link，才用 title 兜底（仅当唯一命中）
    if title:
        hits = [(i, it) for i, it in enumerate(items) if it.get("title") == title]
        if len(hits) == 1:
            log(f"宽松匹配（action 未给 link，title 唯一命中）：title='{title}'")
            return hits[0]
        if len(hits) > 1:
            log(f"跳过（title 命中 {len(hits)} 条且无 link，无法唯一定位）：title='{title}'")
    return None, None


def apply_actions(data: dict, actions: list) -> dict:
    """就地应用 actions 到 data['items']，返回执行统计。drop 删条目，demote 改分。"""
    items = data["items"]
    dropped, demoted, skipped = [], [], []

    for act in actions:
        kind = act.get("action")
        title = act.get("title", "")
        link = act.get("link", "")
        reason = act.get("reason", "")

        i, it = match_item(items, title, link)
        if i is None:
            skipped.append({"action": kind, "title": title, "link": link, "reason": "未匹配到条目"})
            continue

        if kind == "drop":
            items.pop(i)
            dropped.append({"title": it.get("title"), "link": it.get("link"), "reason": reason})
        elif kind == "demote":
            new_score = act.get("new_score")
            if not isinstance(new_score, int) or not (1 <= new_score <= 10):
                skipped.append({"action": kind, "title": title, "link": link,
                                "reason": f"new_score 非法: {new_score}"})
                continue
            old = it.get("ai_score")
            it["ai_score"] = new_score
            demoted.append({"title": it.get("title"), "link": it.get("link"),
                            "old_score": old, "new_score": new_score, "reason": reason})
        else:
            skipped.append({"action": kind, "title": title, "link": link, "reason": "未知 action 类型"})

    # 重排（与 merge_scores.py 一致的排序键）
    items.sort(key=lambda x: (-x.get("ai_score", 0), -x.get("total_score", 0)))
    # 同步统计字段：final_count 跟随条目数；input_count/scored_count/dropped_not_ai 反映上游真实计数，不动
    data["final_count"] = len(items)

    return {"dropped": dropped, "demoted": demoted, "skipped": skipped}


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest 榜单审核修正")
    ap.add_argument("--ranked", required=True, help="digest_ranked.json（修正后原地覆盖）")
    ap.add_argument("--actions", required=True, help="review_actions.json（审核产出的修正指令）")
    ap.add_argument("--digest-md", required=True, help="digest.md 输出路径（重生成）")
    args = ap.parse_args()

    ranked_path = Path(args.ranked)
    actions_path = Path(args.actions)
    md_path = Path(args.digest_md)

    if not ranked_path.exists():
        log(f"ERROR 榜单文件不存在: {ranked_path}")
        return 1
    if not actions_path.exists():
        log(f"无修正指令文件: {actions_path}，跳过修正")
        return 0

    data = json.loads(ranked_path.read_text(encoding="utf-8"))
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    if not isinstance(actions, list):
        log(f"ERROR actions 不是 JSON 数组: {actions_path}")
        return 1

    before_count = len(data.get("items", []))
    stats = apply_actions(data, actions)
    after_count = len(data["items"])

    # 覆盖 ranked（temp/ 中间产物，无需 backup_file.py）
    ranked_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"修正完成: 删除 {len(stats['dropped'])} / 降分 {len(stats['demoted'])} / 跳过 {len(stats['skipped'])}"
        f"（{before_count} → {after_count} 条），已覆盖 {ranked_path}")

    if stats["skipped"]:
        log("被跳过的指令（agent 需检查定位键是否写错）:")
        for s in stats["skipped"]:
            log(f"  - {s['action']} title='{s.get('title')}' link='{s.get('link')}' reason={s.get('reason')}")

    # 重生成 digest.md（复用 build_digest.cmd_digest，保证与 ranked 一致）
    ns = argparse.Namespace(ranked=str(ranked_path), output=str(md_path))
    render_digest(ns)
    return 0


if __name__ == "__main__":
    sys.exit(main())

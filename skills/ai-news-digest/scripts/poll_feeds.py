"""ai-news-digest Phase 1: RSS/Atom 并发抓取 + 增量游标。

读 configs/bestblogs-sources/sources.json 里的指定类型/分类源，并发轮询所有 feed，
按时间窗口 + last_seen_link 游标双重过滤只取新增条目。输出候选列表 JSON。

相对 daily-digest 版的改动:
- 加 --categories 参数（按 sources.json 的 category 字段过滤，聚焦 AI 类）
- 修复增量游标：last_seen_link 从"只写不读"改为"时间窗口兜底 + 游标优先过滤"
  （窗口内但已见过 last_seen_link 的源不再重复抓历史；窗口跨日时也能正确增量）

用法:
  <py> <scripts>/poll_feeds.py --sources <path> --state <path> --output <path>
  [--hours 24] [--concurrency 20] [--timeout 15] [--limit-sources N]
  [--types ARTICLE] [--categories Artificial_Intelligence]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
}


def log(msg: str) -> None:
    print(f"[poll] {msg}", flush=True)


def load_sources(path: Path, types: list[str], categories: list[str] | None) -> list[dict]:
    """加载信源，按 types 过滤；若给 categories 则再按 category 过滤。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    srcs = [s for s in data["sources"] if s["type"] in types and s.get("url")]
    if categories:
        wanted = set(categories)
        srcs = [s for s in srcs if s.get("category") in wanted]
    return srcs


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            log(f"state 文件损坏，重新初始化: {path}")
    return {"sources": {}, "last_run": None}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_entry_date(entry) -> str | None:
    """取条目的发布/更新时间，返回 ISO 字符串。失败返回 None。"""
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    for key in ("published", "updated"):
        v = entry.get(key)
        if v:
            return v
    return None


def is_feed_response(content: bytes, url: str) -> bool:
    """快速判断响应是否为 feed（非 HTML 首页）。"""
    head = content[:2000].decode("utf-8", errors="ignore").lower()
    if "<rss" in head or "<feed" in head or "<atom" in head:
        return True
    if url.lower().endswith((".xml", ".rss")):
        return True
    return False


def poll_one(source: dict, hours_window: float, timeout: float, seen_link: str | None) -> dict:
    """抓单个源，返回该源的新条目。

    seen_link 是该源上一次抓到的最新条目链接（游标）。若设置，则遇到该链接时停止
    （因为它及之前的都是历史条目）；同时叠加时间窗口兜底，防止游标失效（链接变更）。
    """
    sid = source["id"]
    url = source["url"]
    result = {"id": sid, "name": source.get("name", ""), "url": url, "status": "ok",
              "entries": [], "error": None}
    t0 = time.time()
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        result["http_status"] = r.status_code
        if r.status_code != 200:
            result["status"] = "http_error"
            result["error"] = f"HTTP {r.status_code}"
            return result
        if not is_feed_response(r.content, url):
            result["status"] = "not_a_feed"
            result["error"] = "响应是 HTML 页面，非 feed"
            return result
        parsed = feedparser.parse(r.content)
        entries = parsed.get("entries", [])
        if not entries:
            result["status"] = "empty"
            return result
        cutoff = datetime.now(timezone.utc).timestamp() - hours_window * 3600
        for e in entries:
            iso = parse_entry_date(e)
            # 时间过滤：解析出 epoch 且在窗口内；无法解析时间的条目（标题非空）保留，避免漏时效内容
            tp = e.get("published_parsed") or e.get("updated_parsed")
            if tp:
                try:
                    epoch = datetime(*tp[:6], tzinfo=timezone.utc).timestamp()
                    if epoch < cutoff:
                        continue
                except Exception:
                    pass
            link = e.get("link") or ""
            title = (e.get("title") or "").strip()
            if not title:
                continue
            # 游标过滤：遇到上次见过的最新链接，停止（它及之前都是历史）
            if seen_link and link == seen_link:
                break
            result["entries"].append({
                "title": title,
                "link": link,
                "published": iso,
                "summary": (e.get("summary") or e.get("description") or "").strip(),
            })
        result["elapsed"] = round(time.time() - t0, 2)
    except requests.exceptions.RequestException as e:
        result["status"] = "fetch_error"
        result["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    except Exception as e:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-news-digest RSS 轮询")
    ap.add_argument("--sources", required=True, help="sources.json 路径")
    ap.add_argument("--state", required=True, help="state.json 路径（增量游标）")
    ap.add_argument("--output", required=True, help="候选列表输出 JSON 路径")
    ap.add_argument("--hours", type=float, default=24.0, help="时间窗口（小时）")
    ap.add_argument("--concurrency", type=int, default=20, help="并发抓取数")
    ap.add_argument("--timeout", type=float, default=15.0, help="单源超时（秒）")
    ap.add_argument("--limit-sources", type=int, default=0, help="限制源数量（0=不限，调试用）")
    ap.add_argument("--types", default="ARTICLE", help="源类型逗号分隔（默认 ARTICLE）")
    ap.add_argument("--categories", default="", help="源分类逗号分隔（如 Artificial_Intelligence；默认不过滤）")
    args = ap.parse_args()

    sources_path = Path(args.sources)
    state_path = Path(args.state)
    output_path = Path(args.output)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    categories = [c.strip() for c in args.categories.split(",") if c.strip()] or None
    sources = load_sources(sources_path, types, categories)
    if args.limit_sources > 0:
        sources = sources[: args.limit_sources]
    log(f"待抓取源: {len(sources)} 个（类型 {types}，分类 {categories or '全量'}，窗口 {args.hours}h，并发 {args.concurrency}）")

    state = load_state(state_path)

    candidates: list[dict] = []
    stats = {"ok": 0, "empty": 0, "not_a_feed": 0, "http_error": 0, "fetch_error": 0, "error": 0}
    t_start = time.time()

    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(poll_one, s, args.hours, args.timeout,
                               state["sources"].get(s["id"], {}).get("last_seen_link")): s
                   for s in sources}
        for fut in cf.as_completed(futures):
            src = futures[fut]
            try:
                res = fut.result()
            except Exception as e:  # noqa: BLE001
                stats["error"] += 1
                log(f"  [异常] {src.get('name', '')[:24]}: {e}")
                continue
            stats[res["status"]] = stats.get(res["status"], 0) + 1
            if res["entries"]:
                for e in res["entries"]:
                    candidates.append({
                        "title": e["title"],
                        "link": e["link"],
                        "published": e["published"],
                        "summary": e["summary"],
                        "source_id": res["id"],
                        "source_name": res["name"],
                        "source_url": res["url"],
                    })
            # 更新游标：记录该源本次抓到的最新条目链接（去重锚点）
            latest = res["entries"][0]["link"] if res["entries"] else state["sources"].get(res["id"], {}).get("last_seen_link")
            state["sources"][res["id"]] = {
                "name": res["name"],
                "last_seen_link": latest,
                "last_status": res["status"],
                "last_polled": datetime.now(timezone.utc).isoformat(),
            }

    # 全局去重（同一 link 只保留一条，优先更早抓到的）
    seen_links: set[str] = set()
    deduped: list[dict] = []
    for c in candidates:
        key = c["link"] or c["title"]
        if key in seen_links:
            continue
        seen_links.add(key)
        deduped.append(c)

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state_path, state)

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "hours_window": args.hours,
        "source_count": len(sources),
        "candidate_count": len(deduped),
        "stats": stats,
        "elapsed_seconds": round(time.time() - t_start, 1),
        "candidates": deduped,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"完成: {len(deduped)} 候选 (源抓取统计 {stats})，耗时 {out['elapsed_seconds']}s")
    log(f"候选写入: {output_path}")
    log(f"游标写入: {state_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

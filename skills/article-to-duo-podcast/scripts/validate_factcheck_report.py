"""
validate_factcheck_report.py — 校验 duo-factchecker 风险报告的 schema 与逻辑一致性。

检查：
  - 顶层必要字段齐全（round, network_ok, hard_block, summary, claims, fix_directives）
  - claim 字段齐全且 verdict/category 枚举合法
  - hard_block 与 claims 一致：== 存在硬事实类(version/product/date/news) 且 verdict∈{unverifiable,outdated}
  - network_ok=false 时：所有 claim verdict 应为 unverified_due_to_network，且 hard_block 应为 false

Usage:
  python validate_factcheck_report.py --report scorecards/factcheck-round-1.json
"""
import argparse
import json
import sys

HARD_CATEGORIES = {"version", "product", "date", "news"}
BLOCK_VERDICTS = {"unverifiable", "outdated"}
VALID_CATEGORIES = {"version", "product", "date", "news", "data"}
VALID_VERDICTS = {"verified", "unverifiable", "outdated", "corrected",
                  "unverified_due_to_network"}
REPORT_REQUIRED = ["round", "network_ok", "hard_block", "summary", "claims", "fix_directives"]
CLAIM_REQUIRED = ["claim", "source_ref", "category", "verdict", "evidence"]


def compute_hard_block(claims):
    """硬事实类(version/product/date/news) 且 verdict∈{unverifiable,outdated} → True。"""
    for c in claims:
        if c.get("category") in HARD_CATEGORIES and c.get("verdict") in BLOCK_VERDICTS:
            return True
    return False


def validate_report(report):
    """返回 (ok, errors)。校验 schema + hard_block 一致性 + network soft 一致性。"""
    errors = []
    for k in REPORT_REQUIRED:
        if k not in report:
            errors.append(f"missing top-level field: {k}")

    claims = report.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        claims = []

    for i, c in enumerate(claims):
        for k in CLAIM_REQUIRED:
            if k not in c:
                errors.append(f"claim[{i}] missing field: {k}")
        if c.get("category") not in VALID_CATEGORIES:
            errors.append(f"claim[{i}] invalid category: {c.get('category')}")
        if c.get("verdict") not in VALID_VERDICTS:
            errors.append(f"claim[{i}] invalid verdict: {c.get('verdict')}")

    expected_hb = compute_hard_block(claims)
    if report.get("hard_block") != expected_hb:
        errors.append(f"hard_block={report.get('hard_block')} but expected {expected_hb}")

    if report.get("network_ok") is False:
        for i, c in enumerate(claims):
            if c.get("verdict") != "unverified_due_to_network":
                errors.append(
                    f"network_ok=false but claim[{i}] verdict={c.get('verdict')}")
        if report.get("hard_block") is True:
            errors.append("network_ok=false but hard_block=true")

    return (len(errors) == 0), errors


def merge_directives(fc_directives, judge_directives):
    """按 (target, problem) 去重合并；factcheck 优先；每条加 source 字段。"""
    merged = []
    seen = set()
    for d in fc_directives:
        key = (d.get("target"), d.get("problem"))
        if key not in seen:
            seen.add(key)
            merged.append({**d, "source": "factcheck"})
    for d in judge_directives:
        key = (d.get("target"), d.get("problem"))
        if key not in seen:
            seen.add(key)
            merged.append({**d, "source": "judge"})
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    ok, errors = validate_report(report)
    print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

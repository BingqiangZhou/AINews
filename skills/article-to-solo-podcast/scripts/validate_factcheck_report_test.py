"""Tests for validate_factcheck_report.py"""
from validate_factcheck_report import compute_hard_block, validate_report, merge_directives


def _claim(category, verdict):
    return {"claim": "x", "source_ref": "s", "category": category,
            "verdict": verdict, "evidence": "e"}


def _report(claims, hard_block=False, network_ok=True):
    return {"round": 1, "network_ok": network_ok, "hard_block": hard_block,
            "summary": "s", "claims": claims, "fix_directives": []}


def test_schema_valid():
    ok, errors = validate_report(_report([_claim("version", "verified")], hard_block=False))
    assert ok, errors


def test_hard_block_version_unverifiable():
    claims = [_claim("version", "unverifiable")]
    assert compute_hard_block(claims) is True
    ok, errors = validate_report(_report(claims, hard_block=True))
    assert ok, errors


def test_hard_block_false_when_all_verified():
    claims = [_claim("version", "verified"), _claim("date", "verified")]
    assert compute_hard_block(claims) is False


def test_soft_data_no_hardblock():
    claims = [_claim("data", "unverifiable")]
    assert compute_hard_block(claims) is False
    ok, errors = validate_report(_report(claims, hard_block=False))
    assert ok, errors


def test_network_soft_fallback():
    claims = [{"claim": "x", "source_ref": "s", "category": "version",
               "verdict": "unverified_due_to_network", "evidence": "e"}]
    ok, errors = validate_report(_report(claims, hard_block=False, network_ok=False))
    assert ok, errors


def test_network_soft_rejects_hardblock():
    claims = [{"claim": "x", "source_ref": "s", "category": "version",
               "verdict": "unverified_due_to_network", "evidence": "e"}]
    ok, errors = validate_report(_report(claims, hard_block=True, network_ok=False))
    assert not ok
    assert any("hard_block=true" in e for e in errors)


def test_directives_merge_with_judge():
    fc = [{"target": "§6", "problem": "版本号 X.Y", "fix": "删除"}]
    judge = [{"target": "§6", "problem": "版本号 X.Y", "fix": "删除"},
             {"target": "§2", "problem": "机器词'首先'", "fix": "改为口语过渡"}]
    merged = merge_directives(fc, judge)
    # 去重后 2 条；同 (target,problem) 只留 factcheck 那条
    assert len(merged) == 2
    keys = {(m["target"], m["problem"]) for m in merged}
    assert keys == {("§6", "版本号 X.Y"), ("§2", "机器词'首先'")}
    dup = [m for m in merged if m["target"] == "§6"][0]
    assert dup["source"] == "factcheck"
    only_judge = [m for m in merged if m["target"] == "§2"][0]
    assert only_judge["source"] == "judge"

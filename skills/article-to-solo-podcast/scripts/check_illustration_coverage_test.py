"""check_illustration_coverage.py 的单元测试。

覆盖：blueprint 模式提取 Section、[SECTION:N] 标记模式提取、labels 覆盖校验、
跳过逻辑（无 meta / scene 类型）、退出码。
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("check_illustration_coverage.py")
_spec = importlib.util.spec_from_file_location("check_illustration_coverage", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

extract_sections = _module.extract_sections
check_coverage = _module.check_coverage
format_report = _module.format_report


# ── extract_sections：blueprint 模式 ──────────────────────────────────────

def test_extract_blueprint_sections():
    """blueprint.md 的 ### Section N：<heading> 块正确提取。"""
    blueprint = (
        "# 蓝图\n\n## 叙事弧\n\n"
        "### Section 0：第一章\n配图：infographic\n1. 要点A\n2. 要点B\n\n"
        "### Section 1：第二章\n配图：flowchart\n1. 步骤A\n\n"
        "### Section 2：第三章\n无配图\n1. 内容\n"
    )
    sections = extract_sections(blueprint)

    assert 0 in sections
    assert 1 in sections
    assert 2 in sections
    assert "要点A" in sections[0]
    assert "步骤A" in sections[1]


def test_extract_blueprint_skips_preamble():
    """blueprint 的 preamble（### Section 之前的内容）不被当作 section。"""
    blueprint = (
        "# 蓝图\n## 切入角度\n一些内容\n\n"
        "### Section 0：第一章\n要点\n"
    )
    sections = extract_sections(blueprint)

    assert 0 in sections
    assert "切入角度" not in sections.get(0, "")


# ── extract_sections：[SECTION:N] 标记模式 ────────────────────────────────

def test_extract_marker_sections():
    """[SECTION:N] 标记行后的文本正确提取（draft_v1 / 播客_脚本.txt 模式）。"""
    script = (
        "[SECTION:OPENING]\n这是片头旁白。\n\n"
        "[SECTION:0]\n第一章的内容，讲到核心概念。\n\n"
        "[SECTION:1]\n第二章的内容。\n\n"
        "[SECTION:ENDING]\n片尾 CTA。\n"
    )
    sections = extract_sections(script)

    assert "这是片头旁白" in sections["OPENING"]
    assert "第一章的内容" in sections[0]
    assert "第二章的内容" in sections[1]
    assert "片尾 CTA" in sections["ENDING"]


def test_extract_marker_last_section_to_eof():
    """最后一个 [SECTION:N] 标记的文本延伸到文件末尾。"""
    script = "[SECTION:0]\n第一章。\n这是末尾内容。"
    sections = extract_sections(script)

    assert "末尾内容" in sections[0]


# ── check_coverage：核心校验逻辑 ──────────────────────────────────────────

def test_full_coverage():
    """所有 labels 都在脚本中出现 → coverage_rate=1.0，missing=0。"""
    segments = [
        {
            "index": 0, "role": "body", "heading": "第一章",
            "illustration_meta": {"type": "infographic", "title_text": "概念", "labels": ["AI代劳", "判断"]},
        },
    ]
    script = "### Section 0：第一章\n要点讲到了 AI代劳 和 判断 两个词。\n"

    result = check_coverage(segments, script)

    assert result["total_labels"] == 2
    assert result["covered_labels"] == 2
    assert result["missing_labels"] == 0
    assert result["coverage_rate"] == 1.0
    assert result["details"][0]["missing"] == []


def test_partial_coverage():
    """部分 labels 缺失 → coverage_rate < 1.0，missing 列出缺失项。"""
    segments = [
        {
            "index": 0, "role": "body", "heading": "副业",
            "illustration_meta": {
                "type": "infographic", "title_text": "副业",
                "labels": ["写作变现", "视频剪辑", "AI配音"],
            },
        },
    ]
    script = "### Section 0：副业\n只讲到了 写作变现，没讲另外两个。\n"

    result = check_coverage(segments, script)

    assert result["total_labels"] == 3
    assert result["covered_labels"] == 1
    assert result["missing_labels"] == 2
    assert "视频剪辑" in result["details"][0]["missing"]
    assert "AI配音" in result["details"][0]["missing"]
    assert "写作变现" in result["details"][0]["covered"]


def test_skip_segments_without_meta():
    """无 illustration_meta 的 segment 被跳过，不计入 total_labels。"""
    segments = [
        {"index": 0, "role": "body", "heading": "无图段"},  # 无 meta
        {
            "index": 1, "role": "body", "heading": "有图段",
            "illustration_meta": {"type": "infographic", "labels": ["词A"]},
        },
    ]
    script = "### Section 1：有图段\n讲到了 词A。\n"

    result = check_coverage(segments, script)

    assert result["total_labels"] == 1  # 只算有 meta 的段
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["index"] == 0


def test_skip_scene_type_no_labels():
    """scene 类型（labels 为 None/空）的 segment 被跳过。"""
    segments = [
        {
            "index": 0, "role": "body", "heading": "氛围段",
            "illustration_meta": {"type": "scene", "title_text": None, "labels": None},
        },
    ]
    script = "### Section 0：氛围段\n一些氛围描写。\n"

    result = check_coverage(segments, script)

    assert result["total_labels"] == 0
    assert result["coverage_rate"] == 1.0  # 无 labels 可校验 = 视为全覆盖
    assert len(result["skipped"]) == 1


def test_skip_opening_ending_segments():
    """opening/ending 段不参与校验（只校验 body 段）。"""
    segments = [
        {"index": "OPENING", "role": "opening", "illustration_meta": {"type": "scene", "labels": ["片头词"]}},
        {"index": 0, "role": "body", "heading": "正文",
         "illustration_meta": {"type": "infographic", "labels": ["正文词"]}},
        {"index": "ENDING", "role": "ending", "illustration_meta": {"type": "scene", "labels": ["片尾词"]}},
    ]
    script = "### Section 0：正文\n讲到了 正文词。\n"

    result = check_coverage(segments, script)

    assert result["total_labels"] == 1  # 只算 body 段
    assert result["covered_labels"] == 1


def test_fallback_to_full_text_when_no_section_markers():
    """脚本无 section 标记时，用全文兜底匹配（保守，可能漏报但不崩）。"""
    segments = [
        {
            "index": 0, "role": "body", "heading": "段",
            "illustration_meta": {"type": "infographic", "labels": ["关键词"]},
        },
    ]
    script = "这是一段没有 section 标记的脚本，但包含了关键词。\n"

    result = check_coverage(segments, script)

    assert result["covered_labels"] == 1  # 全文兜底命中


def test_empty_segments():
    """空 segments → 无可校验，coverage_rate=1.0。"""
    result = check_coverage([], "任意脚本")

    assert result["total_labels"] == 0
    assert result["coverage_rate"] == 1.0
    assert result["details"] == []


# ── format_report ─────────────────────────────────────────────────────────

def test_report_full_coverage():
    """全覆盖的报告含 ✓ 标记。"""
    result = {
        "total_labels": 2, "covered_labels": 2, "missing_labels": 0,
        "coverage_rate": 1.0, "details": [], "skipped": [],
    }
    report = format_report(result)

    assert "100%" in report
    assert "✓" in report


def test_report_partial_coverage():
    """有缺失的报告含 ✗ 和缺失标签列表。"""
    result = {
        "total_labels": 3, "covered_labels": 1, "missing_labels": 2,
        "coverage_rate": 0.333,
        "details": [
            {"index": 0, "heading": "副业", "labels": ["a", "b", "c"],
             "missing": ["b", "c"], "covered": ["a"]},
        ],
        "skipped": [],
    }
    report = format_report(result)

    assert "✗" in report
    assert "b" in report and "c" in report


# ── 集成：多段混合场景 ───────────────────────────────────────────────────

def test_mixed_scenario_multiple_segments():
    """多段混合：有图段全覆盖、有图段部分覆盖、无图段跳过。"""
    segments = [
        {"index": 0, "role": "body", "heading": "无图段"},  # 跳过
        {
            "index": 1, "role": "body", "heading": "概念段",
            "illustration_meta": {"type": "infographic", "labels": ["概念A", "概念B"]},
        },
        {
            "index": 2, "role": "body", "heading": "流程段",
            "illustration_meta": {"type": "flowchart", "labels": ["步骤1", "步骤2", "步骤3"]},
        },
    ]
    script = (
        "### Section 1：概念段\n讲到了 概念A 和 概念B。\n\n"
        "### Section 2：流程段\n只讲到了 步骤1，漏了另外两个。\n"
    )

    result = check_coverage(segments, script)

    assert result["total_labels"] == 5
    assert result["covered_labels"] == 3  # 概念A, 概念B, 步骤1
    assert result["missing_labels"] == 2  # 步骤2, 步骤3
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["index"] == 0

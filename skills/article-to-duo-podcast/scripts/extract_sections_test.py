"""extract_sections.py 的单元测试。

覆盖：标记剥离、字符偏移、无标记向后兼容、边界情况（首行/末行/连续标记）。
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("extract_sections.py")
_spec = importlib.util.spec_from_file_location("extract_sections", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

extract_sections = _module.extract_sections


def test_strips_markers_and_records_offsets():
    """含 3 个标记 → clean 无标记 + 3 节偏移正确。"""
    script = (
        "[SECTION:0]\n"
        "第一节内容。\n"
        "\n"
        "[SECTION:1]\n"
        "第二节内容。\n"
        "[SECTION:2]\n"
        "第三节。"
    )
    clean, sections = extract_sections(script)

    assert "[SECTION" not in clean
    assert len(sections) == 3
    # clean 文本应是三节内容拼接（标记行整行删除）
    assert clean == "第一节内容。\n\n第二节内容。\n第三节。"
    # 偏移正确指向 clean 文本
    # clean = "第一节内容。\n\n第二节内容。\n第三节。" (19 chars)
    # offsets: [0,8) [8,15) [15,19)
    assert sections[0] == {"index": 0, "char_start": 0, "char_end": 8}
    assert sections[1] == {"index": 1, "char_start": 8, "char_end": 15}
    assert sections[2] == {"index": 2, "char_start": 15, "char_end": 19}


def test_no_markers_returns_original_and_empty_sections():
    """无标记 → clean=原文，sections=[]（向后兼容）。"""
    script = "就是普通播客脚本。\n没有分节标记。\n"
    clean, sections = extract_sections(script)

    assert clean == script
    assert sections == []


def test_marker_at_first_line():
    """标记在首行（紧跟脚本开始）。"""
    script = "[SECTION:0]\n正文从这里开始。"
    clean, sections = extract_sections(script)

    assert clean == "正文从这里开始。"
    assert sections == [{"index": 0, "char_start": 0, "char_end": len(clean)}]


def test_marker_at_last_line_followed_by_content():
    """最后一个标记后有内容 → 该节 char_end = 文本末尾。"""
    script = "前奏。\n[SECTION:0]\n第一节内容。\n[SECTION:1]\n第二节。"
    clean, sections = extract_sections(script)

    # "前奏。\n" 在第一个标记前，算进 section 0 的开头（标记前的内容归到下一节）
    assert sections[0]["char_start"] == len("前奏。\n")
    assert sections[1]["char_end"] == len(clean)


def test_consecutive_markers_create_empty_section():
    """连续两个标记 → 中间产生空内容节（char_start==char_end）。"""
    script = "[SECTION:0]\n内容A\n[SECTION:1]\n[SECTION:2]\n内容C"
    clean, sections = extract_sections(script)

    assert len(sections) == 3
    # section 1 在 "内容A\n" 之后、section 2 之前，内容为空
    sec1 = [s for s in sections if s["index"] == 1][0]
    assert sec1["char_start"] == sec1["char_end"]


def test_non_section_brackets_not_stripped():
    """非 [SECTION:N] 的方括号（如 [MIDHOOK@x]）不被剥离。"""
    script = "[SECTION:0]\n正文。\n[MIDHOOK@中段]\n继续。"
    clean, sections = extract_sections(script)

    assert "[MIDHOOK@中段]" in clean  # 保留
    assert "[SECTION" not in clean     # 剥离
    assert len(sections) == 1


def test_marker_with_surrounding_whitespace():
    """标记行前后有空格仍能识别。"""
    script = "  [SECTION:0]  \n内容。"
    clean, sections = extract_sections(script)

    assert clean == "内容。"
    assert sections == [{"index": 0, "char_start": 0, "char_end": 3}]


def test_section_index_not_consecutive_still_sorted_by_position():
    """section index 跳号（如 0,2,5）→ 仍按出现位置顺序输出，保留原 index 值。"""
    script = "[SECTION:0]\nA\n[SECTION:5]\nB"
    clean, sections = extract_sections(script)

    assert [s["index"] for s in sections] == [0, 5]
    assert sections[0]["char_end"] == sections[1]["char_start"]


# ── 片头片尾标记 OPENING/ENDING（新增）─────────────────────────────────────

def test_opening_ending_string_markers_stripped_and_indexed():
    """[SECTION:OPENING] / [SECTION:ENDING] 标记正确剥离，index 为字符串。"""
    script = (
        "[SECTION:OPENING]\n"
        "片头独白。\n"
        "[SECTION:0]\n"
        "正文第一节。\n"
        "[SECTION:1]\n"
        "正文第二节。\n"
        "[SECTION:ENDING]\n"
        "片尾 CTA。"
    )
    clean, sections = extract_sections(script)

    assert "[SECTION" not in clean
    assert len(sections) == 4
    # index 类型：OPENING/ENDING 是字符串，body 是整数
    assert sections[0]["index"] == "OPENING"
    assert sections[1]["index"] == 0
    assert sections[2]["index"] == 1
    assert sections[3]["index"] == "ENDING"
    # 连续偏移
    assert sections[0]["char_start"] == 0
    assert sections[0]["char_end"] == sections[1]["char_start"]
    assert sections[-1]["char_end"] == len(clean)


def test_mixed_string_and_int_markers_no_regression():
    """混合 OPENING/整数/ENDING 标记 + 纯整数标记都不回归。"""
    # 纯整数（旧脚本）
    script_old = "[SECTION:0]\nA\n[SECTION:1]\nB"
    clean_old, sections_old = extract_sections(script_old)
    assert [s["index"] for s in sections_old] == [0, 1]

    # 混合（新脚本）
    script_new = "[SECTION:OPENING]\n片头\n[SECTION:0]\n正文"
    clean_new, sections_new = extract_sections(script_new)
    assert [s["index"] for s in sections_new] == ["OPENING", 0]


def test_opening_only_marker():
    """只有 [SECTION:OPENING]，无 body/ending。"""
    script = "[SECTION:OPENING]\n只有片头内容。"
    clean, sections = extract_sections(script)

    assert clean == "只有片头内容。"
    assert sections == [{"index": "OPENING", "char_start": 0, "char_end": 7}]

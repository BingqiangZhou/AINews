"""Tests for validate_duo_script.py — anti-AI tell detection (软警告).

双人版的 detect_anti_ai 与单人版逻辑一致（排比/路标/套词/AI高频词检测），
这些用例仍适用。
"""
import sys
from pathlib import Path

# 让测试能 import 同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_detects_parallel_triad_ending():
    from validate_duo_script import detect_anti_ai
    text = "改写比朗读值钱，量化打分比凭感觉靠谱，单次合成比拆段保音色。"
    warns = detect_anti_ai(text)
    assert any("排比" in w for w in warns), f"应检出三段排比，got {warns}"


def test_detects_signpost_numbering():
    from validate_duo_script import detect_anti_ai
    text = "先说第一关。这就是第二关。第三关是合成。"
    warns = detect_anti_ai(text)
    assert any("路标" in w for w in warns), f"应检出路标编号，got {warns}"


def test_detects_repeated_connective():
    from validate_duo_script import detect_anti_ai
    text = "说到这你可能会问A。说到这你可能会问B。"
    warns = detect_anti_ai(text)
    assert any("套式连接词" in w for w in warns), f"应检出套式连接词反复，got {warns}"


def test_detects_ai_buzzword():
    from validate_duo_script import detect_anti_ai
    warns = detect_anti_ai("这事反直觉。")
    assert any("反直觉" in w for w in warns), f"应检出 AI 高频词，got {warns}"


def test_clean_text_no_warning():
    from validate_duo_script import detect_anti_ai
    text = "你有没有听过那种一听就是 AI 念的播客？我最近才发现，差在哪根本不是声音。"
    assert detect_anti_ai(text) == [], f"干净文本不应告警，got {detect_anti_ai(text)}"


# --- 双人对话专属校验测试 ---

def test_strip_role_tag():
    from validate_duo_script import strip_role_tag
    assert strip_role_tag("A：这是主播A的话") == ("a", "这是主播A的话")
    assert strip_role_tag("B：这是主播B的话") == ("b", "这是主播B的话")
    assert strip_role_tag("  A： 带空格") == ("a", "带空格")
    assert strip_role_tag("普通行无标注") == (None, "普通行无标注")


def test_check_dialogue_format_ok():
    from validate_duo_script import check_dialogue_format
    text = "[SECTION:0]\nA：第一句\nB：第二句\nA：第三句\n"
    ok, issues = check_dialogue_format(text)
    assert ok, f"格式正确应通过，got issues={issues}"


def test_check_dialogue_format_missing_tag():
    from validate_duo_script import check_dialogue_format
    text = "A：第一句\n这句没有角色标注\nB：第三句\n"
    ok, issues = check_dialogue_format(text)
    assert not ok, "缺角色标注应失败"
    assert len(issues) == 1


def test_role_balance_and_turns():
    from validate_duo_script import check_role_balance_and_turns
    # A 说 3 段、B 说 3 段交替，平衡
    text = "A：一一\nB：二二\nA：三三\nB：四四\nA：五五\nB：六六\n"
    balance_ok, turn_ok, consec_ok, a_share, turn_count, max_consec, _detail = \
        check_role_balance_and_turns(text, 0.35, 0.65, 3, 4)
    assert balance_ok, f"A/B 平衡应通过，a_share={a_share}"
    assert turn_ok, f"轮次应达标，turn_count={turn_count}"
    assert turn_count == 6, f"6 段交替应是 6 轮，got {turn_count}"
    assert max_consec == 1, f"无连续同角色，max_consec 应=1，got {max_consec}"


def test_role_balance_imbalanced():
    from validate_duo_script import check_role_balance_and_turns
    # A 说 9 段、B 说 1 段，严重失衡
    text = "\n".join(["A：内容" for _ in range(9)] + ["B：内容"])
    balance_ok, _turn_ok, _consec_ok, a_share, _tc, max_consec, _det = \
        check_role_balance_and_turns(text, 0.35, 0.65, 3, 4)
    assert not balance_ok, f"A 占 90% 应失衡，a_share={a_share}"
    assert max_consec == 9, f"A 连续 9 段，max_consec 应=9，got {max_consec}"


def test_strip_all_marks():
    from validate_duo_script import strip_all_marks
    text = "[SECTION:0]\nA：主播A的话\nB：主播B的话\n"
    clean = strip_all_marks(text)
    assert "[SECTION" not in clean, "应剥 section 标记"
    assert "A：" not in clean and "B：" not in clean, "应剥角色标注"
    assert "主播A的话" in clean and "主播B的话" in clean

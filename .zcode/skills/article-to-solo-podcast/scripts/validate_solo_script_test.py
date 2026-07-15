"""Tests for validate_solo_script.py — anti-AI tell detection (软警告)."""
import sys
from pathlib import Path

# 让测试能 import 同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_detects_parallel_triad_ending():
    from validate_solo_script import detect_anti_ai
    text = "改写比朗读值钱，量化打分比凭感觉靠谱，单次合成比拆段保音色。"
    warns = detect_anti_ai(text)
    assert any("排比" in w for w in warns), f"应检出三段排比，got {warns}"


def test_detects_signpost_numbering():
    from validate_solo_script import detect_anti_ai
    text = "先说第一关。这就是第二关。第三关是合成。"
    warns = detect_anti_ai(text)
    assert any("路标" in w for w in warns), f"应检出路标编号，got {warns}"


def test_detects_repeated_connective():
    from validate_solo_script import detect_anti_ai
    text = "说到这你可能会问A。说到这你可能会问B。"
    warns = detect_anti_ai(text)
    assert any("套式连接词" in w for w in warns), f"应检出套式连接词反复，got {warns}"


def test_detects_ai_buzzword():
    from validate_solo_script import detect_anti_ai
    warns = detect_anti_ai("这事反直觉。")
    assert any("反直觉" in w for w in warns), f"应检出 AI 高频词，got {warns}"


def test_clean_text_no_warning():
    from validate_solo_script import detect_anti_ai
    text = "你有没有听过那种一听就是 AI 念的播客？我最近才发现，差在哪根本不是声音。"
    assert detect_anti_ai(text) == [], f"干净文本不应告警，got {detect_anti_ai(text)}"

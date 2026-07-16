"""ingest_article.py 的单元测试（核心清洗逻辑）。

ingest 负责把 Markdown 文章清洗成播客源材料（剥 frontmatter/代码块/图片/
链接/强调/标题井号，保留正文文字）。分段信息不再由 ingest 负责——改由
article-illustrator 的 build_segments.py 产出 imgs/segments.json。
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("ingest_article.py")
_spec = importlib.util.spec_from_file_location("ingest_article", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

ingest = _module.ingest


def test_strips_markdown_syntax_keeps_text():
    """ingest 剥 Markdown 语法，保留正文文字。"""
    md = (
        "# 标题\n\n"
        "## 一、章A\n\n"
        "正文有 **强调** 和 [链接](url) 和 `code`。\n\n"
        "![图片](imgs/x.png)\n\n"
        "列表项。\n"
    )
    clean = ingest(md)

    # 标题文字保留（井号去掉）
    assert "标题" in clean
    assert "一、章A" in clean
    # Markdown 语法被剥
    assert "**" not in clean
    assert "](url)" not in clean
    assert "![" not in clean
    assert "`" not in clean
    assert "##" not in clean


def test_strips_frontmatter():
    """YAML frontmatter 被剥。"""
    md = "---\ntitle: foo\n---\n\n正文。\n"
    clean = ingest(md)

    assert "title" not in clean
    assert "正文。" in clean


def test_strips_code_fences():
    """代码块（含内容）被剥。"""
    md = "正文。\n\n```python\nprint('hi')\n```\n\n更多正文。\n"
    clean = ingest(md)

    assert "print" not in clean
    assert "正文。" in clean
    assert "更多正文。" in clean


def test_strips_images():
    """图片引用被剥。"""
    md = "正文。\n\n![描述](imgs/01.png)\n\n继续。\n"
    clean = ingest(md)

    assert "![" not in clean
    assert "imgs/01.png" not in clean
    assert "正文。" in clean


def test_h1_and_h2_headings_text_preserved():
    """标题井号去掉，但标题文字保留（供下游阅读）。"""
    md = "# 大标题\n\n## 章节\n\n内容。\n"
    clean = ingest(md)

    assert "大标题" in clean
    assert "章节" in clean
    assert "#" not in clean


def test_no_section_markers_in_clean():
    """ingest 不再注入任何分段标记（分段由 build_segments 负责）。

    回归守护：确保 ingest 回归纯清洗，不掺结构标记。
    """
    md = "## 一、章\n\n内容。\n\n## 二、章\n\n内容。\n"
    clean = ingest(md)

    assert "[SECTION" not in clean

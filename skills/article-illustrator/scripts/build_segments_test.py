"""build_segments.py 的单元测试。

覆盖：body 段配对、opening/ending 段、自动扫描片头片尾图、向后兼容、
路径 A（--from-outline 模式）、illustration_meta 提取。
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("build_segments.py")
_spec = importlib.util.spec_from_file_location("build_segments", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

build_segments = _module.build_segments
detect_special_images = _module.detect_special_images
parse_outline_illustrations = _module.parse_outline_illustrations
extract_illustration_meta = _module.extract_illustration_meta
build_meta_map = _module.build_meta_map


# ── body 段（现有逻辑，role=body）──────────────────────────────────────────

def test_one_to_one_six_headings_six_images():
    """正常：6 标题 6 图，1:1 配对，每图归属前一个标题。"""
    md = (
        "# 文章标题\n\n引言。\n\n"
        "## 一、第一章\n\n内容A\n\n![图1](imgs/01.png)\n\n"
        "## 二、第二章\n\n内容B\n\n![图2](imgs/02.png)\n\n"
    )
    segs = build_segments(md)

    assert len(segs) == 2
    assert all(s["role"] == "body" for s in segs)
    assert segs[0]["heading"] == "一、第一章"
    assert segs[0]["illustration"] == "imgs/01.png"
    assert segs[0]["illustration_line"] == 9
    assert segs[1]["heading"] == "二、第二章"
    assert segs[1]["illustration"] == "imgs/02.png"


def test_image_attributed_to_preceding_heading():
    """插图归属它之前最近的 ## 标题（章节末插图模式）。"""
    md = (
        "## 一、章\n\n段落1\n\n段落2\n\n![图](imgs/01.png)\n\n## 二、章\n\n内容\n"
    )
    segs = build_segments(md)

    assert segs[0]["illustration"] == "imgs/01.png"
    assert segs[0]["illustration_line"] == 7
    assert segs[0]["content_end_line"] == 8
    assert segs[1]["illustration"] is None  # 二、章无图


def test_more_images_than_headings_collected_to_list():
    """一节多图：illustration=首张（兼容），illustrations=全部两张。"""
    md = "## 一、章\n\n![图1](imgs/01.png)\n\n![图2](imgs/02.png)\n\n"
    segs = build_segments(md)

    assert len(segs) == 1
    assert segs[0]["illustration"] == "imgs/01.png"  # 单值=首张（向后兼容）
    assert segs[0]["illustrations"] == ["imgs/01.png", "imgs/02.png"]  # 数组=全部


def test_single_image_per_segment_illustrations_singleton_list():
    """一节一图：illustrations 是单元素列表，illustration 与之一致。"""
    md = "## 一、章\n\n![图](imgs/01.png)\n\n## 二、章\n\n![图](imgs/02.png)\n"
    segs = build_segments(md)

    assert segs[0]["illustrations"] == ["imgs/01.png"]
    assert segs[0]["illustration"] == "imgs/01.png"
    assert segs[1]["illustrations"] == ["imgs/02.png"]


def test_no_images_illustrations_empty_list():
    """无图段：illustrations 是空列表，illustration=None。"""
    md = "## 一、章\n\n内容\n\n## 二、章\n\n![图](imgs/02.png)\n"
    segs = build_segments(md)

    assert segs[0]["illustrations"] == []
    assert segs[0]["illustration"] is None
    assert segs[1]["illustrations"] == ["imgs/02.png"]


def test_more_headings_than_images_null_illustration():
    """标题比图多：无图章节 illustration=null。"""
    md = (
        "## 一、章\n\n有图\n\n![图](imgs/01.png)\n\n"
        "## 二、章\n\n无图\n\n## 三、章\n\n也无图\n"
    )
    segs = build_segments(md)

    assert len(segs) == 3
    assert segs[0]["illustration"] == "imgs/01.png"
    assert segs[1]["illustration"] is None
    assert segs[2]["illustration"] is None


def test_no_h2_headings_returns_empty():
    """无 ## 标题 → 返回空列表。"""
    md = "# 大标题\n\n连续正文无章节。\n\n![图](imgs/01.png)\n"
    segs = build_segments(md)

    assert segs == []


def test_no_images_all_null_illustration():
    """有标题无图 → 所有 segment illustration=null。"""
    md = "## 一、章\n\n内容\n\n## 二、章\n\n内容\n"
    segs = build_segments(md)

    assert len(segs) == 2
    assert all(s["illustration"] is None for s in segs)


def test_h1_heading_not_treated_as_section():
    """# 一级标题不触发 segment（只有 ## 算章节）。"""
    md = "# 大标题\n\n## 一、章\n\n![图](imgs/01.png)\n"
    segs = build_segments(md)

    assert len(segs) == 1
    assert segs[0]["heading"] == "一、章"


def test_content_end_line_is_last_line_for_final_section():
    """最后一个 body segment 的 content_end_line = 文章末尾行。"""
    md = "## 一、章\n\n内容A\n\n![图](imgs/01.png)\n"
    segs = build_segments(md)

    assert segs[0]["content_end_line"] == 5


def test_index_is_sequential_zero_based_for_body():
    """body segment.index 从 0 连续递增（整数）。"""
    md = "## 一\n\nx\n\n## 二\n\nx\n\n## 三\n\nx\n"
    segs = build_segments(md)

    assert [s["index"] for s in segs] == [0, 1, 2]


def test_backward_compat_no_illustration_meta_key_when_not_requested():
    """向后兼容：未传 illustration_meta_map 时，segment 不含 illustration_meta 键。"""
    md = "## 一、章\n\n![图](imgs/01.png)\n"
    segs = build_segments(md)

    assert "illustration_meta" not in segs[0]


# ── opening/ending 段（新增）──────────────────────────────────────────────

def test_opening_ending_segments_added_when_images_provided():
    """有片头片尾图 → segments 首尾各多一段，role=opening/ending。"""
    md = "## 一、章\n\n内容\n\n![图](imgs/01.png)\n"
    segs = build_segments(md, opening_image="imgs/00-opening.png", ending_image="imgs/99-ending.png")

    assert len(segs) == 3
    # 首段 opening
    assert segs[0]["role"] == "opening"
    assert segs[0]["index"] == "OPENING"
    assert segs[0]["illustration"] == "imgs/00-opening.png"
    assert segs[0]["heading"] is None
    assert segs[0]["heading_line"] is None
    # 中间 body
    assert segs[1]["role"] == "body"
    assert segs[1]["index"] == 0
    # 末段 ending
    assert segs[2]["role"] == "ending"
    assert segs[2]["index"] == "ENDING"
    assert segs[2]["illustration"] == "imgs/99-ending.png"
    assert segs[2]["heading"] is None


def test_only_opening_image_adds_opening_segment():
    """只有片头图 → 只加 opening 段，无 ending。"""
    md = "## 一、章\n\n内容\n"
    segs = build_segments(md, opening_image="imgs/00-opening.png")

    assert len(segs) == 2
    assert segs[0]["role"] == "opening"
    assert segs[-1]["role"] == "body"


def test_only_ending_image_adds_ending_segment():
    """只有片尾图 → 只加 ending 段，无 opening。"""
    md = "## 一、章\n\n内容\n"
    segs = build_segments(md, ending_image="imgs/99-ending.png")

    assert len(segs) == 2
    assert segs[-1]["role"] == "ending"
    assert segs[0]["role"] == "body"


def test_no_special_images_pure_body_backward_compat():
    """无片头片尾图 → 与现有逻辑一致（纯 body），向后兼容。"""
    md = "## 一、章\n\n![图](imgs/01.png)\n\n## 二、章\n\n![图](imgs/02.png)\n"
    segs = build_segments(md)  # 不传 opening/ending

    assert len(segs) == 2
    assert all(s["role"] == "body" for s in segs)


def test_detect_special_images_by_filename(tmp_path):
    """detect_special_images 从文件名识别片头片尾图。"""
    (tmp_path / "00-opening-theme.png").write_bytes(b"x")
    (tmp_path / "01-infographic.png").write_bytes(b"x")
    (tmp_path / "07-ending-cta.png").write_bytes(b"x")

    opening, ending = detect_special_images(tmp_path)

    assert opening == "imgs/00-opening-theme.png"
    assert ending == "imgs/07-ending-cta.png"


def test_detect_special_images_none_when_no_match(tmp_path):
    """无 opening/ending 文件名 → 返回 (None, None)。"""
    (tmp_path / "01-infographic.png").write_bytes(b"x")
    (tmp_path / "02-scene.png").write_bytes(b"x")

    opening, ending = detect_special_images(tmp_path)

    assert opening is None
    assert ending is None


# ── 路径 A：--from-outline（文章未插图，从 outline 读映射）─────────────────

def test_outline_parse_extracts_segment_to_filename():
    """parse_outline_illustrations 从 outline.md 提取 Segment→Filename 映射（返回列表）。"""
    outline = (
        "# 插图大纲\n\n"
        "## Illustration 1\n"
        "**Segment**: 0\n"
        "**Filename**: 01-infographic-concept.png\n\n"
        "## Illustration 2\n"
        "**Segment**: 1\n"
        "**Filename**: 02-flowchart-steps.png\n\n"
        "## Illustration 3\n"
        "**Segment**: OPENING\n"
        "**Filename**: 00-opening-theme.png\n\n"
        "## Illustration 4\n"
        "**Segment**: ENDING\n"
        "**Filename**: 07-ending-cta.png\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(outline)
        outline_path = Path(f.name)
    try:
        result = parse_outline_illustrations(outline_path)
    finally:
        outline_path.unlink()

    # 每个 segment 的 value 是列表（单图为单元素列表）
    assert result[0] == ["imgs/01-infographic-concept.png"]
    assert result[1] == ["imgs/02-flowchart-steps.png"]
    assert result["OPENING"] == ["imgs/00-opening-theme.png"]
    assert result["ENDING"] == ["imgs/07-ending-cta.png"]


def test_outline_parse_multiple_images_same_segment():
    """一段多图：两个 Illustration 块共享同一 Segment → 列表含两个 filename。"""
    outline = (
        "## Illustration 1\n"
        "**Segment**: 0\n"
        "**Filename**: 01-infographic-concept.png\n\n"
        "## Illustration 2\n"
        "**Segment**: 0\n"
        "**Filename**: 02-flowchart-steps.png\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(outline)
        outline_path = Path(f.name)
    try:
        result = parse_outline_illustrations(outline_path)
    finally:
        outline_path.unlink()

    assert result[0] == ["imgs/01-infographic-concept.png", "imgs/02-flowchart-steps.png"]


def test_path_a_uses_illustration_map_without_scanning_article():
    """路径 A：illustration_map 非空时，不扫描文章 ![]()，从映射填 illustration。"""
    md = "## 一、章\n\n内容（无图片引用）。\n\n## 二、章\n\n也无图。\n"
    illu_map = {0: "imgs/01-foo.png", 1: "imgs/02-bar.png"}
    segs = build_segments(md, illustration_map=illu_map)

    assert len(segs) == 2
    assert segs[0]["illustration"] == "imgs/01-foo.png"
    assert segs[0]["illustration_line"] is None  # 路径 A：图未插入，line=None
    assert segs[1]["illustration"] == "imgs/02-bar.png"
    assert segs[1]["illustration_line"] is None


def test_path_a_missing_segment_in_map_gets_none():
    """路径 A：outline 未给某段配图 → 该段 illustration=None。"""
    md = "## 一\n\nx\n\n## 二\n\nx\n\n## 三\n\nx\n"
    illu_map = {0: "imgs/01.png", 2: "imgs/03.png"}  # 段1无图
    segs = build_segments(md, illustration_map=illu_map)

    assert segs[0]["illustration"] == "imgs/01.png"
    assert segs[1]["illustration"] is None
    assert segs[2]["illustration"] == "imgs/03.png"


# ── illustration_meta 提取（从 prompt 文件 frontmatter）──────────────────

def test_extract_meta_full_frontmatter():
    """prompt 文件含完整 frontmatter（type+title_text+labels）→ 提取成功。"""
    import tempfile
    content = (
        "---\n"
        "illustration_id: 01\n"
        "type: infographic\n"
        "style: sketch-notes\n"
        "palette: macaron\n"
        'title_text: "三个被低估的副业"\n'
        'labels: ["写作变现", "视频剪辑", "AI 配音"]\n'
        "---\n\n[正文]"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        p = Path(f.name)
    try:
        meta = extract_illustration_meta(p)
    finally:
        p.unlink()

    assert meta["type"] == "infographic"
    assert meta["title_text"] == "三个被低估的副业"
    assert meta["labels"] == ["写作变现", "视频剪辑", "AI 配音"]


def test_extract_meta_scene_type_no_labels():
    """scene 类型 prompt（无 title_text/labels）→ meta 的对应字段为 None。"""
    import tempfile
    content = (
        "---\n"
        "type: scene\n"
        "style: watercolor\n"
        "---\n\n[氛围描述]"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        p = Path(f.name)
    try:
        meta = extract_illustration_meta(p)
    finally:
        p.unlink()

    assert meta["type"] == "scene"
    assert meta["title_text"] is None
    assert meta["labels"] is None


def test_extract_meta_no_frontmatter_returns_none():
    """无 frontmatter 的文件 → None。"""
    import tempfile
    content = "这是一段没有 frontmatter 的正文。"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        p = Path(f.name)
    try:
        meta = extract_illustration_meta(p)
    finally:
        p.unlink()

    assert meta is None


def test_build_meta_map_scans_prompts_dir(tmp_path):
    """build_meta_map 扫描 prompts/ 目录，构建 {stem: meta}。"""
    (tmp_path / "01-infographic-foo.md").write_text(
        "---\ntype: infographic\ntitle_text: \"标题A\"\nlabels: [\"标签1\", \"标签2\"]\n---\n", encoding="utf-8"
    )
    (tmp_path / "02-scene-bar.md").write_text(
        "---\ntype: scene\n---\n", encoding="utf-8"
    )
    (tmp_path / "not-a-prompt.txt").write_text("ignore me", encoding="utf-8")

    meta_map = build_meta_map(tmp_path)

    assert "01-infographic-foo" in meta_map
    assert meta_map["01-infographic-foo"]["type"] == "infographic"
    assert meta_map["01-infographic-foo"]["labels"] == ["标签1", "标签2"]
    assert "02-scene-bar" in meta_map
    assert meta_map["02-scene-bar"]["type"] == "scene"
    assert "not-a-prompt" not in meta_map


# ── illustration_meta 注入到 segments（集成）──────────────────────────────

def test_meta_injected_when_meta_map_provided():
    """传 illustration_meta_map → segment 含 illustration_meta 键。"""
    md = "## 一、章\n\n![图](imgs/01-infographic-foo.png)\n"
    meta_map = {
        "01-infographic-foo": {"type": "infographic", "title_text": "标题", "labels": ["a", "b"]},
    }
    segs = build_segments(md, illustration_meta_map=meta_map)

    assert segs[0]["illustration_meta"]["type"] == "infographic"
    assert segs[0]["illustration_meta"]["title_text"] == "标题"
    assert segs[0]["illustration_meta"]["labels"] == ["a", "b"]


def test_meta_null_for_segment_without_image():
    """有图无图的混合段：无图的段 illustration_meta=None（meta_map 传了时）。"""
    md = "## 一\n\n![图](imgs/01-foo.png)\n\n## 二\n\n无图\n"
    meta_map = {"01-foo": {"type": "infographic", "title_text": None, "labels": None}}
    segs = build_segments(md, illustration_meta_map=meta_map)

    assert segs[0]["illustration_meta"]["type"] == "infographic"
    assert segs[1]["illustration_meta"] is None  # 无图


def test_meta_null_when_prompt_not_found():
    """段有图但 meta_map 里无对应 stem → illustration_meta=None。"""
    md = "## 一\n\n![图](imgs/99-orphan.png)\n"
    meta_map = {"01-foo": {"type": "infographic"}}
    segs = build_segments(md, illustration_meta_map=meta_map)

    assert segs[0]["illustration_meta"] is None


def test_meta_injected_for_opening_ending():
    """opening/ending 段也从 meta_map 查 illustration_meta。"""
    md = "## 一\n\n![图](imgs/01-foo.png)\n"
    meta_map = {
        "00-opening": {"type": "scene", "title_text": None, "labels": None},
        "01-foo": {"type": "infographic", "title_text": "正文", "labels": ["x"]},
        "07-ending": {"type": "scene", "title_text": None, "labels": None},
    }
    segs = build_segments(
        md,
        opening_image="imgs/00-opening.png",
        ending_image="imgs/07-ending.png",
        illustration_meta_map=meta_map,
    )

    assert segs[0]["role"] == "opening"
    assert segs[0]["illustration_meta"]["type"] == "scene"
    assert segs[1]["role"] == "body"
    assert segs[1]["illustration_meta"]["type"] == "infographic"
    assert segs[2]["role"] == "ending"
    assert segs[2]["illustration_meta"]["type"] == "scene"


# ── 一段多图：illustration_meta 合并 ──────────────────────────────────────

def test_meta_merged_multiple_images_labels_union():
    """一段两图：labels 取并集，type/title_text 取首张。"""
    md = "## 一、章\n\n![图1](imgs/01-foo.png)\n\n![图2](imgs/02-bar.png)\n"
    meta_map = {
        "01-foo": {"type": "infographic", "title_text": "概念A", "labels": ["标签1", "标签2"]},
        "02-bar": {"type": "infographic", "title_text": "概念B", "labels": ["标签2", "标签3"]},
    }
    segs = build_segments(md, illustration_meta_map=meta_map)

    meta = segs[0]["illustration_meta"]
    assert meta["type"] == "infographic"  # 同类型，不标 mixed
    assert meta["title_text"] == "概念A"   # 取首张
    # labels 并集，去重保序
    assert meta["labels"] == ["标签1", "标签2", "标签3"]


def test_meta_merged_different_types_marked_mixed():
    """一段两图 type 不同 → illustration_meta.type = "mixed"。"""
    md = "## 一、章\n\n![图1](imgs/01-foo.png)\n\n![图2](imgs/02-bar.png)\n"
    meta_map = {
        "01-foo": {"type": "infographic", "title_text": "A", "labels": ["x"]},
        "02-bar": {"type": "flowchart", "title_text": "B", "labels": ["y"]},
    }
    segs = build_segments(md, illustration_meta_map=meta_map)

    assert segs[0]["illustration_meta"]["type"] == "mixed"
    assert segs[0]["illustration_meta"]["labels"] == ["x", "y"]


def test_meta_merged_one_image_missing_meta():
    """一段两图但只一张有 prompt meta → 合并时只取有 meta 的那张。"""
    md = "## 一、章\n\n![图1](imgs/01-foo.png)\n\n![图2](imgs/02-bar.png)\n"
    meta_map = {
        "01-foo": {"type": "infographic", "title_text": "A", "labels": ["x"]},
        # 02-bar 无 meta
    }
    segs = build_segments(md, illustration_meta_map=meta_map)

    meta = segs[0]["illustration_meta"]
    assert meta is not None
    assert meta["type"] == "infographic"
    assert meta["labels"] == ["x"]


# ── 路径 A + meta 集成（分段驱动完整场景）─────────────────────────────────

def test_path_a_with_meta_full_scenario(tmp_path):
    """路径 A（illustration_map）+ illustration_meta_map 完整集成。"""
    md = "## 一、概念\n\n内容。\n\n## 二、对比\n\n内容。\n"
    illu_map = {0: "imgs/01-infographic-concept.png", 1: "imgs/02-comparison-vs.png"}
    meta_map = {
        "01-infographic-concept": {"type": "infographic", "title_text": "核心概念", "labels": ["要素A", "要素B"]},
        "02-comparison-vs": {"type": "comparison", "title_text": "前后对比", "labels": ["旧", "新"]},
    }
    segs = build_segments(md, illustration_map=illu_map, illustration_meta_map=meta_map)

    assert len(segs) == 2
    # 段0
    assert segs[0]["illustration"] == "imgs/01-infographic-concept.png"
    assert segs[0]["illustration_line"] is None  # 路径 A
    assert segs[0]["illustration_meta"]["type"] == "infographic"
    assert segs[0]["illustration_meta"]["labels"] == ["要素A", "要素B"]
    # 段1
    assert segs[1]["illustration"] == "imgs/02-comparison-vs.png"
    assert segs[1]["illustration_meta"]["type"] == "comparison"
    assert segs[1]["illustration_meta"]["labels"] == ["旧", "新"]

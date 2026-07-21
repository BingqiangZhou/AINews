"""
build_segments.py — 扫描文章，产出 imgs/segments.json（章节→插图映射 + 片头片尾 + illustration_meta）。

支持两种构建路径：
  路径 A（分段驱动，--from-outline）：文章尚未插入图片引用时，从 outline.md 读
    segment→filename 映射。用于 prompt_only 模式或 ai-news-digest 的 Phase 7b-prepare
    （让 conductor 在生图前就能拿到分段定义）。
  路径 B（扫描模式，默认）：文章已插入 ![](imgs/...) 引用时，扫描引用归属章节。
    用于全量模式末尾（Step 7）。

两种路径都可选地通过 --prompts-dir 从 prompt 文件的 frontmatter 提取 illustration_meta
（type/title_text/labels），填入每个 segment。illustration_meta 是新增可选字段——下游
（conductor）据此时图内容对齐播客要点，labels 覆盖校验也依赖它。无 prompt 文件或未传
--prompts-dir 时，segment 不含 illustration_meta 键，向下兼容旧下游。

这是「按插图分段」的**唯一权威来源**——下游播客（conductor 分组要点）和视频
（plan_scenes 配图）都读它，不再各自重新分析文章结构。分段只在这里做一次。

Usage:
  # 路径 B：文章已插图（当前默认模式）
  python build_segments.py --article 公众号_文章.md --output imgs/segments.json
  # 补充 illustration_meta
  python build_segments.py --article ... --output ... --prompts-dir imgs/prompts

  # 路径 A：文章未插图（分段驱动 / prompt_only）
  python build_segments.py --article ... --output ... \
      --from-outline imgs/outline.md --prompts-dir imgs/prompts

  # 显式指定片头片尾图
  python build_segments.py --article ... --output ... --opening imgs/00-opening.png --ending imgs/07-ending.png
  # 自动从 imgs/ 扫描文件名含 opening/ending 的图
  python build_segments.py --article ... --output ... --imgs-dir imgs
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ## 章节标题（只匹配二级，不匹配一级文章大标题）
HEADING_RE = re.compile(r"^##\s+(.+)$")
# ![](imgs/xxx.png) 插图引用
IMG_RE = re.compile(r"!\[[^\]]*\]\((imgs/[^)]+)\)")

# Type 字段的合法枚举（三维法方法论的 Type 11 值）。
# 用于 extract_illustration_meta 的 warning 校验——历史 prompt 文件可能含旧值（中文/缩写），
# warning 提示但不阻塞 segments.json 产出。下游 conductor 只用 labels 不用 type 值，
# 所以即使 type 非法也不会影响下游；此 warning 仅用于发现需要迁移的旧 prompt 文件。
VALID_TYPES = frozenset({
    # 视觉构图类（cover 场景为主）
    "hero", "conceptual", "typography", "metaphor", "minimal",
    # 信息结构类（illustrate 场景为主）
    "infographic", "flowchart", "comparison", "framework", "timeline",
    # 场景类
    "scene",
})
# 片头片尾图文件名匹配（opening/ending 关键词）
OPENING_RE = re.compile(r"(?:^|[-_])opening(?:[-_]|$)", re.IGNORECASE)
ENDING_RE = re.compile(r"(?:^|[-_])ending(?:[-_]|$)", re.IGNORECASE)
# outline.md 的 Illustration 块分隔（## Illustration N）
OUTLINE_BLOCK_RE = re.compile(r"^##\s+Illustration\s+\d+", re.MULTILINE)


def build_segments(
    article_text: str,
    opening_image: str | None = None,
    ending_image: str | None = None,
    illustration_map: dict[int, str] | None = None,
    illustration_meta_map: dict[str, dict] | None = None,
) -> list[dict]:
    """扫描文章，构建分段（body 章节 + 可选 opening/ending + 可选 illustration_meta）。

    逻辑：
      1. 找所有 ## 标题（行号 + 标题文本）→ body 段
      2. 配图来源：
         - illustration_map 非空（路径 A）→ 从映射取（illustration_line=None，图未插入）
         - illustration_map 为空（路径 B）→ 扫描 ![](imgs/...) 归属前一个标题
      3. 若有 opening_image → 首位插 opening 段
      4. 若有 ending_image → 末尾插 ending 段
      5. 若 illustration_meta_map 非空 → 每个 segment 补 illustration_meta 键

    Args:
        article_text: 文章 Markdown（路径 B 需已插图；路径 A 不要求）
        opening_image: 片头图路径（如 "imgs/00-opening.png"），无则不加 opening 段
        ending_image: 片尾图路径，无则不加 ending 段
        illustration_map: 路径 A 用——{segment_index: [filename, ...]}，从 outline 读。
            文章未插图时用此映射填 illustration/illustrations（illustration_line=None）。
            支持一段多图（列表多元素）；单图为单元素列表。
        illustration_meta_map: {prompt_stem: {type, title_text, labels}}，从 prompts/
            提取。给每个有图的 segment 补 illustration_meta。None 时 segment 不含该键（向下兼容）

    Returns:
        [{index, role, heading, heading_line, content_end_line, illustration,
          illustration_line, illustrations, [illustration_meta]}, ...]
        body 段 index 是 0-based 整数；opening/ending 段 index 是 "OPENING"/"ENDING" 字符串。
        illustration = illustrations[0]（单值，向后兼容）；illustrations = 该段全部图路径数组。
        无 ## 标题且无片头片尾 → 返回 []。
        illustration_meta 仅当 illustration_meta_map 非空时出现（有图但无 prompt → null）。
        一段多图时 illustration_meta.labels 是所有图 labels 的并集。
    """
    body_segments = _build_body_segments(article_text, illustration_map)

    segments: list[dict] = []
    if opening_image:
        segments.append(_make_special_segment("OPENING", "opening", opening_image))
    segments.extend(body_segments)
    if ending_image:
        segments.append(_make_special_segment("ENDING", "ending", ending_image))

    if illustration_meta_map is not None:
        for seg in segments:
            seg["illustration_meta"] = _lookup_meta(seg, illustration_meta_map)
    return segments


def _build_body_segments(
    article_text: str,
    illustration_map: dict[int, str] | None = None,
) -> list[dict]:
    """从 ## 标题构建 body 段。

    配图来源：
      illustration_map 非空（路径 A）→ 从映射取（illustration_line=None，图未插入文章）
      illustration_map 为空（路径 B）→ 扫描 ![](imgs/...) 引用归属前一个标题
    """
    lines = article_text.splitlines()

    headings = []  # [(line_no, heading_text)]  line_no 1-based
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            headings.append((i + 1, m.group(1).strip()))

    if not headings:
        return []

    # 路径 B：扫描文章中的插图引用
    images: list[tuple[int, str]] = []
    if illustration_map is None:
        for i, line in enumerate(lines):
            m = IMG_RE.search(line)
            if m:
                images.append((i + 1, m.group(1)))

    segments = []
    for h_idx, (h_line, h_text) in enumerate(headings):
        if h_idx + 1 < len(headings):
            content_end = headings[h_idx + 1][0] - 1
        else:
            content_end = len(lines)

        if illustration_map is not None:
            # 路径 A：从 outline 映射取（图未插入文章，line=None）
            # illustration_map[h_idx] 可能是单值（旧 outline）或列表（一段多图）
            mapped = illustration_map.get(h_idx)
            if isinstance(mapped, list):
                seg_images = mapped
            elif mapped is not None:
                seg_images = [mapped]
            else:
                seg_images = []
            seg_image_lines: list[int | None] = [None] * len(seg_images)
        else:
            # 路径 B：扫描归属——收集该 section 范围内的所有图（支持一段多图）
            seg_images = []
            seg_image_lines = []
            for img_line, img_path in images:
                if h_line < img_line <= content_end:
                    seg_images.append(img_path)
                    seg_image_lines.append(img_line)

        # illustration（单值，向后兼容）= 首张；illustrations = 全部
        seg_image = seg_images[0] if seg_images else None
        seg_image_line = seg_image_lines[0] if seg_image_lines else None

        seg: dict = {
            "index": h_idx,
            "role": "body",
            "heading": h_text,
            "heading_line": h_line,
            "content_end_line": content_end,
            "illustration": seg_image,
            "illustration_line": seg_image_line,
            "illustrations": seg_images,
        }
        segments.append(seg)

    return segments


def _make_special_segment(index: str, role: str, image: str) -> dict:
    """构建 opening/ending 段。"""
    return {
        "index": index,
        "role": role,
        "heading": None,
        "heading_line": None,
        "content_end_line": None,
        "illustration": image,
        "illustration_line": None,
        "illustrations": [image] if image else [],
    }


def _lookup_meta(segment: dict, meta_map: dict[str, dict]) -> dict | None:
    """合并该 segment 所有图的 meta。labels 取并集，type/title_text 取首张。

    支持一段多图：遍历 segment.illustrations（数组），每个 stem 查 meta_map，
    labels 取并集（去重保序），type/title_text 取首张有值的图。无图或无匹配 → None。
    """
    illustrations = segment.get("illustrations") or [segment.get("illustration")]
    illustrations = [i for i in illustrations if i]  # 过滤 None/空
    if not illustrations:
        return None

    merged_labels: list[str] = []
    seen_labels: set[str] = set()
    first_type = None
    first_title = None
    types_seen: set[str] = set()
    found_any = False

    for illu in illustrations:
        stem = Path(illu).stem
        meta = meta_map.get(stem)
        if meta is None:
            continue
        found_any = True
        if first_type is None and meta.get("type"):
            first_type = meta["type"]
        if meta.get("type"):
            types_seen.add(meta["type"])
        if first_title is None:
            first_title = meta.get("title_text")
        for label in meta.get("labels") or []:
            if label not in seen_labels:
                seen_labels.add(label)
                merged_labels.append(label)

    if not found_any:
        return None

    # 多张图 type 不一致时标注 mixed
    result_type = "mixed" if len(types_seen) > 1 else first_type
    return {
        "type": result_type,
        "title_text": first_title,
        "labels": merged_labels if merged_labels else None,
    }


# ── outline.md 解析（路径 A）──────────────────────────────────────────────

def parse_outline_illustrations(outline_path: Path) -> dict:
    """解析 outline.md，返回 {segment_key: filename列表} 映射。

    segment_key：body 段为 int（0-based），片头片尾为 "OPENING"/"ENDING"。
    value：filename 列表（同一 segment 多个 Illustration 块 = 一段多图），单元素列表为常见情况。
    filename：归一化为 "imgs/<filename>"（outline 的 Filename 字段通常无 imgs/ 前缀）。

    outline.md 每个 Illustration 块格式：
        ## Illustration 1
        **Segment**: 0
        **Filename**: 01-infographic-concept.png

    一段多图时，多个块共享同一 Segment 值：
        ## Illustration 1
        **Segment**: 0
        **Filename**: 01-infographic-concept.png
        ## Illustration 2
        **Segment**: 0
        **Filename**: 02-flowchart-steps.png
    → mapping[0] = ["imgs/01-...png", "imgs/02-...png"]
    """
    text = outline_path.read_text(encoding="utf-8")
    blocks = OUTLINE_BLOCK_RE.split(text)  # [preamble, block1, block2, ...]
    mapping: dict[int | str, list[str]] = {}
    for block in blocks[1:]:
        seg_m = re.search(r"\*\*Segment\*\*\s*:\s*(.+)", block)
        fn_m = re.search(r"\*\*Filename\*\*\s*:\s*(.+)", block)
        if not (seg_m and fn_m):
            continue
        seg_raw = seg_m.group(1).strip()
        filename = fn_m.group(1).strip()
        if not filename.startswith("imgs/"):
            filename = f"imgs/{filename}"
        if seg_raw in ("OPENING", "ENDING"):
            key: int | str = seg_raw
        else:
            try:
                key = int(seg_raw)
            except ValueError:
                continue
        mapping.setdefault(key, []).append(filename)
    return mapping


# ── illustration_meta 提取（从 prompt 文件 frontmatter）─────────────────

def extract_illustration_meta(prompt_file: Path) -> dict | None:
    """从 prompt 文件的 YAML frontmatter 提取 illustration_meta。

    提取字段：type / title_text / labels（scene 类型可无 title_text/labels）。
    用最小手写解析（不依赖 PyYAML），因为 frontmatter 是已知的扁平结构。

    Returns:
        {"type": str|None, "title_text": str|None, "labels": list[str]|None}；
        无 frontmatter 或文件不存在 → None

    Note:
        对 type 字段做枚举校验（warning，不阻塞）。合法值见 VALID_TYPES。
        历史项目的 prompt 文件可能含旧值（如中文/缩写），warning 提示但不影响 segments.json 产出。
    """
    if not prompt_file.is_file():
        return None
    text = prompt_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]

    type_val = None
    title_text = None
    labels = None
    for line in fm.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("type:"):
            type_val = _scalar(stripped, "type:")
        elif stripped.startswith("title_text:"):
            title_text = _scalar(stripped, "title_text:")
        elif stripped.startswith("labels:"):
            labels = _parse_inline_list(stripped[len("labels:"):])

    # type 枚举校验（warning，不阻塞）
    if type_val and type_val not in VALID_TYPES:
        print(
            f"⚠️  warning: type '{type_val}' in {prompt_file.name} "
            f"not in 11-value enum (hero/conceptual/typography/metaphor/scene/minimal/"
            f"infographic/flowchart/comparison/framework/timeline). "
            f"segments.json will still include it, but consider migrating the prompt file.",
            file=sys.stderr,
        )

    return {"type": type_val, "title_text": title_text, "labels": labels}


def _scalar(line: str, key: str) -> str | None:
    """提取 'key: value' 的 value，去掉引号和空白。空值返回 None。"""
    raw = line[len(key):].strip()
    if not raw:
        return None
    return raw.strip('"').strip("'")


def _parse_inline_list(raw: str) -> list[str] | None:
    """解析 YAML 内联列表 ["a", "b", "c"] 或 [a, b, c]。空或无 → None。"""
    raw = raw.strip()
    if not raw or raw == "[]":
        return None
    inner = raw.strip("[]")
    items = []
    for item in inner.split(","):
        item = item.strip().strip('"').strip("'").strip()
        if item:
            items.append(item)
    return items if items else None


def build_meta_map(prompts_dir: Path) -> dict[str, dict]:
    """扫描 prompts/ 目录，构建 {prompt_stem: meta} 映射。

    prompt_stem（如 "01-infographic-concept"）与对应 PNG 的 stem 一致，
    用于在 segment 的 illustration 路径上查找 meta。
    """
    meta_map: dict[str, dict] = {}
    if not prompts_dir.is_dir():
        return meta_map
    for f in sorted(prompts_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        meta = extract_illustration_meta(f)
        if meta is not None:
            meta_map[f.stem] = meta
    return meta_map


def detect_special_images(imgs_dir: Path) -> tuple[str | None, str | None]:
    """从 imgs/ 目录扫描片头片尾图（文件名含 opening/ending）。

    Returns:
        (opening_image, ending_image) 相对路径（如 "imgs/00-opening.png"），无则 None。
    """
    if not imgs_dir.is_dir():
        return None, None
    opening = None
    ending = None
    for f in sorted(imgs_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".png":
            continue
        rel = f"imgs/{f.name}"
        if opening is None and OPENING_RE.search(f.stem):
            opening = rel
        elif ending is None and ENDING_RE.search(f.stem):
            ending = rel
    return opening, ending


def main():
    ap = argparse.ArgumentParser(
        description="产出 imgs/segments.json（章节→插图 + 片头片尾 + illustration_meta）"
    )
    ap.add_argument("--article", required=True, help="公众号_文章.md（路径 B 需已插图）")
    ap.add_argument("--output", help="输出 segments.json 路径（omit with --stdout）")
    ap.add_argument("--stdout", action="store_true", help="打印到 stdout")
    ap.add_argument("--opening", help="片头图路径（如 imgs/00-opening.png）")
    ap.add_argument("--ending", help="片尾图路径")
    ap.add_argument("--imgs-dir", help="自动扫描片头片尾图的 imgs/ 目录（未指定 --opening/--ending 时用）")
    ap.add_argument(
        "--from-outline",
        help="路径 A：从 outline.md 读 segment→filename 映射（文章未插图时用）",
    )
    ap.add_argument(
        "--prompts-dir",
        help="prompt 文件目录，提取 illustration_meta（type/title_text/labels）",
    )
    args = ap.parse_args()

    article_path = Path(args.article)
    article_text = article_path.read_text(encoding="utf-8")

    # 路径 A：从 outline 读 segment→filename 映射（含 opening/ending）
    illustration_map: dict[int, list[str]] | None = None
    outline_opening: str | None = None
    outline_ending: str | None = None
    if args.from_outline:
        outline_map = parse_outline_illustrations(Path(args.from_outline))
        # opening/ending 是列表（单元素），取首张
        opening_list = outline_map.pop("OPENING", None)
        outline_opening = opening_list[0] if opening_list else None
        ending_list = outline_map.pop("ENDING", None)
        outline_ending = ending_list[0] if ending_list else None
        illustration_map = outline_map  # 剩余为 {int: [filename, ...]}

    # 决定片头片尾图：显式参数 > outline > 自动扫描 imgs/
    opening_image = args.opening or outline_opening
    ending_image = args.ending or outline_ending
    if (opening_image is None or ending_image is None) and args.imgs_dir:
        auto_opening, auto_ending = detect_special_images(Path(args.imgs_dir))
        if opening_image is None:
            opening_image = auto_opening
        if ending_image is None:
            ending_image = auto_ending
    # 若文章目录下有 imgs/ 且未指定，也自动扫
    if opening_image is None or ending_image is None:
        auto_imgs = article_path.parent / "imgs"
        if auto_imgs.is_dir():
            auto_opening, auto_ending = detect_special_images(auto_imgs)
            if opening_image is None:
                opening_image = auto_opening
            if ending_image is None:
                ending_image = auto_ending

    # illustration_meta 从 prompts/ 提取
    illustration_meta_map: dict[str, dict] | None = None
    if args.prompts_dir:
        illustration_meta_map = build_meta_map(Path(args.prompts_dir))

    segments = build_segments(
        article_text,
        opening_image=opening_image,
        ending_image=ending_image,
        illustration_map=illustration_map,
        illustration_meta_map=illustration_meta_map,
    )

    result = {
        "article": article_path.name,
        "segment_count": len(segments),
        "segments": segments,
    }
    output_text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.stdout:
        sys.stdout.write(output_text)
    else:
        if not args.output:
            sys.exit("--output 或 --stdout required")
        Path(args.output).write_text(output_text, encoding="utf-8")

    body_count = sum(1 for s in segments if s["role"] == "body")
    has_opening = any(s["role"] == "opening" for s in segments)
    has_ending = any(s["role"] == "ending" for s in segments)
    meta_count = sum(1 for s in segments if s.get("illustration_meta"))
    sys.stderr.write(
        f"[build_segments] {len(segments)} segments "
        f"(body {body_count}"
        f"{'+opening' if has_opening else ''}"
        f"{'+ending' if has_ending else ''}"
        f"{f', {meta_count} with meta' if meta_count else ''}) → "
        f"{args.output if args.output else 'stdout'}\n"
    )


if __name__ == "__main__":
    main()

"""
check_illustration_coverage.py — 校验播客文本是否覆盖了每段插图的 labels。

这是「确保播客和插图内容对应」的显式校验机制。article-image-studio 的每张图（非 scene
类型）在 prompt frontmatter 记录了 title_text/labels（图内要画的具体中文字），这些通过
segments.json 的 illustration_meta 字段传递到下游。conductor 规划蓝图时被要求覆盖所有
labels，body-writer 写正文时也应呼应这些标签。

本脚本在 conductor 产出 blueprint.md 后（或 body-writer 产出 body.txt / draft_v1 后）跑，
机械检查每个有 illustration_meta.labels 的 body segment，其 labels 是否在对应的 Section
文本中出现。这是对 LLM「零杜撰」「图标签覆盖」约束的事后校验——不靠 LLM 自觉，靠代码兜底。

Usage:
  # 校验蓝图（conductor 之后）
  python check_illustration_coverage.py \
      --segments <文章目录>/imgs/segments.json \
      --script <文章目录>/_podcast/temp/blueprint.md

  # 校验正文（body-writer / draft_v1 之后）
  python check_illustration_coverage.py \
      --segments <文章目录>/imgs/segments.json \
      --script <文章目录>/_podcast/temp/draft_v1.txt

  # 严格模式：有缺失即报错（退出码 1）
  python check_illustration_coverage.py --segments ... --script ... --strict

退出码：
  0 = 全覆盖（或无 labels 可校验）
  1 = 有 labels 缺失（仅 --strict 时；默认 warning 仍返回 0）
  2 = 输入错误（文件不存在、格式错误）
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extract_sections(script_text: str) -> dict[int | str, str]:
    """从脚本文本提取每个 Section 的文本块。

    支持两种格式：
      - blueprint.md 的 `### Section N：<heading>` 块
      - 最终脚本的 `[SECTION:N]` 标记行后的段落（draft_v1 / body.txt / 播客_脚本.txt）

    Returns:
        {section_key: section_text}，section_key 为 int（body 段）或
        "OPENING"/"ENDING"（片头片尾）。未匹配到任何 section → 空 dict。
    """
    sections: dict[int | str, str] = {}

    # 模式 A：blueprint.md 的 ### Section N：<heading>
    blueprint_re = re.compile(r"^###\s+Section\s+(\w+)\s*：", re.MULTILINE)
    blueprint_splits = blueprint_re.split(script_text)
    # split 结果：[preamble, key1, body1, key2, body2, ...]
    for i in range(1, len(blueprint_splits) - 1, 2):
        key_raw = blueprint_splits[i].strip()
        body = blueprint_splits[i + 1]
        key = _parse_section_key(key_raw)
        if key is not None:
            sections[key] = body

    # 模式 B：[SECTION:N] 标记（draft_v1 / 播客_脚本.txt）
    # 标记独占一行，其后到下一个标记（或文件末）为该段文本
    marker_re = re.compile(r"^\s*\[SECTION:(\w+)\]\s*$", re.MULTILINE)
    marker_matches = list(marker_re.finditer(script_text))
    for i, m in enumerate(marker_matches):
        key_raw = m.group(1)
        start = m.end()
        end = marker_matches[i + 1].start() if i + 1 < len(marker_matches) else len(script_text)
        key = _parse_section_key(key_raw)
        if key is not None:
            # 标记模式的 section 文本：若该 key 已被 blueprint 模式捕获，合并；否则新增
            existing = sections.get(key, "")
            sections[key] = existing + "\n" + script_text[start:end]

    return sections


def _parse_section_key(raw: str) -> int | str | None:
    """解析 section key：整数或 OPENING/ENDING/DEEPDIVE。无法解析 → None。"""
    if raw in ("OPENING", "ENDING", "DEEPDIVE"):
        return raw
    try:
        return int(raw)
    except ValueError:
        return None


def check_coverage(
    segments: list[dict],
    script_text: str,
) -> dict:
    """校验每个有 illustration_meta.labels 的 body segment 的 labels 覆盖情况。

    Args:
        segments: segments.json 的 segments 数组
        script_text: 播客脚本文本（blueprint / body.txt / draft_v1 / 播客_脚本.txt）

    Returns:
        {
            "total_labels": int,          # 所有 body segment 的 labels 总数
            "covered_labels": int,        # 在脚本中出现的 labels 数
            "missing_labels": int,        # 缺失的 labels 数
            "coverage_rate": float,       # 0.0~1.0
            "details": [                  # 每个 body segment 的校验明细
                {
                    "index": int, "heading": str,
                    "labels": list[str], "missing": list[str],
                    "covered": list[str],
                }
            ],
            "skipped": [                  # 跳过的 segment（无 meta 或无 labels）
                {"index": int|"str", "role": str, "reason": str}
            ],
        }
    """
    section_texts = extract_sections(script_text)

    details = []
    skipped = []
    total_labels = 0
    missing_labels = 0

    for seg in segments:
        index = seg.get("index")
        role = seg.get("role", "body")

        # 只校验 body 段（opening/ending 是片头片尾，不在 Section 分组里）
        if role != "body":
            continue

        meta = seg.get("illustration_meta")
        if meta is None:
            skipped.append({"index": index, "role": role, "reason": "no illustration_meta"})
            continue
        labels = meta.get("labels")
        if not labels:
            skipped.append({"index": index, "role": role, "reason": "no labels (scene type or empty)"})
            continue

        # 获取该 section 的文本；若无 section 标记，用全文兜底（保守，可能漏报）
        section_text = section_texts.get(index, script_text)

        covered = []
        missing = []
        for label in labels:
            if label in section_text:
                covered.append(label)
            else:
                missing.append(label)

        total_labels += len(labels)
        missing_labels += len(missing)

        details.append({
            "index": index,
            "heading": seg.get("heading", ""),
            "labels": labels,
            "missing": missing,
            "covered": covered,
        })

    covered_labels = total_labels - missing_labels
    coverage_rate = covered_labels / total_labels if total_labels > 0 else 1.0

    return {
        "total_labels": total_labels,
        "covered_labels": covered_labels,
        "missing_labels": missing_labels,
        "coverage_rate": round(coverage_rate, 3),
        "details": details,
        "skipped": skipped,
    }


def format_report(result: dict) -> str:
    """格式化覆盖率报告为人读文本。"""
    lines = []
    rate = result["coverage_rate"]
    pct = f"{rate * 100:.0f}%"
    lines.append(f"插图标签覆盖率：{result['covered_labels']}/{result['total_labels']}（{pct}）")
    lines.append("")

    if result["missing_labels"] == 0:
        lines.append("✓ 全部覆盖——播客讲到了所有插图标签。")
    else:
        lines.append(f"✗ {result['missing_labels']} 个标签缺失（播客没讲到这些图上画的词）：")
        for d in result["details"]:
            if d["missing"]:
                lines.append(
                    f"  Section {d['index']}（{d['heading']}）：缺 {d['missing']}"
                )

    if result["skipped"]:
        lines.append("")
        lines.append(f"跳过 {len(result['skipped'])} 个 segment（无 meta 或 scene 类型）：")
        for s in result["skipped"][:5]:
            lines.append(f"  index={s['index']} role={s['role']} reason={s['reason']}")
        if len(result["skipped"]) > 5:
            lines.append(f"  ...（共 {len(result['skipped'])} 个）")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="校验播客文本是否覆盖每段插图的 labels（图标签覆盖校验）"
    )
    ap.add_argument("--segments", required=True, help="imgs/segments.json 路径")
    ap.add_argument("--script", required=True, help="播客脚本路径（blueprint/body.txt/draft_v1/播客_脚本.txt）")
    ap.add_argument("--strict", action="store_true", help="有缺失即报错（退出码 1）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式（默认人读文本）")
    args = ap.parse_args()

    segments_path = Path(args.segments)
    script_path = Path(args.script)

    if not segments_path.is_file():
        sys.stderr.write(f"[coverage] segments.json 不存在：{segments_path}\n")
        sys.exit(2)
    if not script_path.is_file():
        sys.stderr.write(f"[coverage] 脚本不存在：{script_path}\n")
        sys.exit(2)

    seg_data = json.loads(segments_path.read_text(encoding="utf-8"))
    segments = seg_data.get("segments", [])
    script_text = script_path.read_text(encoding="utf-8")

    result = check_coverage(segments, script_text)

    if args.json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_report(result) + "\n")

    # 退出码
    if result["missing_labels"] > 0 and args.strict:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

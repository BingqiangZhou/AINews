#!/usr/bin/env python3
"""Machine-checkable quality gates for article writing outputs (brand voice, structure, banned phrases).

This script intentionally validates only deterministic constraints. LLM quality
gates remain responsible for semantic judgment such as platform-native voice and
reader value.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# The authoritative banned-phrase list lives in references/brand-config.md
# ("## 禁用 AI 腔短语"). We parse it at import time so this validator never drifts
# from the doc — updating brand-config.md is the only change needed. Phrases whose
# doc entry carries a "（…段落开头…）" annotation are only flagged at paragraph start.
_BRAND_CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "brand-config.md"

# Emergency fallback only, used if brand-config.md is unreadable. Keep in sync
# with the doc; it is NOT a parallel source of truth.
_FALLBACK_BANNED_ALWAYS = [
    "值得一提", "不得不承认", "总的来说", "综上所述", "首先", "其次",
    "然而", "与此同时", "不仅如此", "显著提升", "深入探讨",
    "不可忽视", "众所周知", "毋庸置疑", "不言而喻",
]
_FALLBACK_BANNED_START = ["最后"]


def _load_banned_phrases(path: Path = _BRAND_CONFIG_PATH) -> tuple[list[str], list[str]]:
    """Parse brand-config.md into (always_banned, paragraph_start_only) lists.

    Each doc entry is a backtick-wrapped phrase, optionally followed by a （注解）.
    Annotations mentioning "段落开头" mark start-only phrases (e.g. 最后).
    """
    if not path.exists():
        return _FALLBACK_BANNED_ALWAYS, _FALLBACK_BANNED_START

    text = path.read_text(encoding="utf-8-sig")
    section = re.search(r"##\s*禁用 AI 腔短语(.*?)(?=\n##\s|\Z)", text, flags=re.DOTALL)
    if not section:
        return _FALLBACK_BANNED_ALWAYS, _FALLBACK_BANNED_START

    always: list[str] = []
    start_only: list[str] = []
    for phrase, note in re.findall(r"`([^`]+)`(（[^）]*）)?", section.group(1)):
        # Only accept CJK phrases; skip stray inline-code tokens in the section
        # prose (e.g. `agents/_shared.md` references the mirror doc).
        if not re.search(r"[一-鿿]", phrase):
            continue
        if note and "段落开头" in note:
            start_only.append(phrase)
        else:
            always.append(phrase)
    if not always and not start_only:
        return _FALLBACK_BANNED_ALWAYS, _FALLBACK_BANNED_START
    return always, start_only


_BANNED_ALWAYS, _BANNED_START = _load_banned_phrases()

VALID_PLATFORMS = {"gongzhonghao", "boker"}

# Default gongzhonghao thresholds (legacy orchestrator scenario). Other skills
# (article-studio, daily-digest) override the values they need via CLI
# args / thresholds dict — see validate_project().
DEFAULT_GZH_THRESHOLDS: dict[str, int] = {
    "title_min": 15,
    "title_max": 30,
    "summary_max": 120,
    "body_min": 900,
    "body_max": 2000,
    "min_sections": 2,
    "max_sections": 4,
    "min_illustrations": 2,
    "max_illustrations": 4,
}


@dataclass
class Failure:
    code: str
    message: str
    file: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        data = {"code": self.code, "message": self.message, "severity": self.severity}
        if self.file:
            data["file"] = self.file
        return data


@dataclass
class ValidationResult:
    passed: bool
    platforms: list[str]
    global_failures: list[Failure] = field(default_factory=list)
    failures_by_platform: dict[str, list[Failure]] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "platforms": self.platforms,
            "checked_at": self.checked_at,
            "global_failures": [failure.to_dict() for failure in self.global_failures],
            "failures_by_platform": {
                platform: [failure.to_dict() for failure in failures]
                for platform, failures in self.failures_by_platform.items()
            },
            "scores": self.scores,
        }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _visible_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _contains_banned_phrase(text: str) -> str | None:
    for phrase in _BANNED_ALWAYS:
        if phrase in text:
            return phrase
    for phrase in _BANNED_START:
        # brand-config 禁止这些短语"作为段落开头时"出现——只要位于段首即触发，
        # 不要求其后紧跟标点（"最后我们来看看…"同样是套路化收尾，应被拦截）。
        if re.search(rf"(^|\n)\s*{re.escape(phrase)}", text):
            return phrase
    return None


def _validate_state_schema(output_dir: Path) -> list[Failure]:
    """Validate critical state.json structure and required fields.

    兼容多个 skill 的 state schema：
      - `audio-to-social-v3` / `audio-to-social-v4`（编排器，v4 已迁移掉 requested_platforms）
      - `article-studio-v1`（article-studio 复用本脚本做 Phase 2a 预检）
    版本校验用白名单，requested_platforms 不再作必需键（v4/article-studio 没有该字段）。
    各 skill 的产物存在性由平台校验器（_validate_gongzhonghao/_validate_boker）直接查文件，
    本函数只做 state.json 结构健全性检查。
    """
    failures: list[Failure] = []
    state_path = output_dir / "state.json"

    if not state_path.exists():
        # state.json not yet created is not necessarily an error during early phases
        return failures

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        failures.append(Failure("STATE_SCHEMA", f"state.json is not valid JSON: {e}"))
        return failures

    if not isinstance(state, dict):
        failures.append(Failure("STATE_SCHEMA", "state.json root must be a JSON object"))
        return failures

    # Check required top-level fields (schema_version + output_dir 是所有 skill 共有的)
    required_keys = ["schema_version", "output_dir"]
    for key in required_keys:
        if key not in state:
            failures.append(Failure("STATE_SCHEMA", f"state.json missing required key: {key}"))

    # Check schema version against known-good allowlist
    allowed_versions = {"audio-to-social-v3", "audio-to-social-v4", "article-studio-v1"}
    version = state.get("schema_version", "")
    if version and version not in allowed_versions:
        failures.append(
            Failure("STATE_SCHEMA",
                    f"state.json schema_version is '{version}', expected one of {sorted(allowed_versions)}")
        )

    return failures


def _failure_if_missing(path: Path, code: str, message: str) -> list[Failure]:
    if not path.exists() or path.stat().st_size == 0:
        return [Failure(code, message, str(path))]
    return []


def _check_text_safety(text: str, path: Path) -> list[Failure]:
    failures: list[Failure] = []
    banned = _contains_banned_phrase(text)
    if banned:
        failures.append(Failure("platform.banned_phrase", f"包含禁用 AI 腔短语: {banned}", str(path)))
    return failures


def _validate_gongzhonghao(
    output_dir: Path,
    thresholds: dict | None = None,
    article_name: str = "公众号_文章.md",
    require_summary: bool = True,
) -> list[Failure]:
    th = {**DEFAULT_GZH_THRESHOLDS, **(thresholds or {})}

    article_path = output_dir / article_name
    summary_path = output_dir / "公众号_摘要.txt"
    failures = _failure_if_missing(article_path, "gongzhonghao.article_missing", f"{article_name} 缺失")
    if require_summary:
        failures += _failure_if_missing(summary_path, "gongzhonghao.summary_missing", "公众号_摘要.txt 缺失")
    if failures:
        return failures

    article = _read_text(article_path)
    failures += _check_text_safety(article, article_path)
    first_line = article.splitlines()[0].strip() if article.splitlines() else ""
    title = first_line[2:].strip() if first_line.startswith("# ") else ""
    if not title:
        failures.append(Failure("gongzhonghao.title_format", "第一行必须是 # 标题", str(article_path)))
    elif not th["title_min"] <= _visible_len(title) <= th["title_max"]:
        failures.append(Failure("gongzhonghao.title_length", f"标题必须为 {th['title_min']}-{th['title_max']} 字", str(article_path)))

    summary = _read_text(summary_path).strip() if summary_path.exists() else ""
    if summary:
        failures += _check_text_safety(summary, summary_path)
    if require_summary and _visible_len(summary) > th["summary_max"]:
        failures.append(Failure("gongzhonghao.summary_length", f"公众号摘要必须 <={th['summary_max']} 字符", str(summary_path)))

    body = "\n".join(article.splitlines()[1:])
    body_len = _visible_len(body)
    if not th["body_min"] <= body_len <= th["body_max"]:
        failures.append(Failure("gongzhonghao.body_length", f"公众号正文必须为 {th['body_min']}-{th['body_max']} 字", str(article_path)))
    section_count = len(re.findall(r"^##\s+", article, flags=re.MULTILINE))
    if section_count < th["min_sections"]:
        failures.append(Failure("gongzhonghao.sections", f"公众号文章至少包含 {th['min_sections']} 个 ## 小节标题", str(article_path)))

    # Check illustration placeholders / image references
    img_ref_re = re.compile(r"!\[[^\]]*\]\(imgs/[^)]+\)")
    marker_count = article.count("<!-- illustration -->")
    existing_img_refs = len(img_ref_re.findall(article))
    total_illust = marker_count + existing_img_refs
    if not th["min_illustrations"] <= total_illust <= th["max_illustrations"]:
        failures.append(
            Failure(
                "gongzhonghao.illustration_count",
                f"公众号文章必须包含 {th['min_illustrations']}-{th['max_illustrations']} 个 illustration 占位符或图片引用，当前 {total_illust} 个",
                str(article_path),
                severity="warning",
            )
        )

    return failures


def _validate_boker(output_dir: Path) -> list[Failure]:
    # 播客产物 canonical 在 _podcast/（article-to-solo-podcast 输出位），根目录作兼容回退
    script_path = output_dir / "_podcast" / "播客_脚本.txt"
    if not script_path.exists():
        script_path = output_dir / "播客_脚本.txt"
    meta_path = output_dir / "_podcast" / "播客_标题与描述.txt"
    if not meta_path.exists():
        meta_path = output_dir / "播客_标题与描述.txt"
    failures = _failure_if_missing(script_path, "boker.script_missing", "播客_脚本.txt 缺失")
    failures += _failure_if_missing(meta_path, "boker.meta_missing", "播客_标题与描述.txt 缺失")
    if failures:
        return failures

    script = _read_text(script_path)
    meta = _read_text(meta_path)
    failures += _check_text_safety(script, script_path)
    failures += _check_text_safety(meta, meta_path)
    if re.search(r"#|\*\*|>", script):
        failures.append(Failure("boker.markdown", "播客脚本必须是纯文本", str(script_path)))
    script_len = _visible_len(script)
    if not 1550 <= script_len <= 2500:
        failures.append(Failure("boker.script_length", "播客脚本必须为 1550-2500 字", str(script_path)))
    long_paragraphs = [p for p in re.split(r"\n\s*\n", script) if _visible_len(p) > 80]
    if long_paragraphs:
        failures.append(Failure("boker.paragraph_length", "播客每段必须 <=80 字", str(script_path)))
    if "标题：" not in meta or "简介：" not in meta or "标签：" not in meta:
        failures.append(Failure("boker.meta_format", "播客标题与描述必须包含 标题/简介/标签", str(meta_path)))
    else:
        # Validate title length
        title_match = re.search(r"标题[：:]\s*(.+)", meta)
        if title_match:
            title_text = title_match.group(1).strip()
            title_visible_len = _visible_len(title_text)
            if title_visible_len > 35:
                failures.append(
                    Failure("boker.title_length", f"播客标题必须 <=35 字，当前 {title_visible_len} 字", str(meta_path))
                )
            if title_visible_len < 5:
                failures.append(Failure("boker.title_length", "播客标题过短（<5字）", str(meta_path)))
            # Validate episode number prefix: must be 4-digit zero-padded + Chinese colon (e.g. "0224：")
            if not re.match(r"^\d{4}：", title_text):
                failures.append(
                    Failure("boker.title_episode_format",
                            "播客标题必须以四位零填充集号+中文冒号开头（如 0224：）", str(meta_path))
                )
        # Validate tag count
        tags_match = re.search(r"标签[：:]\s*(.+)", meta)
        if tags_match:
            tags = tags_match.group(1).strip().split()
            if not 5 <= len(tags) <= 8:
                failures.append(
                    Failure("boker.tag_count", f"播客标签必须 5-8 个，当前 {len(tags)} 个", str(meta_path))
                )
    return failures


PLATFORM_VALIDATORS = {
    "gongzhonghao": _validate_gongzhonghao,
    "boker": _validate_boker,
}


def _score_platform(failures: list[Failure]) -> int:
    return max(0, 100 - 12 * len([failure for failure in failures if failure.severity == "error"]))


def validate_project(
    output_dir: str | Path,
    platforms: list[str],
    thresholds: dict | None = None,
    article_name: str = "公众号_文章.md",
    require_summary: bool = True,
) -> ValidationResult:
    output_path = Path(output_dir)
    unknown = [platform for platform in platforms if platform not in VALID_PLATFORMS]
    if unknown:
        raise ValueError(f"unknown platform(s): {', '.join(unknown)}")

    global_failures: list[Failure] = []

    # Validate state.json structure
    state_failures = _validate_state_schema(output_path)
    global_failures.extend(state_failures)

    failures_by_platform: dict[str, list[Failure]] = {}
    scores: dict[str, int] = {}

    for platform in platforms:
        if platform == "gongzhonghao":
            failures = _validate_gongzhonghao(
                output_path,
                thresholds=thresholds,
                article_name=article_name,
                require_summary=require_summary,
            )
        else:
            failures = PLATFORM_VALIDATORS[platform](output_path)
        failures_by_platform[platform] = failures
        scores[platform] = _score_platform(failures)

    passed = not global_failures and all(not failures for failures in failures_by_platform.values())
    return ValidationResult(
        passed=passed,
        platforms=platforms,
        global_failures=global_failures,
        failures_by_platform=failures_by_platform,
        scores=scores,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate article machine-checkable quality gates.")
    parser.add_argument("--output-dir", required=True, help="article output directory")
    parser.add_argument("--platform", action="append", dest="platforms", required=True, help="Platform to validate")
    parser.add_argument("--report", help="Optional JSON report path")
    # Threshold overrides (default None → use DEFAULT_GZH_THRESHOLDS). Allow other
    # skills (article-studio, daily-digest) to adapt the gongzhonghao gate
    # to their own config without forking the script.
    parser.add_argument("--title-min", type=int, default=None)
    parser.add_argument("--title-max", type=int, default=None)
    parser.add_argument("--body-min", type=int, default=None)
    parser.add_argument("--body-max", type=int, default=None)
    parser.add_argument("--summary-max", type=int, default=None)
    parser.add_argument("--min-sections", type=int, default=None)
    parser.add_argument("--max-sections", type=int, default=None)
    parser.add_argument("--min-illustrations", type=int, default=None)
    parser.add_argument("--max-illustrations", type=int, default=None)
    parser.add_argument("--article-name", default="公众号_文章.md",
                        help="Article filename under output-dir (default: 公众号_文章.md). "
                             "Pass a custom filename to skip the copy workaround.")
    parser.add_argument("--no-summary-required", dest="require_summary", action="store_false", default=True,
                        help="Do not fail when 公众号_摘要.txt is missing (e.g. when running quality checks before the summary exists).")
    args = parser.parse_args()

    # Assemble thresholds dict from non-None CLI overrides
    thresholds: dict[str, int] = {}
    for key in DEFAULT_GZH_THRESHOLDS:
        cli_key = key.replace("_", "-")  # argparse normalizes dashes to underscores
        val = getattr(args, key, None)
        if val is not None:
            thresholds[key] = val

    result = validate_project(
        args.output_dir,
        args.platforms,
        thresholds=thresholds or None,
        article_name=args.article_name,
        require_summary=args.require_summary,
    )
    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload + "\n", encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
validate_solo_script.py — 单人播客脚本的确定性预检（LLM judge 之前）。

硬失败检查（任一不过 → exit 1）：
  - 正文去空白字数 ∈ [min_chars, max_chars]
  - 每段（按空行分段，再按换行）字符数 ≤ max_para_chars
  - 无 Markdown 标记（# ** > ``` 行首 - 等）
  - 元数据：标题（去集号前缀）≤35字、简介字数 ∈ [200,300]、标签 5-8、集号前缀格式 {dddd}：

软警告（写入报告但不影响 exit）：
  - 机器味词命中（单一权威源：article-studio/references/brand-config.md 的
    "## 禁用 AI 腔短语"，与 validate_content_quality.py 同源；config.content.
    machine_word_blocklist_extra 若提供则作为补充词，默认不再维护并行列表）

Usage:
  python validate_solo_script.py --script 播客_脚本.txt --meta 播客_标题与描述.txt [--config config.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path


# AI-腔禁用词的单一权威源：article-studio/references/brand-config.md
# （与 article-studio 的 validate_content_quality.py 解析同一文件，避免两份
# 冲突的"权威"列表漂移）。config.content.machine_word_blocklist_extra 仍可作为
# 补充词，但默认不再维护并行的禁用词列表。
_BRAND_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]  # skills/
    / "article-studio" / "references" / "brand-config.md"
)

# Emergency fallback only, used if brand-config.md is unreadable. Keep in sync
# with the doc; it is NOT a parallel source of truth.
_FALLBACK_MACHINE_WORDS = [
    "值得一提", "不得不承认", "总的来说", "综上所述", "首先", "其次",
    "然而", "与此同时", "不仅如此", "显著提升", "深入探讨",
    "不可忽视", "众所周知", "毋庸置疑", "不言而喻",
]


def _load_brand_machine_words(path: Path = _BRAND_CONFIG_PATH) -> list[str]:
    """Parse brand-config.md "## 禁用 AI 腔短语" into a flat machine-word list.

    Mirrors validate_content_quality.py's _load_banned_phrases() but collapses
    the always/paragraph-start distinction into one list (this validator only
    emits soft warnings, so positional nuance is not needed here).
    """
    if not path.exists():
        return list(_FALLBACK_MACHINE_WORDS)
    text = path.read_text(encoding="utf-8-sig")
    section = re.search(r"##\s*禁用 AI 腔短语(.*?)(?=\n##\s|\Z)", text, flags=re.DOTALL)
    if not section:
        return list(_FALLBACK_MACHINE_WORDS)
    words: list[str] = []
    for phrase, _note in re.findall(r"`([^`]+)`(（[^）]*）)?", section.group(1)):
        # Only accept CJK phrases; skip stray inline-code tokens in the prose.
        if re.search(r"[一-鿿]", phrase):
            words.append(phrase)
    return words or list(_FALLBACK_MACHINE_WORDS)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_chars(text, lo, hi):
    n = len(re.sub(r"\s", "", text))
    return n, (lo <= n <= hi), f"{n} chars (range {lo}-{hi})"


def check_paragraphs(text, limit):
    over = []
    for i, para in enumerate(re.split(r"\n\s*\n", text), 1):
        for line in para.splitlines():
            line = line.strip()
            if not line:
                continue
            if len(line) > limit:
                over.append({"para": i, "len": len(line), "snippet": line[:40]})
    return (len(over) == 0), over


def check_markdown(text):
    marks = []
    for tag, pat in [
        ("heading", r"^\s{0,3}#{1,6}\s"),
        ("bold", r"\*\*[^*]+\*\*"),
        ("italic_star", r"(?<!\*)\*[^*\n]+\*(?!\*)"),
        ("quote", r"^\s{0,3}>\s?"),
        ("code_fence", r"```"),
        ("ul_list", r"^\s{0,3}[-*+]\s"),
        ("ol_list", r"^\s{0,3}\d+\.\s"),
    ]:
        if re.search(pat, text, flags=re.MULTILINE):
            marks.append(tag)
    return (len(marks) == 0), marks


def check_machine_words(text, blocklist):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for w in blocklist:
            if w in line:
                hits.append({"line": i, "word": w, "snippet": line.strip()[:50]})
    return hits


_AI_BUZZWORDS = ["反认知", "反直觉"]


def detect_anti_ai(text):
    """软警告：检测 AI 味套路（三段排比/路标编号/套式连接词反复/AI高频词/信源机械句式/点评标签）。不阻断。"""
    warns = []
    # 三段及以上"比…值钱/靠谱"式工整排比（单句内 ≥3 个"比"且含评价词）
    for s in re.split(r"[。！？]", text):
        if len(re.findall(r"比", s)) >= 3 and re.search(r"比[^\s，,；;。！？]{1,10}(值钱|靠谱|稳|好|强|高|快|慢)", s):
            warns.append("anti_ai: 疑似三段排比（'比…值钱/靠谱'式工整排比是 AI 招牌）")
            break
    # 路标式编号分段（第N关/第N步式；不含"件"，避免误伤"第一件事"等自然口语）
    if re.search(r"第[一二三四五六七八九十两\d]+[关卡步]|先说第[一二三四\d]", text):
        warns.append("anti_ai: 路标式编号分段（用自然过渡代替）")
    # 套式连接词反复（同一套词出现 >1 次）
    for phrase in ["说到这你可能会问", "好那我们", "接下来我们"]:
        if text.count(phrase) > 1:
            warns.append(f"anti_ai: 套式连接词 '{phrase}' 反复出现")
    # 信源机械句式反复（"信源是 XX，X月X号"独立成句，全篇 >2 次即套路）
    source_pattern_hits = len(re.findall(r"信源是.{0,20}[，,]", text))
    if source_pattern_hits > 2:
        warns.append(f"anti_ai: 信源机械句式反复（'信源是 XX，'出现 {source_pattern_hits} 次，>2 次为套路；改为自然嵌入'据 XX 报道'，开场统一交代覆盖日期）")
    # "点评："书面标签残留（应改自然判断句式）
    dianping_hits = len(re.findall(r"点评：", text))
    if dianping_hits > 0:
        warns.append(f"anti_ai: '点评：'书面标签残留 {dianping_hits} 处（改为自然判断句式：'这里值得多看一眼''要我说''换个角度看'）")
    # AI 高频词
    for w in _AI_BUZZWORDS:
        if w in text:
            warns.append(f"anti_ai: AI 高频词 '{w}'")
    return warns


def parse_meta(meta_text):
    """返回 dict: title, intro, tags(list), prefix_ok"""
    info = {"title": "", "intro": "", "tags": [], "prefix_ok": False}
    # 标题
    m = re.search(r"^标题：\s*(.*)$", meta_text, flags=re.MULTILINE)
    if m:
        info["title"] = m.group(1).strip()
        info["prefix_ok"] = bool(re.match(r"^\d{4}：", info["title"]))
    # 简介
    m = re.search(r"简介：\s*\n(.*?)(?=^标签：|\Z)", meta_text, flags=re.MULTILINE | re.DOTALL)
    if m:
        info["intro"] = m.group(1).strip()
    # 标签
    m = re.search(r"^标签：\s*(.*)$", meta_text, flags=re.MULTILINE)
    if m:
        info["tags"] = [t.strip() for t in re.split(r"[\s,，]+", m.group(1).strip()) if t.strip()]
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = args.config or str(skill_root / "config.json")
    cfg = load_config(cfg_path)

    text = Path(args.script).read_text(encoding="utf-8")
    meta_text = Path(args.meta).read_text(encoding="utf-8")

    # 剥 [SECTION:N] 标记用于字数/段落检查（标记 TTS 前会被 extract_sections 剥掉，非正文内容）
    text_clean = re.sub(r"\[SECTION:\w+\]\s*\n?", "", text)

    checks = []
    hard_fail = False

    # 字数
    n, ok, detail = check_chars(text_clean, cfg["content"]["min_chars"], cfg["content"]["max_chars"])
    checks.append({"name": "char_count", "pass": ok, "detail": detail})
    hard_fail = hard_fail or not ok

    # 段落
    ok, over = check_paragraphs(text_clean, cfg["content"]["max_para_chars"])
    checks.append({"name": "paragraph_len<=80", "pass": ok,
                   "detail": "ok" if ok else f"{len(over)} over-limit: {over[:5]}"})
    hard_fail = hard_fail or not ok

    # Markdown
    ok, marks = check_markdown(text)
    checks.append({"name": "no_markdown", "pass": ok,
                   "detail": "ok" if ok else f"found: {marks}"})
    hard_fail = hard_fail or not ok

    # 元数据
    info = parse_meta(meta_text)
    title_body = re.sub(r"^\d{4}：", "", info["title"])
    title_ok = 0 < len(title_body) <= 35
    checks.append({"name": "title_len<=35", "pass": title_ok,
                   "detail": f"{len(title_body)} chars '{title_body}'"})
    hard_fail = hard_fail or not title_ok

    intro_n = len(re.sub(r"\s", "", info["intro"]))
    intro_ok = 200 <= intro_n <= 300
    checks.append({"name": "intro_200-300", "pass": intro_ok, "detail": f"{intro_n} chars"})
    hard_fail = hard_fail or not intro_ok

    tag_ok = 5 <= len(info["tags"]) <= 8
    checks.append({"name": "tags_5-8", "pass": tag_ok, "detail": f"{len(info['tags'])} tags"})
    hard_fail = hard_fail or not tag_ok

    checks.append({"name": "episode_prefix", "pass": info["prefix_ok"],
                   "detail": f"title='{info['title']}' (集号前缀可选，不报错)"})
    # episode_prefix 不再 hard_fail：播客不报集数，标题不带前缀是正常的

    # 软警告：标题质量（数字钩子 + 英文避让）—— 不 hard_fail，只记 warning
    title_warnings = []
    if not re.search(r"[0-9零一二三四五六七八九十百千万亿%]", title_body):
        title_warnings.append("title_no_number_hook")
    if re.search(r"[A-Za-z]{4,}", title_body[:10]):
        title_warnings.append("title_english_heavy_prefix")

    # 软警告：机器词——单一权威源 brand-config.md，config.content.machine_word_blocklist_extra
    # 若提供则作为补充词（去重合并），默认不再维护并行列表。
    machine_words = _load_brand_machine_words()
    extra = cfg.get("content", {}).get("machine_word_blocklist_extra", []) or []
    if extra:
        machine_words = list(dict.fromkeys(machine_words + list(extra)))
    hits = check_machine_words(text, machine_words)

    report = {
        "hard_fail": hard_fail,
        "char_count": n,
        "checks": checks,
        "machine_word_warnings": hits,
        "anti_ai_warnings": detect_anti_ai(text),
        "title_warnings": title_warnings,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()

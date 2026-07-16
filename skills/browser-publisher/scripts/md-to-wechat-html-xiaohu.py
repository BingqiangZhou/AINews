#!/usr/bin/env python3
"""
Markdown to WeChat HTML Converter — xiaohu-wechat-format 引擎适配层。

用 xiaohu-wechat-format 的 format.py（python-markdown + 41 主题）生成内联样式 HTML，
再做本项目需要的后处理（图片路径重写、表格滚动包裹、字体消毒），最后输出
标准 JSON 契约：
    { "title": "...", "content": "...", "digest": "..." }

被 wechat-mp-draft.py 的 --engine xiaohu 路径调用。

Usage:
    python md-to-wechat-html-xiaohu.py --input <markdown_file> [--theme <theme_name>] [--python <path>]

Output (JSON to stdout):
    { "title": "...", "content": "...", "digest": "..." }
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
XIAOHU_DIR = SCRIPT_DIR / "xiaohu-format"
XIAOHU_FORMAT_PY = XIAOHU_DIR / "scripts" / "format.py"


# ─── 字体消毒（西文字名会被微信整条 style 剥光）──────────────────────
# WeChat 的草稿清洗器会拒绝西文具名字体（Georgia、'Times New Roman'、Playfair 等），
# 一旦命中就把整条 style 属性剥光。xiaohu 的 github 主题用了 Georgia/Consolas 等，
# 必须消毒。中文字体（PingFang SC）和通用族关键字（serif/sans-serif）能保留。
_WECHAT_OK_FONT = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto",
    "pingfang sc", "pingfang tc", "hiragino sans gb", "microsoft yahei",
    "微软雅黑", "songti sc", "stsong", "宋体", "simhei", "黑体",
    "noto sans sc", "noto serif sc", "source han sans sc",
}
_FONT_GENERICS = {"serif", "sans-serif", "monospace", "cursive", "fantasy"}


def _safe_font_family(value):
    fonts = [f.strip().strip("\"'").lower() for f in value.split(",")]
    fonts = [f for f in fonts if f]
    kept = [f for f in fonts if f in _WECHAT_OK_FONT]
    if not kept:
        kept = [next((g for g in fonts if g in _FONT_GENERICS), "sans-serif")]
    if not any(f in _FONT_GENERICS for f in kept):
        kept.append("sans-serif")
    out = []
    for f in kept:
        if f in _FONT_GENERICS or f.startswith("-") or f in (
            "system-ui", "blinkmacsystemfont", "segoe ui", "roboto"):
            out.append(f)
        else:
            out.append(f"'{f}'")
    return "font-family: " + ", ".join(out) + ";"


def sanitize_fonts_for_wechat(html):
    """把所有 font-family 折叠成微信可接受的字体栈，避免整条 style 被剥。"""
    return re.sub(r"font-family:\s*([^;]+);", lambda m: _safe_font_family(m.group(1)), html)


# ─── 标题/摘要提取 ─────────────────────────────────────────────────
def extract_title(md):
    for line in md.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return ""


def extract_digest(md, max_len=120):
    text = re.sub(r"^#{1,6}\s+.*", "", md, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    plain = " ".join(lines)
    return plain[:max_len]


def strip_h1(html):
    """Remove the first <h1>...</h1> from HTML content."""
    return re.sub(r"<h1\b[^>]*>.*?</h1>", "", html, count=1, flags=re.DOTALL).lstrip()


# ─── 表格滚动包裹（xiaohu 不套滚动容器，只压缩列宽，这里补回）─────────────
# 用实测过微信兼容的 section 滚动容器方案，匹配 xiaohu 输出的裸 <table>。
def wrap_tables_for_scroll(html):
    wrapper_style = (
        "max-width:100%!important;"
        "width:100%!important;"
        "overflow-x:auto;"
        "overflow-y:hidden;"
        "-webkit-overflow-scrolling:touch;"
        "box-sizing:border-box;"
        "margin:1.5em 0;"
    )
    # 保留 min-width:600px + width:max-content 维持横向滑动能力（宽表/手机窄屏都需要），
    # 但去掉 white-space:nowrap——它强制每个单元格不换行，让内容不长的窄表也被撑超宽。
    # 允许单元格按 word-break 换行后，窄表自然收窄（仍受 min-width 兜底可滑动），
    # 长内容的表照常撑开滑动。
    table_extra_style = "display:block;min-width:600px;width:max-content;"
    hint_style = (
        "text-align:center;font-size:12px;color:#999;"
        "padding:4px 0 0;letter-spacing:0.1em;"
    )
    hint = f'<section style="{hint_style}">← 左右滑动查看完整表格 →</section>'

    count = 0

    def replacer(m):
        nonlocal count
        table_tag = m.group(0)
        # 给 table 加 display:block + min-width
        if 'style="' in table_tag:
            fixed = table_tag.replace('style="', f'style="{table_extra_style}', 1)
        else:
            fixed = table_tag.replace("<table", f'<table style="{table_extra_style}"', 1)
        # width:100% → width:max-content（让表格按内容撑开触发滚动）
        # 注意否定先行 (?<!max-)：只改独立的 width，不误伤 max-width:100%
        fixed = re.sub(r"(?<!max-)width:\s*100%", "width:max-content", fixed)
        count += 1
        return f'<section style="{wrapper_style}">{fixed}'

    # 匹配裸 <table>（xiaohu 输出无外层 div），包进 section 滚动容器
    html = re.sub(r"<table[^>]*>", replacer, html)
    # 每个 </table> 后补 hint + 关闭 section
    html = re.sub(r"(</table>)", lambda m: m.group(1) + hint + "</section>", html)

    if count:
        print(f"[xiaohu] wrapped {count} table(s) with scrollable section", file=sys.stderr)
    return html


# ─── 图片路径重写（xiaohu 用 images/ 前缀，本项目用 imgs/）──────────────
def rewrite_image_paths(html):
    """xiaohu 的 copy_markdown_images 把图片复制到 output/images/ 并用 images/ 前缀。
    本项目的 process_inline_images（wechat-mp-draft.py）正则只匹配 imgs/ 前缀。
    把 images/ 改回 imgs/，让 draft 脚本能找到原文件并上传。
    """
    count = 0

    def replacer(m):
        nonlocal count
        count += 1
        return f'{m.group(1)}imgs/{m.group(2)}{m.group(3)}'

    # src="images/xxx" → src="imgs/xxx"
    html = re.sub(r'(src=")images/([^"]+)(")', replacer, html)
    if count:
        print(f"[xiaohu] rewrote {count} image path(s) images/ → imgs/", file=sys.stderr)
    return html


# ─── 公众号文章互推链接还原（xiaohu 把所有外链脚注化，但公众号文章链接应可点击）──
# xiaohu 的 extract_links_as_footnotes 把所有 http 链接转成「正文上标 [N] + 文末脚注」。
# 这对普通外链（GitHub 等）是对的（公众号正文不支持普通外链跳转），但对公众号文章
# 互推链接（mp.weixin.qq.com）是错的——这类链接在公众号正文里可以直接做成可点击的
# 蓝色文字，读者不用滑到底部找脚注。
#
# 本函数把脚注区里 mp.weixin.qq.com 的条目还原成正文内联可点击链接，并删除对应脚注。
def restore_wechat_article_links(html):
    """把 mp.weixin.qq.com 的脚注还原为正文内联可点击链接。"""
    # 1. 解析脚注区，提取 [idx, text, url] 三元组
    # 脚注条目格式：<p style="...">[N] text: url</p>
    footnote_item_re = re.compile(
        r'<p([^>]*)>\s*\[(\d+)\]\s*([^:]*?):\s*(https?://[^\s<]+)\s*</p>'
    )
    # 公众号文章链接（mp.weixin.qq.com）的脚注条目
    wechat_notes = {}  # idx → (text, url)
    for m in footnote_item_re.finditer(html):
        idx, text, url = int(m.group(2)), m.group(3).strip(), m.group(4).strip()
        if "mp.weixin.qq.com" in url:
            wechat_notes[idx] = (text, url)

    if not wechat_notes:
        return html  # 没有公众号链接，无需处理

    # 2. 正文中把对应的 text<sup>[idx]</sup> 替换成可点击 <a> 链接
    # 公众号正文 <a> 样式：蓝色 + 下划线（微信支持 mp.weixin.qq.com 域名跳转）
    link_style = "color:#576B95;text-decoration:underline"  # #576B95 是公众号标准链接蓝
    for idx, (text, url) in wechat_notes.items():
        # 匹配 text<sup ...>[idx]</sup>（text 后紧跟 sup 上标）
        escaped_text = re.escape(text)
        pattern_str = escaped_text + r'(\s*<sup[^>]*>\s*\[' + str(idx) + r'\]\s*</sup>)'
        sup_pattern = re.compile(pattern_str)
        replacement = f'<a href="{url}" style="{link_style}">{text}</a>'
        new_html, n = sup_pattern.subn(replacement, html)
        if n > 0:
            html = new_html
            print(
                f"[xiaohu] restored wechat link [{idx}] inline: "
                f"{text[:30]}... → mp.weixin.qq.com",
                file=sys.stderr,
            )

    # 3. 从脚注区删除已还原的公众号链接条目
    def remove_replaced_footnote(m):
        idx = int(m.group(2))
        if idx in wechat_notes:
            return ""  # 删除该脚注条目
        return m.group(0)

    html = footnote_item_re.sub(remove_replaced_footnote, html)
    return html


# ─── 脚注去重（xiaohu 对同一 URL 多次出现分配不同编号，脚注区重复）─────────
# xiaohu 的 extract_links_as_footnotes 对每个 <a> 都递增计数器，不去重 URL。
# 例如 https://acemusic.ai 出现两次会得到 [1] 和 [5]，脚注区列两条一模一样的条目。
# 本函数把重复 URL 的后续上标编号改成首次出现的编号，并删除脚注区的重复条目。
def dedup_footnotes(html):
    """合并重复 URL 的脚注：后续出现改用首个编号，删除脚注区重复条目。"""
    footnote_item_re = re.compile(
        r'<p([^>]*)>\s*\[(\d+)\]\s*([^:]*?):\s*(https?://[^\s<]+)\s*</p>'
    )

    # 收集每个 URL 的首个编号（按出现顺序）
    url_to_first_idx = {}  # url → first idx (int)
    dup_mapping = {}       # later idx (int) → first idx (int)
    for m in footnote_item_re.finditer(html):
        idx = int(m.group(2))
        url = m.group(4).strip()
        if url in url_to_first_idx:
            first = url_to_first_idx[url]
            if idx != first:
                dup_mapping[idx] = first
        else:
            url_to_first_idx[url] = idx

    if not dup_mapping:
        return html  # 无重复

    # 1. 正文中把重复的上标编号改成首个编号
    for later_idx, first_idx in dup_mapping.items():
        # 匹配 <sup ...>[later_idx]</sup>
        pattern = re.compile(r'(<sup[^>]*>\s*)\[' + str(later_idx) + r'\](\s*</sup>)')
        html, n = pattern.subn(r'\g<1>[' + str(first_idx) + r']\g<2>', html)
        if n:
            print(
                f"[xiaohu] dedup footnote: [{later_idx}] → [{first_idx}] "
                f"(重复 URL 合并)",
                file=sys.stderr,
            )

    # 2. 从脚注区删除重复条目（保留首次出现的）
    def remove_dup(m):
        idx = int(m.group(2))
        if idx in dup_mapping:
            return ""
        return m.group(0)

    html = footnote_item_re.sub(remove_dup, html)
    return html


# ─── 空脚注区清理 ──────────────────────────────────────────────────────
# restore_wechat_article_links 把 mp.weixin.qq.com 脚注还原为内联链接后会删除脚注条目，
# dedup_footnotes 合并重复 URL 后也会删条目。这两种情况都可能留下空的脚注区：
# 只有"参考链接"标题 + 空 section 外壳，没有任何 [N] 条目。这种空壳必须清掉，否则
# 读者会在文末看到一个没有内容的"参考链接"小标题。
def cleanup_empty_footnote_section(html):
    """删除没有任何脚注条目的空"参考链接"区（标题 + section 外壳）。"""
    footnote_item_re = re.compile(
        r'<p([^>]*)>\s*\[(\d+)\]\s*[^:]*?:\s*https?://[^\s<]+\s*</p>'
    )
    # 如果还有脚注条目，说明脚注区非空，无需处理
    if footnote_item_re.search(html):
        return html

    # 没有脚注条目但可能有空壳：删除"参考链接"标题段
    # 标题格式：<p style="...">参考链接</p>（含可能的空白/换行）
    title_re = re.compile(r'<p[^>]*>\s*参考链接\s*</p>\s*', re.MULTILINE)
    new_html, n = title_re.subn('', html)
    if n:
        print("[xiaohu] removed empty 参考链接 section (no footnote items left)", file=sys.stderr)
        # 顺带清理可能残留的空 <section>...</section> 外壳（脚注区 section）
        # 脚注区 section 通常紧跟标题，现在标题已删，section 可能仍在
        new_html = re.sub(r'<section style="[^"]*">\s*</section>\s*', '', new_html)
    return new_html


# ─── 代码块 pre>code 扁平化（微信 API 对 pre>code 嵌套做错误处理）────────
# 微信草稿清洗器对 <pre><code style="...">...</code></pre> 嵌套结构有固定动作：
# 它试图给 <code> 注入 font-size:16px，但正则替换出 bug，产生
# "font-size:16px="font-size:16px" px="px"" 这种乱码属性，导致整条 style 失效，
# 甚至让 </code></pre> 闭合错乱、<pre> 吞噬后续所有正文内容。
#
# 根因：<pre> 内嵌 <code> 这个结构本身触发微信的有 bug 的清洗逻辑。
# 解法：把 <pre><code style="...">CONTENT</code></pre> 扁平化为
# <pre style="(合并样式)">CONTENT</pre>——去掉内层 <code> 标签，
# 把 code 的有用样式(color)合并到 pre，内容原样保留。微信没有 <pre><code> 嵌套可破坏。
def flatten_pre_code(html):
    """把 <pre><code>...</code></pre> 扁平化为 <pre>...</pre>，规避微信清洗 bug。"""
    count = 0

    def replacer(m):
        nonlocal count
        pre_open = m.group(1)      # <pre ...>
        code_open = m.group(2)     # <code ...>
        content = m.group(3)       # 代码内容（第三个捕获组）
        # code 的有用样式：color（pre 可能没有）
        code_color = ""
        cm = re.search(r"color:\s*(#[0-9a-fA-F]+)", code_open)
        if cm:
            pre_color = re.search(r"color:\s*(#[0-9a-fA-F]+)", pre_open)
            if not pre_color or pre_color.group(1) != cm.group(1):
                code_color = cm.group(0)
        # 合并到 pre 的 style 末尾
        if code_color and 'style="' in pre_open:
            new_pre = pre_open.replace('style="', f'style="{code_color};', 1)
        else:
            new_pre = pre_open
        count += 1
        return f"{new_pre}{content}</pre>"

    # 匹配 <pre ...><code ...>CONTENT</code></pre>（3 个捕获组）
    html = re.sub(
        r"(<pre\b[^>]*>)\s*(<code\b[^>]*>)([\s\S]*?)</code>\s*</pre>",
        replacer, html
    )
    if count:
        print(f"[xiaohu] flattened {count} <pre><code> → <pre> (规避微信清洗 bug)", file=sys.stderr)
    return html


# ─── 主转换函数 ──────────────────────────────────────────────────────
def md_to_wechat_html_xiaohu(md_file_path, theme="github", python_executable=None):
    """用 xiaohu format.py 把 markdown 转成微信兼容 HTML。"""
    md_file = Path(md_file_path).resolve()
    if not XIAOHU_FORMAT_PY.exists():
        raise FileNotFoundError(f"xiaohu format.py not found: {XIAOHU_FORMAT_PY}")

    python = python_executable or os.environ.get("XIAOHU_PYTHON", sys.executable)

    # 读原始 md（提取 title/digest 用）
    md_text = md_file.read_text(encoding="utf-8")
    title = extract_title(md_text)
    digest = extract_digest(md_text)

    # 用临时目录做输出，避免污染项目
    with tempfile.TemporaryDirectory(prefix="xiaohu_fmt_") as tmp_out:
        tmp_out_path = Path(tmp_out)
        cmd = [
            python, str(XIAOHU_FORMAT_PY),
            "--input", str(md_file),
            "--theme", theme,
            "--output", str(tmp_out_path),
            "--no-open",
            "--format", "wechat",
        ]
        print(f"[xiaohu] Running: {theme} theme", file=sys.stderr)
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            cwd=str(XIAOHU_DIR),  # format.py 模块级读 config.json 需要 cwd 正确
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"xiaohu format.py failed (exit {result.returncode}):\n{result.stderr}"
            )
        # format.py 日志在 stdout/stderr，article.html 在 <output>/<stem>/article.html
        stem = md_file.stem
        article_html_path = tmp_out_path / stem / "article.html"
        if not article_html_path.exists():
            raise FileNotFoundError(
                f"xiaohu did not produce article.html at {article_html_path}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        content = article_html_path.read_text(encoding="utf-8")

    # 去掉 H1（标题作为草稿 title 字段，不重复出现在正文）
    if title:
        content = strip_h1(content)

    # 后处理 1: 图片路径 images/ → imgs/
    content = rewrite_image_paths(content)

    # 后处理 2: 表格滚动包裹（xiaohu 不套滚动容器，这里补回）
    content = wrap_tables_for_scroll(content)

    # 后处理 3: 字体消毒（xiaohu 主题用了 Georgia/Consolas，微信会剥光整条 style）
    content = sanitize_fonts_for_wechat(content)

    # 后处理 4: 扁平化 pre>code 嵌套（微信对 <pre><code> 有清洗 bug，会破坏样式+吞噬内容）
    content = flatten_pre_code(content)

    # 后处理 5: 公众号文章互推链接还原（xiaohu 脚注化所有外链，但 mp.weixin.qq.com 应可点击）
    content = restore_wechat_article_links(content)

    # 后处理 6: 脚注去重（同一 URL 多次出现分配不同编号，合并为首个编号）
    content = dedup_footnotes(content)

    # 后处理 7: 空脚注区清理（脚注条目被前面步骤清空时，删掉残留的"参考链接"标题）
    content = cleanup_empty_footnote_section(content)

    return {"title": title, "content": content, "digest": digest}


def main():
    parser = argparse.ArgumentParser(description="Convert markdown to WeChat HTML (xiaohu engine)")
    parser.add_argument("--input", required=True, help="Input markdown file path")
    parser.add_argument("--theme", default="github", help="xiaohu theme name (default: github)")
    parser.add_argument("--python", default="", help="Python executable for format.py subprocess")
    args = parser.parse_args()

    py = args.python if args.python else None
    result = md_to_wechat_html_xiaohu(args.input, theme=args.theme, python_executable=py)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

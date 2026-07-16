"""WeChat MP Draft Creator — 通过微信公众号 API 创建草稿文章。

用法: python wechat-mp-draft.py --project-dir "<directory>" [--html-file "<path>"]

环境变量:
  WECHAT_MP_APPID     — 公众号 AppID
  WECHAT_MP_APPSECRET — 公众号 AppSecret
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Shared helpers from scripts/lib/utils.py (run as a script -> scripts/ is on
# sys.path[0]; the insert keeps it import-safe under other loaders too).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import (  # noqa: E402
    get_access_token,
    https_post_json,
    upload_multipart,
)

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SKILL_DIR / "config.json"


def upload_thumb_image(access_token, image_path):
    print(f"[upload] Uploading cover image: {image_path}", file=sys.stderr)
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
    resp = upload_multipart(url, image_path)
    if resp.get("errcode"):
        raise RuntimeError(f"Upload thumb error: {resp['errcode']} - {resp['errmsg']}")
    print(f"[upload] Cover uploaded. media_id={resp['media_id']}", file=sys.stderr)
    return resp


def upload_article_image(access_token, image_path):
    print(f"[upload-img] Uploading: {image_path}", file=sys.stderr)
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
    resp = upload_multipart(url, image_path)
    if resp.get("errcode"):
        raise RuntimeError(f"Upload image error: {resp['errcode']} - {resp['errmsg']}")
    print(f"[upload-img] OK: {resp['url']}", file=sys.stderr)
    return resp["url"]


def process_inline_images(access_token, html, project_dir):
    img_regex = re.compile(r'(<img\s+[\s\S]*?src=")(imgs/[^"]+)("[\s\S]*?/?>)')
    uploaded = 0
    total = len(list(img_regex.finditer(html)))
    while True:
        match = img_regex.search(html)
        if not match:
            break
        local_path = match.group(2)
        full_path = Path(project_dir) / local_path

        # WeChat API does not accept webp — fall back to png if referenced as webp
        if local_path.endswith(".webp"):
            png_path = Path(str(full_path).replace(".webp", ".png"))
            if png_path.exists():
                full_path = png_path

        if full_path.exists():
            wx_url = upload_article_image(access_token, str(full_path))
            replacement = match.group(1) + wx_url + match.group(3)
            html = html[:match.start()] + replacement + html[match.end():]
            uploaded += 1
        else:
            print(f"[warn] Image not found: {full_path}", file=sys.stderr)
            break

    print(f"[upload-img] {uploaded}/{total} images uploaded", file=sys.stderr)
    return html, uploaded




def create_draft(access_token, article):
    print(f"[draft] Creating draft: \"{article['title']}\"", file=sys.stderr)
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    body = {
        "articles": [{
            "title": article["title"],
            "author": article["author"],
            "digest": article["digest"],
            "content": article["content"],
            "thumb_media_id": article["thumb_media_id"],
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }],
    }
    resp = https_post_json(url, body)
    if resp.get("errcode"):
        raise RuntimeError(f"Draft API error: {resp['errcode']} - {resp['errmsg']}")
    print(f"[draft] Draft created. media_id={resp['media_id']}", file=sys.stderr)
    return resp["media_id"]


# --- Markdown to HTML (via xiaohu-wechat-format) ---

def markdown_to_html(md_file_path, theme="github"):
    """xiaohu-wechat-format 引擎。输出 {title, content, digest} JSON 契约。
    图片路径重写、表格滚动包裹、字体消毒由 md-to-wechat-html-xiaohu.py 内部完成。"""
    script = Path(__file__).parent / "md-to-wechat-html-xiaohu.py"
    python = os.environ.get("XIAOHU_PYTHON", sys.executable)
    cmd = [python, str(script), "--input", str(md_file_path), "--theme", theme]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"xiaohu conversion failed: {result.stderr}")
    return json.loads(result.stdout)


# --- Helpers ---

def extract_title_from_html(html):
    m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def strip_title_from_content(html):
    return re.sub(r"<h1[^>]*>[\s\S]*?</h1>\s*", "", html, count=1)


def read_digest(project_dir):
    digest_file = Path(project_dir) / "公众号_摘要.txt"
    if digest_file.exists():
        return digest_file.read_text(encoding="utf-8").strip()
    return ""


def main():
    parser = argparse.ArgumentParser(description="通过微信公众号 API 创建草稿文章")
    parser.add_argument("--project-dir", required=True, help="项目目录")
    parser.add_argument("--html-file", default="", help="直接使用 HTML 文件 (跳过 Markdown 转换)")
    parser.add_argument("--md", default="", help="指定 Markdown 文件路径 (默认用 <project-dir>/公众号_文章.md)")
    parser.add_argument("--title", default="", help="Override article title (当 HTML 中缺少 h1 标题时使用)")
    parser.add_argument("--theme", default="github", help="xiaohu 主题名 (默认 github，可用 --theme 覆盖，可选: github/chinese/elegant-classic/newspaper 等 41 个)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    html_file = Path(args.html_file).resolve() if args.html_file else None
    cover_file = project_dir / "公众号_封面.png"

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
    author = config.get("wechat_mp", {}).get("author", "Bingqiang Zhou")

    if html_file:
        if not html_file.exists():
            raise RuntimeError(f"HTML file not found: {html_file}")
        content = html_file.read_text(encoding="utf-8")
        title = args.title or extract_title_from_html(content)
        content = strip_title_from_content(content)
        digest = read_digest(project_dir)
        if not title:
            raise RuntimeError("Could not extract title. Use --title to provide one, or ensure HTML contains an <h1> tag.")
        print(f"[parse] Using HTML file: {html_file}", file=sys.stderr)
        print(f'[parse] Title: "{title}"', file=sys.stderr)
        print(f"[parse] Content: {len(content)} chars, digest: {len(digest)} chars", file=sys.stderr)
    else:
        md_file = Path(args.md).resolve() if args.md else (project_dir / "公众号_文章.md")
        if not md_file.exists():
            raise RuntimeError(f"File not found: {md_file}")
        result = markdown_to_html(md_file, args.theme)
        title = result["title"]
        content = strip_title_from_content(result["content"])
        digest = read_digest(project_dir) or result.get("digest", "")
        if not title:
            raise RuntimeError("Could not extract title from markdown. Ensure the first line starts with '# '.")
        print(f'[parse] Title: "{title}"', file=sys.stderr)
        print(f"[parse] Content: {len(content)} chars, {len(digest)} chars digest", file=sys.stderr)

    # Step 1: Get access token
    access_token = get_access_token()

    # Step 2: Upload inline images
    processed_content, image_count = process_inline_images(access_token, content, str(project_dir))

    # (表格滚动包裹由 md-to-wechat-html-xiaohu.py 内部完成，此处无需再处理)

    # Step 3: Upload cover image
    thumb_media_id = ""
    if cover_file.exists():
        upload_result = upload_thumb_image(access_token, str(cover_file))
        thumb_media_id = upload_result["media_id"]
    else:
        print(f"[warn] Cover image not found: {cover_file}", file=sys.stderr)
        print("[warn] Creating draft without cover image", file=sys.stderr)

    # Step 4: Create draft
    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": processed_content,
        "thumb_media_id": thumb_media_id,
    }

    media_id = create_draft(access_token, article)

    result = {
        "success": True,
        "media_id": media_id,
        "title": title,
        "author": author,
        "has_cover": bool(thumb_media_id),
        "inline_images": image_count,
    }

    # 草稿创建成功 → 自动写 publish.json 的 wechat_mp track (status=draft)。
    # 这是「某篇文章发到哪些平台」的权威记录（schema publish-record-v1）。
    # 写失败只 warn，绝不阻断草稿创建主流程（publish.json 是记录，不是草稿本身）。
    try:
        from update_publish_record import update_record
        update_record(
            project_dir,
            "wechat_mp",
            "draft",
            url="https://mp.weixin.qq.com/",
            media_id=media_id,
        )
        result["publish_record"] = "draft"
    except Exception as exc:
        print(f"[warn] publish.json 未写入: {exc}", file=sys.stderr)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        sys.exit(130)
    except Exception as err:
        print(f"\n[error] {err}", file=sys.stderr)
        print(json.dumps({"success": False, "error": str(err)}, indent=2, ensure_ascii=False))
        sys.exit(1)

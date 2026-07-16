"""WeChat MP Draft Updater — 更新已有草稿的标题/封面/摘要。

用法: python wechat-mp-update-draft.py --media-id "<id>" [--title "..."] [--cover "path"] [--digest "..."] [--project-dir "dir"]

环境变量:
  WECHAT_MP_APPID     — 公众号 AppID
  WECHAT_MP_APPSECRET — 公众号 AppSecret
"""
import argparse
import json
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


def get_draft(access_token, media_id):
    print(f"[draft] Fetching draft: {media_id}", file=sys.stderr)
    resp = https_post_json(
        f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={access_token}",
        {"media_id": media_id},
    )
    if resp.get("errcode"):
        raise RuntimeError(f"Get draft error: {resp['errcode']} - {resp['errmsg']}")
    return resp["news_item"]


def update_draft(access_token, media_id, index, articles):
    print(f"[draft] Updating draft: {media_id}", file=sys.stderr)
    resp = https_post_json(
        f"https://api.weixin.qq.com/cgi-bin/draft/update?access_token={access_token}",
        {"media_id": media_id, "index": index, "articles": articles},
    )
    if resp.get("errcode"):
        raise RuntimeError(f"Update draft error: {resp['errcode']} - {resp['errmsg']}")
    return resp


def upload_thumb(access_token, image_path):
    print(f"[upload] Uploading cover: {image_path}", file=sys.stderr)
    resp = upload_multipart(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=thumb",
        image_path,
    )
    if resp.get("errcode"):
        raise RuntimeError(f"Upload error: {resp['errcode']} - {resp['errmsg']}")
    print(f"[upload] Uploaded. media_id={resp['media_id']}", file=sys.stderr)
    return resp["media_id"]


def list_drafts(access_token, count=20):
    print(f"[draft] Listing drafts (count={count})", file=sys.stderr)
    resp = https_post_json(
        f"https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token={access_token}",
        {"offset": 0, "count": count, "no_content": 1},
    )
    if resp.get("errcode"):
        raise RuntimeError(f"List drafts error: {resp['errcode']} - {resp['errmsg']}")
    return resp["item"]


def main():
    parser = argparse.ArgumentParser(description="更新已有微信公众号草稿")
    parser.add_argument("--media-id", required=True, help="草稿 media_id")
    parser.add_argument("--title", default="", help="新标题")
    parser.add_argument("--cover", default="", help="新封面图路径")
    parser.add_argument("--digest", default="", help="新摘要")
    parser.add_argument("--project-dir", default="", help="项目目录 (读取 公众号_摘要.txt)")
    args = parser.parse_args()

    # If no digest provided but project-dir has 公众号_摘要.txt, read from it
    digest = args.digest
    if not digest and args.project_dir:
        digest_file = Path(args.project_dir) / "公众号_摘要.txt"
        if digest_file.exists():
            digest = digest_file.read_text(encoding="utf-8").strip()
            print(f"[digest] Read from file: {len(digest)} chars", file=sys.stderr)

    access_token = get_access_token()
    media_id = args.media_id

    # Get existing draft articles
    articles = get_draft(access_token, media_id)
    if not articles:
        raise RuntimeError("Draft has no articles")

    existing = articles[0]
    update = {
        "title": args.title or existing["title"],
        "author": existing["author"],
        "digest": digest or existing.get("digest", ""),
        "content": existing["content"],
        "thumb_media_id": existing.get("thumb_media_id", ""),
        "need_open_comment": existing.get("need_open_comment", 0),
        "only_fans_can_comment": existing.get("only_fans_can_comment", 0),
    }

    # Upload new cover if provided
    if args.cover and Path(args.cover).exists():
        update["thumb_media_id"] = upload_thumb(access_token, args.cover)

    update_draft(access_token, media_id, 0, update)

    result = {
        "success": True,
        "media_id": media_id,
        "title": update["title"],
        "digest": update["digest"][:60] + "...",
        "cover_updated": bool(args.cover),
    }

    # 草稿更新成功 → 刷新 publish.json 的 wechat_mp track（保持 status=draft，
    # 刷新 media_id/title；更新不是发表）。仅当传了 --project-dir 才写。
    # 写失败只 warn，不阻断更新主流程。
    if args.project_dir:
        try:
            from update_publish_record import update_record
            update_record(
                Path(args.project_dir),
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

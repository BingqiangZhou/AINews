"""WeChat MP Video Material Uploader — 把视频作为永久视频素材上传到公众号素材库。

用法:
  python wechat-mp-upload-video.py --project-dir "<dir>" [--md "<article.md>"] [--limit N] [--delay 1.0]

从文章 markdown 中按文档顺序提取所有视频引用 (results/**/*.mp4)，
逐条通过 add_material?type=video 上传为永久视频素材，记录 media_id 到清单 JSON。
视频素材要求 multipart 同时带 media(文件) 和 description(JSON: title+introduction)。

环境变量:
  WECHAT_MP_APPID / WECHAT_MP_APPSECRET (由 lib.utils.get_access_token 读取)
"""
import argparse
import json
import mimetypes
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen, Request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import get_access_token  # noqa: E402

DIR_LABEL = {
    "single_subject": "单主体运动·橘猫海滩走",
    "multi_dynamic": "复杂多动态·夜间城市航拍",
    "camera_motion": "运镜控制·科幻走廊推镜头",
    "underwater": "特殊场景·水下海龟",
    "long_video": "长视频·夜市街道",
}
RUN_RE = re.compile(r"run(\d+)", re.I)


def video_title(relpath):
    p = Path(relpath)
    cat = p.parts[1] if len(p.parts) > 2 else p.parent.name
    fname = p.stem
    if cat == "consistency":
        if "cat" in fname:
            label = "复现性·窗台橘猫看雨"
        elif "market" in fname:
            label = "复现性·夜市摊位"
        else:
            label = "复现性"
    elif cat == "i2v":
        if "cat" in fname:
            label = "图生视频·窗台橘猫"
        elif "man" in fname or "subway" in fname:
            label = "图生视频·地铁青年"
        elif "food" in fname:
            label = "图生视频·夜市小笼包"
        else:
            label = "图生视频"
    else:
        label = DIR_LABEL.get(cat, cat)
    m = RUN_RE.search(fname)
    if m:
        return f"{label} - 第{m.group(1)}次"
    return label


def upload_video_material(token, video_path, title, introduction="Agnes 视频模型实测素材"):
    url = (f"https://api.weixin.qq.com/cgi-bin/material/add_material"
           f"?access_token={token}&type=video")
    boundary = uuid.uuid4().hex
    video = Path(video_path).read_bytes()
    mime = mimetypes.guess_type(str(video_path))[0] or "video/mp4"
    desc = json.dumps({"title": title, "introduction": introduction}, ensure_ascii=False)
    b = f"--{boundary}\r\n".encode()
    head_desc = b'Content-Disposition: form-data; name="description"\r\n\r\n'
    head_media = (f'Content-Disposition: form-data; name="media"; filename="{Path(video_path).name}"\r\n'
                 f"Content-Type: {mime}\r\n\r\n").encode()
    body = (b + head_desc + desc.encode("utf-8") + b"\r\n"
            + b + head_media + video + b"\r\n"
            + b + b"--\r\n")
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    with urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--md", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    project_dir = Path(args.project_dir).resolve()
    orig = project_dir / "02-agnes-video-免费视频模型实测_v2.md"
    md_file = Path(args.md) if args.md else orig
    text = md_file.read_text(encoding="utf-8")

    vids = re.findall(r'\[!\[[^\]]*\]\([^)]+\)\]\(([^)]+\.mp4)\)', text)
    seen, ordered = set(), []
    for v in vids:
        if v not in seen:
            seen.add(v)
            ordered.append(v)
    if args.limit:
        ordered = ordered[:args.limit]
    print(f"[extract] {len(ordered)} videos from {md_file.name}", file=sys.stderr)

    token = get_access_token()
    results = []
    for i, rel in enumerate(ordered, 1):
        full = project_dir / rel
        title = video_title(rel)
        if not full.exists():
            print(f"[{i}/{len(ordered)}] MISSING: {rel}", file=sys.stderr)
            results.append({"path": rel, "title": title, "ok": False, "error": "missing"})
            continue
        size_kb = full.stat().st_size // 1024
        print(f"[{i}/{len(ordered)}] {title} <- {rel} ({size_kb}KB)", file=sys.stderr)
        try:
            resp = upload_video_material(token, str(full), title)
            if resp.get("media_id"):
                print(f"   OK media_id={resp['media_id']}", file=sys.stderr)
                results.append({"path": rel, "title": title, "ok": True,
                                "media_id": resp["media_id"], "url": resp.get("url")})
            else:
                print(f"   ERR {resp}", file=sys.stderr)
                results.append({"path": rel, "title": title, "ok": False, "error": str(resp)})
        except Exception as e:  # noqa: BLE001
            print(f"   EXC {e}", file=sys.stderr)
            results.append({"path": rel, "title": title, "ok": False, "error": str(e)})
        time.sleep(args.delay)

    manifest = project_dir / "公众号_视频素材清单.json"
    manifest.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r.get("ok"))
    print(json.dumps({"total": len(results), "ok": ok, "manifest": str(manifest)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

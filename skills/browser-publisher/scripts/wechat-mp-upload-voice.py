"""WeChat MP Voice Uploader — 上传音频为公众号永久 voice 素材。

用法: python wechat-mp-upload-voice.py --file "<音频文件路径>"

环境变量:
  WECHAT_MP_APPID     — 公众号 AppID
  WECHAT_MP_APPSECRET — 公众号 AppSecret

微信 voice 素材约束：格式 mp3/wma/wav/amr；大小 ≤30MB；时长 ≤30 分钟。
超过限制（如长播客）改用文章正文放外链（喜马拉雅等）的方式，见 wechat-mp.md。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import get_access_token, upload_multipart  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="上传音频为微信公众号永久 voice 素材")
    parser.add_argument("--file", required=True, help="音频文件路径 (mp3/wma/wav/amr)")
    args = parser.parse_args()

    audio_path = Path(args.file).resolve()
    if not audio_path.exists():
        raise RuntimeError(f"File not found: {audio_path}")

    size_mb = audio_path.stat().st_size / (1024 * 1024)
    if size_mb > 30:
        raise RuntimeError(
            f"File too large: {size_mb:.1f}MB > 30MB limit. "
            "voice 素材限 ≤30MB；长音频请改用文章正文放外链（喜马拉雅等）。"
        )
    print(f"[upload] {audio_path.name} ({size_mb:.1f}MB)", file=sys.stderr)

    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=voice"
    resp = upload_multipart(url, audio_path)

    if resp.get("media_id"):
        print(json.dumps({
            "success": True,
            "media_id": resp["media_id"],
            "filename": audio_path.name,
        }, ensure_ascii=False))
    else:
        raise RuntimeError(f"Upload failed: {json.dumps(resp, ensure_ascii=False)}")


if __name__ == "__main__":
    main()

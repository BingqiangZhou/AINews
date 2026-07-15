#!/usr/bin/env python3
"""
Shared utilities for browser-publisher WeChat MP scripts.

Vendored (intentionally, per the project's skill-independence principle) to keep
browser-publisher standalone. Holds the access-token cache and the HTTP helpers
that wechat-mp-draft.py / wechat-mp-update-draft.py previously each inlined a
copy of.

Functions:
    get_access_token()                — cached WeChat MP access_token
    https_get_json(url)               — GET, parse JSON
    https_post_json(url, body)        — POST JSON, parse JSON
    upload_multipart(url, file_path)  — POST a file as multipart/form-data
"""

import json
import mimetypes
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen, Request

_UTILS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _UTILS_FILE.parent.parent
SKILL_DIR = _UTILS_FILE.parent.parent.parent
TOKEN_CACHE_FILE = SKILL_DIR / "configs" / "browser-auth" / "wechat-mp-token.json"

TOKEN_EXPIRY_MARGIN = 300


# --- HTTP helpers ---

def https_get_json(url):
    req = Request(url)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def https_post_json(url, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def upload_multipart(url, file_path):
    file_path = Path(file_path)
    boundary = uuid.uuid4().hex
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_data = file_path.read_bytes()

    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header + file_data + footer

    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


# --- API: access token (with on-disk cache) ---

def get_access_token():
    """Return a valid WeChat MP access_token, caching it to disk.

    Reads WECHAT_MP_APPID / WECHAT_MP_APPSECRET from the environment. Reuses a
    cached token (configs/browser-auth/wechat-mp-token.json) if it is still
    valid beyond TOKEN_EXPIRY_MARGIN seconds; otherwise fetches a fresh one and
    caches it. Raises RuntimeError on missing env vars or an API error.
    """
    app_id = os.environ.get("WECHAT_MP_APPID")
    app_secret = os.environ.get("WECHAT_MP_APPSECRET")
    if not app_id or not app_secret:
        raise RuntimeError("Missing environment variables: WECHAT_MP_APPID and/or WECHAT_MP_APPSECRET")

    if TOKEN_CACHE_FILE.exists():
        try:
            cached = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
            if cached.get("access_token") and cached["expires_at"] > time.time() + TOKEN_EXPIRY_MARGIN:
                remaining = int((cached["expires_at"] - time.time()) / 60)
                print(f"[token] Using cached access token (expires in {remaining} min)", file=sys.stderr)
                return cached["access_token"]
        except Exception:
            pass

    print("[token] Fetching new access token...", file=sys.stderr)
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    resp = https_get_json(url)
    if resp.get("errcode"):
        raise RuntimeError(f"Token API error: {resp['errcode']} - {resp['errmsg']}")

    token_data = {
        "access_token": resp["access_token"],
        "expires_at": int(time.time()) + resp["expires_in"],
    }
    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"[token] Cached access token (valid for {int(resp['expires_in'] / 60)} min)", file=sys.stderr)
    return resp["access_token"]

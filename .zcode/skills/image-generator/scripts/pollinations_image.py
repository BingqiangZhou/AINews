#!/usr/bin/env python3
"""
Pollinations 图片模型测试脚本（flux / turbo / ...）

完全基于官方文档（https://github.com/pollinations/pollinations/blob/master/APIDOCS.md）。
依赖 requests + Pillow（Pillow 用于读实际输出像素尺寸 / 校验图片完整性，
并把 jpeg 字节统一另存为 png，与系列里其它文章的命名约定对齐）。

官方接口要点（图片接口是 **GET only**，没有 POST body 端点）：
  - 端点：GET https://image.pollinations.ai/prompt/{prompt}
         （也支持统一网关 https://gen.pollinations.ai/image/{prompt}，用 --base 切换）
  - 认证：Authorization: Bearer <key> 头（推荐）；也可 --auth query 走 ?key=<key>
  - 参数：model / width / height / seed / nologo / enhance / private
  - 返回：直接返回图片字节（Content-Type: image/jpeg 或 image/png），不是 JSON

⚠️ 双 key 轮换（本任务核心约束）：
  - 读两个 env：POLLINATIONS_API_KEY_precise-koi、POLLINATIONS_API_KEY_sick-snake
    （额度按小时刷新）。任一 key 命中 429/限流 → 标记冷却、切到另一个 key 立即重试；
    两个都在冷却 → sleep 到最早恢复点再重试。这就是"一个不够换另一个，两个都不够就等"。
  - 传 --api-key 则进单 key 模式（不轮换）。

用法：
  python pollinations_image.py --prompt "a cat in space" --model flux -o cat.png
  python pollinations_image.py --prompt "..." --model turbo --seed 42 --size 1024x1024 -o out.png --meta out.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

DEFAULT_BASE = "https://image.pollinations.ai"
DEFAULT_MODEL = "flux"

# 两个按小时刷新额度的 key（env 变量名）；顺序即优先级（sick-snake 额度更充裕，优先用）
KEY_ENVS = ["POLLINATIONS_API_KEY_sick-snake", "POLLINATIONS_API_KEY_precise-koi"]


def mask(key: str) -> str:
    """日志里只露前缀 + 长度，绝不打印完整 key。"""
    if not key:
        return "<empty>"
    return f"{key[:3]}…(len={len(key)})"


def load_keys(cli_key: str | None) -> list[tuple[str, str]]:
    """返回 [(label, value), ...]。label 取 env 名后缀（precise-koi / sick-snake），非密。"""
    if cli_key:
        return [("cli", cli_key)]
    keys: list[tuple[str, str]] = []
    missing: list[str] = []
    for env in KEY_ENVS:
        v = os.environ.get(env)
        if v:
            label = env.split("_", 3)[-1]  # POLLINATIONS_API_KEY_precise-koi -> precise-koi
            keys.append((label, v))
        else:
            missing.append(env)
    if not keys:
        sys.exit("错误：未找到任何 API Key。请设置环境变量 "
                 + " / ".join(KEY_ENVS) + "，或用 --api-key 传入。")
    if missing:
        print(f"⚠️ 未设置：{', '.join(missing)}（将只用已设置的 key）", file=sys.stderr)
    print(f"已加载 {len(keys)} 个 key：" + ", ".join(f"{lbl}({mask(v)})" for lbl, v in keys),
          file=sys.stderr)
    return keys


class KeyRotator:
    """双 key 轮换 + 冷却 + 等待。"""

    def __init__(self, keys: list[tuple[str, str]], cooldown: int):
        self.keys = keys
        self.cooldown = cooldown
        self.cooling: dict[str, float] = {}  # label -> 恢复时间戳
        self._idx = 0

    def available(self) -> list[tuple[str, str]]:
        now = time.time()
        return [(l, v) for (l, v) in self.keys if self.cooling.get(l, 0) <= now]

    def mark_cooling(self, label: str) -> None:
        self.cooling[label] = time.time() + self.cooldown
        print(f"  ⏸ {label} 命中限流，冷却 {self.cooldown}s（到 {time.strftime('%H:%M:%S', time.localtime(self.cooling[label]))}）",
              file=sys.stderr)

    def wait_for_any(self) -> None:
        """所有 key 都在冷却时，睡到最早恢复点。"""
        if not self.cooling:
            return
        now = time.time()
        earliest_label = min(self.cooling, key=lambda l: self.cooling[l])
        wait = max(0.0, self.cooling[earliest_label] - now) + 2.0
        print(f"  ⏳ 所有 key 都在冷却，等待 {wait:.0f}s（{earliest_label} 先恢复）…",
              file=sys.stderr)
        time.sleep(wait)


def _looks_like_quota_error(resp: requests.Response) -> bool:
    """429，或返回 JSON 里带 quota / rate_limit / payment 字样。"""
    if resp.status_code == 429:
        return True
    ct = resp.headers.get("Content-Type", "")
    if "json" in ct:
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            return False
        text = json.dumps(body).lower()
        return any(k in text for k in ("quota", "rate_limit", "rate limit",
                                       "payment", "credit", "insufficient"))
    return False


def generate(prompt: str, *, model: str, width: int, height: int, seed: int,
             nologo: bool, enhance: bool, private: bool, base: str, auth: str,
             rotator: KeyRotator, retries: int, timeout: int = 180) -> tuple[bytes, str, str, str, int]:
    """
    带 key 轮换的生成调用。
    返回 (image_bytes, content_type, used_label, reproducible_url, http_status)。
    reproducible_url 不含 key（seed 固定 → 同一 URL 复现同一张图，供视觉模型复核）。
    """
    prompt_path = quote(prompt, safe="")
    # 路径：统一网关用 /image/，legacy 用 /prompt/。统一网关才真正按 model 出图。
    path_seg = "image" if "gen.pollinations.ai" in base else "prompt"
    # 给视觉模型复核用的"可复现 URL"（无 key；nologo 不影响内容）
    repro_url = (f"{base}/{path_seg}/{prompt_path}?model={quote(model)}"
                 f"&width={width}&height={height}&seed={seed}&nologo={'true' if nologo else 'false'}")

    transient = 0  # 网络 / 5xx 瞬时错误计数（独立于 429 轮换）
    quota_marks = 0  # 本轮被配额/余额耗尽的 key 计数；达到 key 总数说明账户级耗尽，直接失败
    guard = 0      # 总迭代上限，防死循环
    while True:
        guard += 1
        if guard > 200:
            raise RuntimeError("迭代上限超出，疑似无限循环")
        avail = rotator.available()
        if not avail:
            rotator.wait_for_any()
            continue
        label, key = avail[0]

        params = {"model": model, "width": width, "height": height, "seed": seed,
                  "nologo": "true" if nologo else "false",
                  "enhance": "true" if enhance else "false",
                  "private": "true" if private else "false"}
        headers = {"Accept": "image/*"}
        if auth == "query":
            params["key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"
        url = f"{base}/{path_seg}/{prompt_path}"

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as e:
            transient += 1
            if transient > retries:
                raise RuntimeError(f"网络错误重试 {retries} 次仍失败：{e}")
            wait = 2 ** transient
            print(f"  网络错误({e})，{wait}s 后重试 ({transient}/{retries})", file=sys.stderr)
            time.sleep(wait)
            continue

        # 限流 / 配额：标记冷却，切下一个 key
        if _looks_like_quota_error(resp):
            print(f"  🔄 {label} 限流/配额不足 (HTTP {resp.status_code})", file=sys.stderr)
            rotator.mark_cooling(label)
            quota_marks += 1
            # 账户级耗尽（所有 key 都因配额挂掉）：等也不会恢复，直接失败
            if quota_marks >= len(rotator.keys):
                raise RuntimeError(f"所有 key 配额/余额耗尽（HTTP {resp.status_code}）：{resp.text[:200]}")
            continue

        # 5xx：瞬时错误，退避重试（不轮换 key）
        if 500 <= resp.status_code < 600:
            transient += 1
            if transient > retries:
                raise RuntimeError(f"服务端 {resp.status_code} 重试 {retries} 次仍失败：{resp.text[:200]}")
            wait = 2 ** transient
            print(f"  HTTP {resp.status_code}，{wait}s 后重试 ({transient}/{retries})", file=sys.stderr)
            time.sleep(wait)
            continue

        # 其它 4xx：直接失败（auth 错、参数错等，换 key 也没用）
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

        ct = resp.headers.get("Content-Type", "")
        if not ct.startswith("image/"):
            # 偶尔会把错误包成 200 + JSON
            raise RuntimeError(f"非图片响应 Content-Type={ct}: {resp.text[:300]}")

        return resp.content, ct, label, repro_url, resp.status_code


def save_image(content: bytes, output: str, *, verify: bool = False) -> tuple[str, str]:
    """
    把返回字节（jpeg/png）用 PIL 打开后统一另存为 .png。
    返回 (output, actual_size)，actual_size 形如 "1024x1024"。
    """
    from PIL import Image
    import io
    with Image.open(io.BytesIO(content)) as im:
        if verify:
            im.verify()
        # verify 后对象不可再用，重新打开
        with Image.open(io.BytesIO(content)) as im2:
            w, h = im2.size
            im2.convert("RGB").save(output, format="PNG")
    if w < 1 or h < 1:
        raise RuntimeError(f"图片尺寸异常 {w}x{h}")
    return output, f"{w}x{h}"


def main():
    parser = argparse.ArgumentParser(description="Pollinations 图片模型测试 (flux/turbo)")
    parser.add_argument("--prompt", required=True, help="提示词")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型名（默认 {DEFAULT_MODEL}）")
    parser.add_argument("--size", default="1024x1024", help="输出尺寸，如 1024x1024")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42，固定以保证可复现）")
    parser.add_argument("--output", "-o", default=None, help="输出图片路径（默认 pollinations_<时间>.png）")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"API base URL（默认 {DEFAULT_BASE}）")
    parser.add_argument("--auth", choices=["header", "query"], default="header",
                        help="认证方式：header(Authorization Bearer) 或 query(?key=)。默认 header")
    parser.add_argument("--nologo", choices=["true", "false"], default="true",
                        help="去水印（需带 key）。默认 true")
    parser.add_argument("--enhance", action="store_true", help="开启 prompt 增强改写（默认关）")
    parser.add_argument("--private", action="store_true", help="不进公共信息流（默认关）")
    parser.add_argument("--api-key", default=None, help="单 key 模式（传则不轮换）")
    parser.add_argument("--cooldown", type=int, default=600,
                        help="单 key 限流后冷却秒数（默认 600，对齐小时刷新）")
    parser.add_argument("--retries", type=int, default=3, help="瞬时错误重试次数（默认 3）")
    parser.add_argument("--meta", default=None, help="把元信息写到这个 JSON 文件")
    parser.add_argument("--verify", action="store_true", help="下载后用 PIL.verify() 校验完整性")
    parser.add_argument("--json", action="store_true", help="结构化输出（供编排器解析）")
    args = parser.parse_args()

    try:
        w, h = (int(x) for x in args.size.lower().split("x"))
    except Exception:
        sys.exit(f"错误：--size 格式应为 WxH，如 1024x1024，收到 {args.size}")

    keys = load_keys(args.api_key)
    rotator = KeyRotator(keys, args.cooldown)
    output = args.output or f"pollinations_{time.strftime('%Y%m%d_%H%M%S')}.png"
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    content, ct, used_label, repro_url, http_status = generate(
        args.prompt, model=args.model, width=w, height=h, seed=args.seed,
        nologo=(args.nologo == "true"), enhance=args.enhance, private=args.private,
        base=args.base, auth=args.auth, rotator=rotator, retries=args.retries,
    )
    _, actual_size = save_image(content, output, verify=args.verify)
    elapsed = time.time() - started
    size_note = ("请求尺寸与实际一致" if actual_size == args.size
                 else f"请求 {args.size} 但实际输出 {actual_size}（缩水/放大）")
    print(f"已保存：{output}（{args.model} · {elapsed:.1f}s · 实际 {actual_size} · key={used_label}）",
          file=sys.stderr)

    meta = {
        "provider": "pollinations",
        "model": args.model,
        "prompt": args.prompt,
        "requested_size": args.size,
        "actual_size": actual_size,
        "size_note": size_note,
        "seed": args.seed,
        "nologo": args.nologo == "true",
        "enhance": args.enhance,
        "image_url": repro_url,
        "key_used": used_label,
        "content_type": ct,
        "http_status": http_status,
        "endpoint": args.base,
        "elapsed_seconds": round(elapsed, 2),
    }
    if args.meta:
        with open(args.meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"元信息已保存：{args.meta}", file=sys.stderr)
    if args.json:
        meta["output_path"] = str(Path(output).resolve())
        print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()

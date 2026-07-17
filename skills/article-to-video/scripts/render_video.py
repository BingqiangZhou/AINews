#!/usr/bin/env python3
"""
render_video.py — 阶段 4：用 hyperframes CLI 渲染视频

对 _video/hyperframes_project/ 跑：
  1. npx hyperframes lint   （静态校验，快）
  2. npx hyperframes check  （浏览器运行时校验，关卡）
  3. npx hyperframes render --quality <q> --output <公众号_视频.mp4>

lint/check 若有 error 则中止（warning 可接受，继续）。
render 用本地 Chrome headless 逐帧渲染（零云成本）。

Usage:
  python render_video.py --article-dir <文章目录> [--quality draft|standard|high] [--skip-check]

质量档位：
  draft    快速预览（低分辨率/低码率，迭代用）
  standard 标准发布
  high     最高质量（慢，发布精品用）
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import setup_windows_encoding  # noqa: E402

NPX = shutil.which("npx") or "npx"
# 固定版本，避免 npx 每次拉新版（doctor 报 0.7.61 latest）
HF_CMD = [NPX, "hyperframes"]


def _resolve_cache_dir(article_dir: Path) -> str:
    """hyperframes 渲染缓存目录。

    渲染逐帧 PNG 需大量临时空间（11 分钟视频可达数 GB）。
    优先用文章目录同盘的 .hf-cache（通常是数据盘，空间足）；
    避免用系统盘 Temp（Windows C: 常空间不足导致渲染中断）。
    """
    # 文章目录的盘符根 + .hf-cache（与文章同盘，空间通常充足）
    drive = article_dir.anchor  # 如 "/" 或 "\\"
    parts = article_dir.parts
    if len(parts) >= 2:
        # Windows: E:/Projects/... → E:/；POSIX: /home/... → /
        root = Path(parts[0]) if parts[0].endswith(":") else Path("/")
    else:
        root = Path("/")
    cache = root / ".hf-cache"
    cache.mkdir(parents=True, exist_ok=True)
    return str(cache)


def run(cmd: list[str], cwd: Path, check_errors: bool = True) -> tuple[int, str]:
    """运行命令，返回 (exit_code, output)。非 TTY 自动非交互。"""
    print(f"  $ {' '.join(cmd)}  (cwd: {cwd.name})")
    result = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=1800,
    )
    out = (result.stdout or "") + (result.stderr or "")
    # 截断显示
    tail = out[-1500:] if len(out) > 1500 else out
    print(tail)
    return result.returncode, out


def parse_findings(output: str) -> tuple[int, int]:
    """从 check/lint 输出解析 error/warning 计数。

    hyperframes 输出形如 '◇  0 error(s), 4 warning(s), 0 info(s)' 或 'Check failed'。
    """
    import re
    errs = warnings = 0
    for m in re.finditer(r"(\d+)\s*error\(s\),\s*(\d+)\s*warning\(s\)", output):
        errs = max(errs, int(m.group(1)))
        warnings = max(warnings, int(m.group(2)))
    return errs, warnings


def main():
    setup_windows_encoding()
    ap = argparse.ArgumentParser(description="阶段 4：hyperframes 渲染视频")
    ap.add_argument("--article-dir", required=True, help="文章目录")
    ap.add_argument("--quality", default="standard",
                    choices=["draft", "standard", "high"],
                    help="渲染质量（draft 快/standard 标准/high 精品）")
    ap.add_argument("--skip-check", action="store_true",
                    help="跳过 lint+check，直接 render（迭代时省时）")
    ap.add_argument("--snapshot-only", action="store_true",
                    help="只跑 snapshot 抽帧，不渲染（快速看效果）")
    args = ap.parse_args()

    article_dir = Path(args.article_dir).resolve()
    project_dir = article_dir / "_video" / "hyperframes_project"
    if not project_dir.exists() or not (project_dir / "index.html").exists():
        print(f"ERROR: hyperframes 项目不存在: {project_dir}", file=sys.stderr)
        print("请先运行 build_composition.py", file=sys.stderr)
        sys.exit(1)

    # ── 1. lint + check（除非 --skip-check）──
    if not args.skip_check:
        print("\n=== 阶段 4a: lint ===")
        rc, out = run(HF_CMD + ["lint"], project_dir)
        errs, warns = parse_findings(out)
        if rc != 0 or errs > 0:
            print(f"\n❌ lint 失败（{errs} error）。修复后再渲染。", file=sys.stderr)
            sys.exit(1)
        print(f"✓ lint 通过（{errs} error, {warns} warning）")

        print("\n=== 阶段 4b: check（浏览器关卡） ===")
        rc, out = run(HF_CMD + ["check"], project_dir)
        errs, warns = parse_findings(out)
        if rc != 0 or errs > 0 or "Check failed" in out:
            print(f"\n❌ check 失败（{errs} error）。修复后再渲染。", file=sys.stderr)
            sys.exit(1)
        print(f"✓ check 通过（{errs} error, {warns} warning）")
    else:
        print("  (--skip-check: 跳过 lint+check)")

    # ── 2. snapshot 抽帧（可选，快速看效果）──
    if args.snapshot_only:
        print("\n=== snapshot 抽帧 ===")
        # 取每 60s 一帧 + 几个 section 起点
        run(HF_CMD + ["snapshot", "--frames", "11"], project_dir)
        snap_dir = project_dir / "snapshots"
        if snap_dir.exists():
            frames = sorted(snap_dir.glob("*.png"))
            print(f"\n✓ 生成 {len(frames)} 帧快照: {snap_dir}")
        return

    # ── 3. render ──
    output_path = article_dir / "_video" / "公众号_视频.mp4"
    # 先备份旧视频（若有）
    if output_path.exists():
        import datetime
        bak = output_path.with_suffix(
            f".bak-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
        )
        shutil.move(str(output_path), str(bak))
        print(f"  旧视频备份: {bak.name}")

    # hyperframes 渲染缓存目录（避免系统盘 Temp 空间不足导致渲染中断）
    cache_dir = _resolve_cache_dir(article_dir)
    print(f"\n=== 阶段 4c: render (quality={args.quality}) ===")
    print(f"  本地 Chrome headless 渲染，约 11 分钟视频预计耗时 20-40 分钟...")
    print(f"  帧缓存目录: {cache_dir}（避免系统盘 Temp 耗尽）")

    # 设置环境变量：渲染临时空间重定向到文章同盘
    env = os.environ.copy()
    env["HYPERFRAMES_EXTRACT_CACHE_DIR"] = cache_dir
    # TMP/TEMP 也指向同盘（部分中间件读这两个）
    tmp_dir = Path(cache_dir).parent / ".hf-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    env["TMP"] = str(tmp_dir)
    env["TEMP"] = str(tmp_dir)

    cmd = HF_CMD + [
        "render", "--quality", args.quality,
        "--output", str(output_path),
        "--frames-cache-dir", cache_dir,
    ]
    print(f"  $ {' '.join(cmd[:2])} ... --frames-cache-dir {cache_dir}")
    result = subprocess.run(
        cmd, cwd=str(project_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=3600,
    )
    out = (result.stdout or "") + (result.stderr or "")
    print(out[-2000:] if len(out) > 2000 else out)
    rc = result.returncode
    if rc != 0:
        print(f"\n❌ render 失败 (exit {rc})", file=sys.stderr)
        sys.exit(1)

    if not output_path.exists() or output_path.stat().st_size == 0:
        print(f"\n❌ render 未产出视频文件: {output_path}", file=sys.stderr)
        sys.exit(1)

    # ffprobe 校验
    import os
    ffprobe = os.environ.get("AINews_FFPROBE") or "ffprobe"
    try:
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_name,codec_type,width,height:format=duration,size",
             "-of", "default", str(output_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        info = probe.stdout
        has_video = "codec_type=video" in info
        has_audio = "codec_type=audio" in info
        import re
        dur_m = re.search(r"duration=(\d+\.?\d*)", info)
        dur = float(dur_m.group(1)) if dur_m else 0
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ 视频渲染完成: {output_path}")
        print(f"   video={has_video} audio={has_audio} duration={dur:.1f}s size={size_mb:.1f}MB")
        if not (has_video and has_audio):
            print(f"   WARNING: 缺少 video 或 audio 流", file=sys.stderr)
    except Exception as e:
        print(f"\n✅ 视频渲染完成（ffprobe 校验跳过: {e}）: {output_path}")


if __name__ == "__main__":
    main()

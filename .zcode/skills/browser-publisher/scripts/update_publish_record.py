"""发布记录写入工具 — 合并更新某篇文章的 publish.json。

每篇文章目录下一份 publish.json，记录该文章在各平台的发布状态。
本工具幂等地合并单个平台 track（保留其它平台不动），原子写回。

用法:
  python update_publish_record.py \
      --article-dir "articles/2026-07-12_xxx" \
      --platform wechat_mp \
      --status published \
      --url "https://mp.weixin.qq.com/s/..." \
      --media-id "MEDIA_ID"        # 公众号专用，可选
      --episode 251                # 喜马拉雅专用，可选
      --error "上传超时"            # failed 时用，可选

约定见 references/publish-record.md。schema: publish-record-v1。
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCHEMA_VERSION = "publish-record-v1"

# 平台内部名（与 SKILL.md「支持平台」表一致，不用编排器别名）
PLATFORMS = ("wechat_mp", "ximalaya", "douyin", "xiaohongshu", "wechat_channels")

# status 枚举
STATUSES = ("draft", "published", "scheduled", "failed", "skipped")

# 北京时区（本机内容生产默认时区，published_at 用它）
_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    """当前时间，ISO 8601 带时区（CST）。"""
    return datetime.now(_CST).isoformat(timespec="seconds")


def _validate(platform: str, status: str) -> None:
    if platform not in PLATFORMS:
        raise ValueError(
            f"非法 platform {platform!r}，合法值: {', '.join(PLATFORMS)}"
        )
    if status not in STATUSES:
        raise ValueError(
            f"非法 status {status!r}，合法值: {', '.join(STATUSES)}"
        )


def load_record(article_dir: Path) -> dict:
    """读现有 publish.json；不存在或损坏返回空骨架。"""
    path = article_dir / "publish.json"
    skeleton = {
        "schema_version": SCHEMA_VERSION,
        "article_dir": _rel_article_dir(article_dir),
        "tracks": {},
        "updated_at": None,
    }
    if not path.exists():
        return skeleton
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 损坏文件不静默吞，但给出可恢复的骨架（调用方决定是否覆盖）
        print(f"[warn] publish.json 解析失败，将重建骨架: {path}", file=sys.stderr)
        return skeleton
    # 兼容性补全（缺字段时填默认）
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("article_dir", _rel_article_dir(article_dir))
    data.setdefault("tracks", {})
    data.setdefault("updated_at", None)
    return data


def _rel_article_dir(article_dir: Path) -> str:
    """把绝对路径转成仓库相对（articles/...）；转不了就用原样字符串。"""
    s = str(article_dir).replace("\\", "/")
    idx = s.find("/articles/")
    if idx != -1:
        return s[idx + 1:]  # 含开头的 articles/
    return s


def build_track(
    status: str,
    url: str | None,
    media_id: str | None,
    episode: int | None,
    error: str | None,
) -> dict:
    """构造单个平台的 track dict（按平台语义选填字段）。"""
    track = {"status": status}
    if url:
        track["url"] = url
    if media_id:
        track["media_id"] = media_id
    if episode is not None:
        track["episode"] = episode
    if status == "failed":
        track["error"] = error or "unknown"
    track["published_at"] = _now_iso()
    return track


def update_record(
    article_dir: Path,
    platform: str,
    status: str,
    url: str | None = None,
    media_id: str | None = None,
    episode: int | None = None,
    error: str | None = None,
) -> dict:
    """合并更新某平台的 track，返回写回后的完整 record。

    幂等：只覆盖指定 platform 的 track，其它平台 track 保留。
    """
    _validate(platform, status)
    record = load_record(article_dir)
    record["tracks"][platform] = build_track(
        status, url, media_id, episode, error
    )
    record["updated_at"] = _now_iso()
    write_record(article_dir, record)
    return record


def write_record(article_dir: Path, record: dict) -> None:
    """原子写 publish.json（先写 .tmp 再 rename，避免半截文件）。"""
    article_dir.mkdir(parents=True, exist_ok=True)
    path = article_dir / "publish.json"
    # ensure_ascii=False 保留中文；indent=2 便于人读和 git diff（虽不进 git）
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    # tempfile 和目标同目录，保证 rename 是原子的（同卷）
    fd, tmp_path = tempfile.mkstemp(
        prefix=".publish.", suffix=".tmp", dir=str(article_dir)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(payload)
        os.replace(tmp_path, path)
    except BaseException:
        # 写失败要清理 tmp，不留垃圾
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="合并更新某篇文章的 publish.json 发布记录"
    )
    p.add_argument("--article-dir", required=True, help="文章目录绝对/相对路径")
    p.add_argument("--platform", required=True, help=f"平台内部名: {', '.join(PLATFORMS)}")
    p.add_argument(
        "--status", required=True, help=f"状态: {', '.join(STATUSES)}"
    )
    p.add_argument("--url", default=None, help="发布结果页 URL")
    p.add_argument("--media-id", default=None, help="公众号 media_id")
    p.add_argument("--episode", type=int, default=None, help="喜马拉雅集号")
    p.add_argument("--error", default=None, help="失败原因（failed 时用）")
    args = p.parse_args(argv)

    try:
        record = update_record(
            Path(args.article_dir),
            args.platform,
            args.status,
            url=args.url,
            media_id=args.media_id,
            episode=args.episode,
            error=args.error,
        )
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2

    out = Path(args.article_dir) / "publish.json"
    print(f"[ok] wrote {out}", file=sys.stderr)
    print(json.dumps(record["tracks"][args.platform], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

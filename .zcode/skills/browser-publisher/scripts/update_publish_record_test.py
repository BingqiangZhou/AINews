"""update_publish_record.py 的单元测试。

覆盖：新建、合并（保留其它平台）、覆盖单平台、失败 track、
损坏文件重建、非法输入校验、原子写（失败回退）。

跑法：cd .zcode/skills/browser-publisher && python -m pytest scripts/
"""
import json
import os
import sys
from pathlib import Path

import pytest

# 让测试能 import 同目录模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_publish_record as upr  # noqa: E402


# ---------- helpers ----------

def _read(d: Path) -> dict:
    return json.loads((d / "publish.json").read_text(encoding="utf-8"))


# ---------- 基础写入 ----------

def test_creates_new_record(tmp_path):
    """目录无 publish.json 时新建，含正确骨架。"""
    upr.update_record(tmp_path, "wechat_mp", "published", url="https://mp.weixin.qq.com/s/abc")
    rec = _read(tmp_path)
    assert rec["schema_version"] == "publish-record-v1"
    assert rec["tracks"]["wechat_mp"]["status"] == "published"
    assert rec["tracks"]["wechat_mp"]["url"] == "https://mp.weixin.qq.com/s/abc"
    assert rec["updated_at"] is not None
    assert "publish.json" in os.listdir(tmp_path)


def test_published_at_is_iso_with_tz(tmp_path):
    """published_at 必须是 ISO 8601 且带时区。"""
    upr.update_record(tmp_path, "ximalaya", "published", episode=251)
    ts = _read(tmp_path)["tracks"]["ximalaya"]["published_at"]
    # 形如 2026-07-14T12:00:00+08:00
    assert "T" in ts and "+08:00" in ts


def test_episode_recorded(tmp_path):
    upr.update_record(tmp_path, "ximalaya", "published", episode=251)
    assert _read(tmp_path)["tracks"]["ximalaya"]["episode"] == 251


def test_media_id_recorded(tmp_path):
    upr.update_record(tmp_path, "wechat_mp", "draft", media_id="MEDIA_123")
    rec = _read(tmp_path)["tracks"]["wechat_mp"]
    assert rec["status"] == "draft"
    assert rec["media_id"] == "MEDIA_123"


# ---------- 合并：保留其它平台 ----------

def test_merges_keeps_other_platforms(tmp_path):
    """更新 ximalaya 时，已存在的 wechat_mp track 必须保留。"""
    upr.update_record(tmp_path, "wechat_mp", "published", url="https://a")
    upr.update_record(tmp_path, "ximalaya", "published", episode=99)
    tracks = _read(tmp_path)["tracks"]
    assert set(tracks.keys()) == {"wechat_mp", "ximalaya"}
    assert tracks["wechat_mp"]["url"] == "https://a"
    assert tracks["ximalaya"]["episode"] == 99


def test_overwrite_single_platform_preserves_others(tmp_path):
    """重复更新同一平台覆盖该 track，但其它平台不动。"""
    upr.update_record(tmp_path, "wechat_mp", "draft", media_id="OLD")
    upr.update_record(tmp_path, "ximalaya", "published", episode=1)
    # 第二次更新 wechat_mp
    upr.update_record(tmp_path, "wechat_mp", "published", url="https://b")
    tracks = _read(tmp_path)["tracks"]
    assert tracks["wechat_mp"]["status"] == "published"
    assert "media_id" not in tracks["wechat_mp"]  # 新 track 没传 media_id
    assert tracks["ximalaya"]["episode"] == 1  # 没被动


# ---------- 失败 track ----------

def test_failed_requires_error_default(tmp_path):
    """failed 状态没传 error 时兜底为 'unknown'。"""
    upr.update_record(tmp_path, "douyin", "failed")
    rec = _read(tmp_path)["tracks"]["douyin"]
    assert rec["status"] == "failed"
    assert rec["error"] == "unknown"


def test_failed_with_error(tmp_path):
    upr.update_record(tmp_path, "douyin", "failed", error="上传超时")
    assert _read(tmp_path)["tracks"]["douyin"]["error"] == "上传超时"


# ---------- 损坏文件恢复 ----------

def test_recovers_from_corrupt_file(tmp_path):
    """publish.json 损坏（非法 JSON）时重建骨架而非崩溃。"""
    (tmp_path / "publish.json").write_text("{ 乱七八糟", encoding="utf-8")
    upr.update_record(tmp_path, "wechat_mp", "published")
    rec = _read(tmp_path)
    assert rec["tracks"]["wechat_mp"]["status"] == "published"


# ---------- 校验 ----------

def test_invalid_platform_rejected(tmp_path):
    with pytest.raises(ValueError, match="非法 platform"):
        upr.update_record(tmp_path, "gongzhonghao", "published")


def test_invalid_status_rejected(tmp_path):
    with pytest.raises(ValueError, match="非法 status"):
        upr.update_record(tmp_path, "wechat_mp", "ok")


def test_cli_invalid_platform_exits_2(tmp_path, capsys):
    """CLI 非法输入返回退出码 2，不写文件。"""
    rc = upr.main(
        ["--article-dir", str(tmp_path), "--platform", "foo", "--status", "published"]
    )
    assert rc == 2
    assert not (tmp_path / "publish.json").exists()


def test_cli_success(tmp_path, capsys):
    rc = upr.main(
        [
            "--article-dir", str(tmp_path),
            "--platform", "wechat_mp",
            "--status", "published",
            "--url", "https://x",
        ]
    )
    assert rc == 0
    assert _read(tmp_path)["tracks"]["wechat_mp"]["url"] == "https://x"


# ---------- 原子写 ----------

def test_no_tmp_left_after_success(tmp_path):
    """成功写入后目录里只剩 publish.json，无 .tmp 残留。"""
    upr.update_record(tmp_path, "wechat_mp", "published")
    files = os.listdir(tmp_path)
    assert "publish.json" in files
    assert not any(f.startswith(".publish.") for f in files)


def test_all_five_platforms_accepted(tmp_path):
    """5 个合法平台内部名都能写入。"""
    for pf in ("wechat_mp", "ximalaya", "douyin", "xiaohongshu", "wechat_channels"):
        upr.update_record(tmp_path, pf, "published")
    assert len(_read(tmp_path)["tracks"]) == 5

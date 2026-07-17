#!/usr/bin/env python3
"""
test_resolve_podcast.py — resolve_podcast_path 的单元测试

覆盖 article-to-video 对播客产物路径的解析：
  - _podcast/ 子目录存在（canonical，article-to-duo-podcast 输出位）
  - 仅根目录存在（向后兼容）
  - 两者都缺（返回 _podcast/ canonical 路径用于报错）
  - 两者都在（优先 _podcast/）

无外部依赖，纯 tmp_path fixture。
"""

import sys
from pathlib import Path

# 让本测试文件能 import lib.utils（scripts/ 加入 sys.path）
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.utils import resolve_podcast_path  # noqa: E402

FILENAME = "播客_TTS.mp3"


def test_prefers_podcast_subdir(tmp_path):
    """_podcast/ 存在 → 返回 _podcast/ 下的路径。"""
    podcast_dir = tmp_path / "_podcast"
    podcast_dir.mkdir()
    (podcast_dir / FILENAME).write_text("audio", encoding="utf-8")

    result = resolve_podcast_path(tmp_path, FILENAME)

    assert result == podcast_dir / FILENAME
    assert result.exists()
    assert "_podcast" in result.parts


def test_falls_back_to_root(tmp_path):
    """仅根目录存在 → 返回根目录路径（向后兼容）。"""
    (tmp_path / FILENAME).write_text("audio", encoding="utf-8")
    # 不创建 _podcast/

    result = resolve_podcast_path(tmp_path, FILENAME)

    assert result == tmp_path / FILENAME
    assert result.exists()


def test_returns_podcast_canonical_when_missing(tmp_path):
    """两者都不存在 → 返回 _podcast/ canonical 路径（用于准确报错）。"""
    result = resolve_podcast_path(tmp_path, FILENAME)

    assert result == (tmp_path / "_podcast" / FILENAME).resolve()
    assert not result.exists()


def test_podcast_wins_when_both_exist(tmp_path):
    """两者都在 → 优先 _podcast/（canonical 胜过根目录兼容）。"""
    podcast_dir = tmp_path / "_podcast"
    podcast_dir.mkdir()
    (podcast_dir / FILENAME).write_text("canonical", encoding="utf-8")
    (tmp_path / FILENAME).write_text("legacy-root", encoding="utf-8")

    result = resolve_podcast_path(tmp_path, FILENAME)

    assert result == podcast_dir / FILENAME
    assert result.read_text(encoding="utf-8") == "canonical"


def test_returns_absolute_path(tmp_path):
    """结果总是绝对路径（传入相对 article_dir 也要 resolve）。"""
    podcast_dir = tmp_path / "_podcast"
    podcast_dir.mkdir()
    (podcast_dir / FILENAME).write_text("audio", encoding="utf-8")

    # 传入相对路径（切到父目录）
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path.parent)
        result = resolve_podcast_path(tmp_path.name, FILENAME)
    finally:
        os.chdir(old_cwd)

    assert result.is_absolute()
    assert result == podcast_dir / FILENAME

"""递增 boker_next_episode 并清除 episode_number_claimed。

用法:
  # 递增集号（发布成功后调用）
  python bump_episode.py --config "<config.json path>" --state "<state.json path>" --bump

  # 查看当前集号（不修改）
  python bump_episode.py --config "<config.json path>" --state "<state.json path>"

  # 强制设置为指定值（用于修正历史集号，必须 >= 1）
  python bump_episode.py --config "<config.json path>" --state "<state.json path>" --set 224
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Reuse the canonical atomic backup helper so this script honors the same
# overwrite-with-backup convention as the rest of the skill (SKILL.md).
from backup_file import backup_file


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically: render to a sibling temp file, then os.replace.

    A crash or interruption mid-write never leaves a half-written config/state
    behind. The temp file lives in the same directory so the rename stays on a
    single filesystem (atomic on Windows and POSIX).
    """
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description="管理喜马拉雅播客集号")
    parser.add_argument("--config", required=True, help="audio-to-social config.json 路径")
    parser.add_argument("--state", required=True, help="项目 state.json 路径")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--bump", action="store_true", help="发布成功后递增集号 +1")
    group.add_argument("--set", type=int, dest="set_value", help="强制设置集号为指定值（必须 >= 1）")
    args = parser.parse_args()

    config_path = Path(args.config)
    state_path = Path(args.state)

    if not config_path.exists():
        print(f"[error] config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = read_json(config_path)
    platforms = config.setdefault("platforms", {})
    current = platforms.get("boker_next_episode")

    if args.bump:
        if current is None:
            print("[error] boker_next_episode not found in config", file=sys.stderr)
            sys.exit(1)

        new_value = current + 1
        # 覆盖非 temp 文件前先备份（遵循 SKILL.md 覆盖前备份规则）
        backup_file(config_path)
        platforms["boker_next_episode"] = new_value
        write_json_atomic(config_path, config)

        # 清除 state.json 中的 episode_number_claimed
        if state_path.exists():
            state = read_json(state_path)
            # 置空而非删除键：state-schema 要求 episode_number_claimed 字段存在
            # （nullable）。pop 会删键，导致后续读取 KeyError 并破坏 schema 一致性。
            claimed = state.get("episode_number_claimed")
            if claimed is not None:
                state["episode_number_claimed"] = None
                backup_file(state_path)
                write_json_atomic(state_path, state)
                print(f"[bump] episode_number_claimed ({claimed}) cleared")
        else:
            print(f"[warn] state.json not found: {state_path}")

        print(f"[bump] boker_next_episode: {current} → {new_value}")

    elif args.set_value is not None:
        if args.set_value < 1:
            print("[error] --set value must be >= 1 (episode numbers are positive)", file=sys.stderr)
            sys.exit(1)
        old = current
        backup_file(config_path)
        platforms["boker_next_episode"] = args.set_value
        write_json_atomic(config_path, config)

        # 清除 state.json 中的 episode_number_claimed：手动修正集号后，旧的 claimed
        # 集号已失效，否则下次初始化会复用过期的 claimed 值（见 phase0 第 7 步）而非
        # 修正后的基线，削弱 claim→bump 去重协议。与 --bump 分支保持一致。
        if state_path.exists():
            state = read_json(state_path)
            # 置空而非删除键：state-schema 要求 episode_number_claimed 字段存在
            # （nullable）。pop 会删键，导致后续读取 KeyError 并破坏 schema 一致性。
            claimed = state.get("episode_number_claimed")
            if claimed is not None:
                state["episode_number_claimed"] = None
                backup_file(state_path)
                write_json_atomic(state_path, state)
                print(f"[set] episode_number_claimed ({claimed}) cleared")
        else:
            print(f"[warn] state.json not found: {state_path}")

        print(f"[set] boker_next_episode: {old} → {args.set_value}")

    else:
        # 只读模式
        claimed = None
        if state_path.exists():
            state = read_json(state_path)
            claimed = state.get("episode_number_claimed")
        print(f"[info] boker_next_episode: {current}")
        if claimed is not None:
            print(f"[info] episode_number_claimed: {claimed}")
        else:
            print(f"[info] episode_number_claimed: (none)")


if __name__ == "__main__":
    main()

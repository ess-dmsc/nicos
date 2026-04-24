"""Helpers for wiring test runtime resources into temporary roots."""

from __future__ import annotations

import shutil
from pathlib import Path


def _same_directory_tree(left: Path, right: Path) -> bool:
    if not right.is_dir():
        return False
    left_entries = sorted(path.relative_to(left) for path in left.rglob("*"))
    right_entries = sorted(path.relative_to(right) for path in right.rglob("*"))
    if left_entries != right_entries:
        return False
    for relpath in left_entries:
        left_path = left / relpath
        right_path = right / relpath
        if left_path.is_dir() != right_path.is_dir():
            return False
        if left_path.is_file() != right_path.is_file():
            return False
        if left_path.is_file() and left_path.read_bytes() != right_path.read_bytes():
            return False
    return True


def ensure_runtime_resources(src: str | Path, dst: str | Path) -> None:
    src_path = Path(src).resolve()
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.is_symlink():
        try:
            resolved_dst = dst_path.resolve(strict=True)
        except FileNotFoundError:
            dst_path.unlink()
        else:
            if resolved_dst == src_path:
                return
            dst_path.unlink()
    elif dst_path.exists():
        if _same_directory_tree(src_path, dst_path):
            return
        message = (
            "runtime resource destination already exists and is not a symlink: "
            f"{dst_path}"
        )
        raise FileExistsError(
            message
        )

    try:
        dst_path.symlink_to(src_path, target_is_directory=True)
    except OSError:
        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

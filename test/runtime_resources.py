"""Helpers for wiring test runtime resources into temporary roots."""

from __future__ import annotations

import shutil
from pathlib import Path


def ensure_runtime_resources(src: str | Path, dst: str | Path) -> None:
    src_path = Path(src).resolve()
    dst_path = Path(dst)

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
        raise FileExistsError(
            f"runtime resource destination already exists and is not a symlink: {dst_path}"
        )

    try:
        dst_path.symlink_to(src_path, target_is_directory=True)
    except OSError:
        shutil.copytree(src_path, dst_path)

"""Helpers for wiring test runtime resources into temporary roots."""

from __future__ import annotations

import shutil
from pathlib import Path


def ensure_runtime_resources(src: str | Path, dst: str | Path) -> None:
    src_path = Path(src).resolve()
    dst_path = Path(dst)

    if dst_path.is_symlink():
        if dst_path.resolve() == src_path:
            return
        dst_path.unlink()
    elif dst_path.exists():
        return

    try:
        dst_path.symlink_to(src_path, target_is_directory=True)
    except OSError:
        shutil.copytree(src_path, dst_path)

"""Helpers for wiring test runtime resources into temporary roots."""

from __future__ import annotations

import shutil
from pathlib import Path


def link_or_copy_runtime_resources(src: str | Path, dst: str | Path) -> None:
    """Wire runtime resources with a symlink, falling back to a fresh copy.

    Existing destinations are replaced unless they are already the correct
    symlink, so stale copied resources or stale symlinks cannot hide source
    changes between test sessions.

    This is a pragmatic bridge for tests while GUI code still resolves assets
    through ``config.nicos_root/resources``. If the resources package later
    exposes a stable importlib.resources-style API, this filesystem wiring can
    be refactored away.
    """
    src_path = Path(src).resolve()
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.is_symlink():
        if dst_path.resolve(strict=False) == src_path:
            return
        dst_path.unlink()
    elif dst_path.exists():
        if dst_path.is_dir():
            shutil.rmtree(dst_path)
        else:
            dst_path.unlink()

    try:
        dst_path.symlink_to(src_path, target_is_directory=True)
    except OSError:
        shutil.copytree(src_path, dst_path)

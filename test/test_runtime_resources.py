from pathlib import Path

import pytest

from test.runtime_resources import ensure_runtime_resources


def test_ensure_runtime_resources_repairs_stale_symlink(tmp_path):
    src = tmp_path / "resources"
    stale = tmp_path / "stale"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    stale.mkdir()
    dst.symlink_to(stale, target_is_directory=True)

    ensure_runtime_resources(src, dst)

    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_ensure_runtime_resources_repairs_broken_symlink(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    dst.symlink_to(tmp_path / "missing", target_is_directory=True)

    ensure_runtime_resources(src, dst)

    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_ensure_runtime_resources_rejects_existing_directory(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    dst.mkdir()
    marker = dst / "marker.txt"
    marker.write_text("keep me")

    with pytest.raises(FileExistsError, match="already exists and is not a symlink"):
        ensure_runtime_resources(src, dst)

    assert dst.is_dir()
    assert not dst.is_symlink()
    assert marker.read_text() == "keep me"


def test_ensure_runtime_resources_creates_missing_parent(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "missing-parent" / "runtime-resources"

    src.mkdir()
    (src / "marker.txt").write_text("resource")

    ensure_runtime_resources(src, dst)

    assert dst.parent.is_dir()
    assert (dst / "marker.txt").read_text() == "resource"


def test_ensure_runtime_resources_reuses_repeated_copy_fallback(tmp_path, monkeypatch):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    (src / "marker.txt").write_text("resource")

    def fail_symlink(*args, **kwargs):
        raise OSError("symlinks unavailable")

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)

    ensure_runtime_resources(src, dst)
    ensure_runtime_resources(src, dst)

    assert not dst.is_symlink()
    assert (dst / "marker.txt").read_text() == "resource"

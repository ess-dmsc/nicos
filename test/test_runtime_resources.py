"""Tests for runtime resource symlink/copy wiring."""

from pathlib import Path

from test.runtime_resources import link_or_copy_runtime_resources


def test_link_or_copy_runtime_resources_repairs_stale_symlink(tmp_path):
    src = tmp_path / "resources"
    stale = tmp_path / "stale"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    stale.mkdir()
    dst.symlink_to(stale, target_is_directory=True)

    link_or_copy_runtime_resources(src, dst)

    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_link_or_copy_runtime_resources_repairs_broken_symlink(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    dst.symlink_to(tmp_path / "missing", target_is_directory=True)

    link_or_copy_runtime_resources(src, dst)

    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_link_or_copy_runtime_resources_refreshes_existing_directory(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    (src / "resource.txt").write_text("fresh")
    dst.mkdir()
    marker = dst / "marker.txt"
    marker.write_text("stale")

    link_or_copy_runtime_resources(src, dst)

    assert dst.is_dir()
    assert (dst / "resource.txt").read_text() == "fresh"
    assert not marker.exists()


def test_link_or_copy_runtime_resources_creates_missing_parent(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "missing-parent" / "runtime-resources"

    src.mkdir()
    (src / "marker.txt").write_text("resource")

    link_or_copy_runtime_resources(src, dst)

    assert dst.parent.is_dir()
    assert (dst / "marker.txt").read_text() == "resource"


def test_link_or_copy_runtime_resources_reuses_repeated_copy_fallback(
    tmp_path, monkeypatch
):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    (src / "marker.txt").write_text("resource")

    def fail_symlink(*args, **kwargs):
        raise OSError("symlinks unavailable")

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)

    link_or_copy_runtime_resources(src, dst)
    link_or_copy_runtime_resources(src, dst)

    assert not dst.is_symlink()
    assert (dst / "marker.txt").read_text() == "resource"

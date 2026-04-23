from pathlib import Path

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


def test_ensure_runtime_resources_keeps_existing_directory(tmp_path):
    src = tmp_path / "resources"
    dst = tmp_path / "runtime-resources"

    src.mkdir()
    dst.mkdir()
    marker = dst / "marker.txt"
    marker.write_text("keep me")

    ensure_runtime_resources(src, dst)

    assert dst.is_dir()
    assert not dst.is_symlink()
    assert marker.read_text() == "keep me"

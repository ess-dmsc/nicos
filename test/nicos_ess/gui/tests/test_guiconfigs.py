from pathlib import Path

import pytest

import nicos_ess
from nicos.clients.gui.config import processGuiConfig

ess_root = Path(nicos_ess.__file__).resolve().parent
guiconfig_paths = list(ess_root.rglob("guiconfig.py"))


@pytest.mark.parametrize(
    "path", guiconfig_paths, ids=lambda path: path.relative_to(ess_root).as_posix()
)
def test_guiconfig_contains_mainwindow_and_uses_ess_mainwindow_class(path):
    source = path.read_text(encoding="utf-8")
    config = processGuiConfig(compile(source, str(path), "exec"))
    assert config.options["mainwindow_class"] == "nicos_ess.gui.mainwindow.MainWindow"

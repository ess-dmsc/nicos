"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests use file-based guiconfigs under
``test/nicos_ess/gui/guiconfigs`` and default to ``base.py`` unless a module
selects a more specific panel or layout config.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.utils import importString
from nicos.utils.loggers import NicosLogger

from test.nicos_ess.gui.doubles import FakeClientTransport, FakeDaemon


GUICONFIGS_DIR = Path(__file__).with_name("guiconfigs").resolve()
TEST_ROOT = Path(__file__).resolve().parents[2] / "root"
RESOURCES_DIR = Path(__file__).resolve().parents[3] / "resources"
_IGNORED_QT_MESSAGE_PATTERNS = (
    r"^QObject::connect: No such signal "
    r"QPlatformNativeInterface::systemTrayWindowChanged\(QScreen\*\)$",
    r"^This plugin does not support propagateSizeHints\(\)$",
)
_ORIGINAL_QT_QPA_PLATFORM = None


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    global _ORIGINAL_QT_QPA_PLATFORM
    _ORIGINAL_QT_QPA_PLATFORM = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    for pattern in _IGNORED_QT_MESSAGE_PATTERNS:
        config.addinivalue_line("qt_log_ignore", pattern)


def pytest_unconfigure(config):
    del config
    if _ORIGINAL_QT_QPA_PLATFORM is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ["QT_QPA_PLATFORM"] = _ORIGINAL_QT_QPA_PLATFORM


def _resolve_guiconfig_path(guiconfig_name: str) -> Path:
    if not isinstance(guiconfig_name, str) or not guiconfig_name:
        raise ValueError(
            "GUI test guiconfig_name must be a non-empty relative path, "
            "for example 'panels/devices.py'"
        )
    guiconfig_path = (GUICONFIGS_DIR / guiconfig_name).resolve()
    if not guiconfig_path.is_file():
        raise FileNotFoundError(
            f"GUI test guiconfig not found: {guiconfig_name!r} -> {guiconfig_path}"
        )
    return guiconfig_path


@pytest.fixture
def fake_daemon():
    return FakeDaemon()


@pytest.fixture(scope="session", autouse=True)
def gui_runtime_resources():
    dst = TEST_ROOT / "resources"
    if dst.exists() or dst.is_symlink():
        return
    try:
        dst.symlink_to(RESOURCES_DIR, target_is_directory=True)
    except OSError:
        shutil.copytree(RESOURCES_DIR, dst)


@pytest.fixture(autouse=True)
def assert_fake_daemon_contract(fake_daemon):
    yield
    assert fake_daemon.unknown_evals == []


@pytest.fixture
def guiconfig_name(request):
    return getattr(request.module, "guiconfig_name", "base.py")


@pytest.fixture
def panel_name(request):
    return getattr(request.module, "panel_name", None)


@pytest.fixture
def guiconfig_path(guiconfig_name):
    return _resolve_guiconfig_path(guiconfig_name)


@pytest.fixture
def gui_window_factory(monkeypatch, qtbot, fake_daemon):
    from nicos.guisupport.qt import QApplication

    windows = []

    def _build(*, guiconfig_path):
        if guiconfig_path is None:
            raise ValueError("pass guiconfig_path to gui_window_factory()")

        monkeypatch.setattr(
            "nicos.clients.base.ClientTransport",
            lambda: FakeClientTransport(fake_daemon),
        )

        config_source = Path(guiconfig_path).read_text()
        config = processGuiConfig(config_source.strip())
        # Keep GUI tests independent from optional stylesheet/resource lookup.
        config.stylefile = ""

        mainwindow_cls = importString(config.options["mainwindow_class"])
        window = mainwindow_cls(NicosLogger("mainwindow"), config)
        window.autoconnect = False
        window.confirmexit = False

        window.show()
        qtbot.waitUntil(lambda w=window: w.isVisible(), timeout=2000)

        window.client.connect(ConnectionData("fake", 0, "test", "test"))
        qtbot.waitUntil(lambda w=window: w.client.isconnected, timeout=2000)

        windows.append(window)
        return window

    yield _build

    for window in windows:
        if window.client.isconnected:
            window.client.disconnect()
            qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
        thread = getattr(window.client, "event_thread", None)
        if thread is not None:
            thread.join(timeout=1.0)
            assert not thread.is_alive()
        # The real MainWindow.closeEvent() quits the shared QApplication,
        # which breaks subsequent pytest-qt tests in the same session.
        window.hide()
        window.deleteLater()

    QApplication.processEvents()


@pytest.fixture
def gui_window(gui_window_factory, guiconfig_path):
    return gui_window_factory(guiconfig_path=guiconfig_path)


@pytest.fixture
def gui_window_from_name(gui_window_factory):
    def _build(guiconfig_name):
        return gui_window_factory(guiconfig_path=_resolve_guiconfig_path(guiconfig_name))

    return _build


@pytest.fixture
def gui_panel(gui_window, panel_name, guiconfig_name):
    if panel_name is None:
        raise ValueError(
            "gui_panel requires module-level panel_name, "
            f"for example in tests using {guiconfig_name!r}"
        )
    panel = gui_window.getPanel(panel_name)
    if panel is None:
        raise LookupError(
            f"panel {panel_name!r} not found in GUI test config {guiconfig_name!r}"
        )
    return panel

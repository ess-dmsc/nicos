"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests must provide their GUI config
explicitly so missing or ambiguous configuration fails immediately.
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
        raise ValueError("set module-level guiconfig_name = 'devices.py' for GUI tests")
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
    name = getattr(request.module, "guiconfig_name", None)
    if name is None:
        raise ValueError(
            f"{request.module.__name__} must define module-level guiconfig_name"
        )
    return name


@pytest.fixture
def guiconfig_path(guiconfig_name):
    return _resolve_guiconfig_path(guiconfig_name)


@pytest.fixture
def gui_window_factory(monkeypatch, qtbot, fake_daemon):
    from nicos.guisupport.qt import QApplication

    windows = []

    def _build(*, config_text=None, guiconfig_path=None):
        if (config_text is None) == (guiconfig_path is None):
            raise ValueError(
                "pass exactly one of config_text or guiconfig_path to gui_window_factory()"
            )

        monkeypatch.setattr(
            "nicos.clients.base.ClientTransport",
            lambda: FakeClientTransport(fake_daemon),
        )

        config_source = config_text
        if config_source is None:
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
def devices_panel(gui_window):
    return gui_window.getPanel("Devices")

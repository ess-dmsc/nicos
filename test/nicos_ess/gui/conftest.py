"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests must provide their GUI config
explicitly so missing or ambiguous configuration fails immediately.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("pytestqt")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.utils import importString
from nicos.utils.loggers import NicosLogger

from test.nicos_ess.gui.doubles import FakeClientTransport, FakeDaemon


GUICONFIGS_DIR = Path(__file__).with_name("guiconfigs").resolve()


def _resolve_guiconfig_path(guiconfig_name: str) -> Path:
    if not isinstance(guiconfig_name, str) or not guiconfig_name:
        raise ValueError("set module-level guiconfig_name = 'devices.py' for GUI tests")
    guiconfig_path = (GUICONFIGS_DIR / guiconfig_name).resolve()
    try:
        guiconfig_path.relative_to(GUICONFIGS_DIR)
    except ValueError as err:
        raise ValueError(
            f"guiconfig_name must resolve inside {GUICONFIGS_DIR}: {guiconfig_name!r}"
        ) from err
    if not guiconfig_path.is_file():
        raise FileNotFoundError(
            f"GUI test guiconfig not found: {guiconfig_name!r} -> {guiconfig_path}"
        )
    return guiconfig_path


@pytest.fixture
def fake_daemon():
    return FakeDaemon()


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
        config.stylefile = ""

        mainwindow_cls = importString(config.options["mainwindow_class"])
        window = mainwindow_cls(NicosLogger("mainwindow"), config)
        window.autoconnect = False
        window.confirmexit = False

        qtbot.addWidget(window)
        window.show()
        qtbot.waitUntil(window.isVisible)

        window.client.connect(ConnectionData("fake", 0, "test", "test"))
        qtbot.waitUntil(lambda: window.client.isconnected, timeout=2000)

        windows.append(window)
        return window

    windows: list = []
    yield _build

    for window in windows:
        if window.client.isconnected:
            window.client.disconnect()
            qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
        thread = getattr(window.client, "event_thread", None)
        if thread is not None:
            thread.join(timeout=1.0)


@pytest.fixture
def gui_window(gui_window_factory, guiconfig_path):
    return gui_window_factory(guiconfig_path=guiconfig_path)


@pytest.fixture
def devices_panel(gui_window):
    return gui_window.getPanel("Devices")

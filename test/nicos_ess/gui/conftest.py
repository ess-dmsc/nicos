"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests use file-based guiconfigs under
``test/nicos_ess/gui/guiconfigs`` and default to ``base.py`` unless a module
selects a more specific panel or layout config.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.utils import importString
from nicos.utils.loggers import NicosLogger

from test.nicos_ess.gui.doubles import FakeClientTransport, FakeDaemon
from test.nicos_ess.gui.helpers import get_panel_by_class
from test.runtime_resources import ensure_runtime_resources


GUICONFIGS_DIR = Path(__file__).with_name("guiconfigs").resolve()
TEST_ROOT = Path(__file__).resolve().parents[2] / "root"
RESOURCES_DIR = Path(__file__).resolve().parents[3] / "resources"
_IGNORED_QT_MESSAGE_PATTERNS = (
    r"^QObject::connect: No such signal "
    r"QPlatformNativeInterface::systemTrayWindowChanged\(QScreen\*\)$",
    r"^This plugin does not support propagateSizeHints\(\)$",
)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # This must happen before pytest-qt creates the QApplication. The mutation
    # is process-local to the pytest run, so best-effort restoration is enough.
    config._nicos_original_qt_qpa_platform = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    for pattern in _IGNORED_QT_MESSAGE_PATTERNS:
        config.addinivalue_line("qt_log_ignore", pattern)


def pytest_unconfigure(config):
    original_qt_qpa_platform = getattr(
        config, "_nicos_original_qt_qpa_platform", None
    )
    if original_qt_qpa_platform is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ["QT_QPA_PLATFORM"] = original_qt_qpa_platform


def _resolve_guiconfig_path(guiconfig_name: str) -> Path:
    if not isinstance(guiconfig_name, str) or not guiconfig_name:
        raise ValueError(
            "GUI test guiconfig_name must be a non-empty relative path, "
            "for example 'command_console.py'"
        )
    guiconfig_path = (GUICONFIGS_DIR / guiconfig_name).resolve()
    try:
        guiconfig_path.relative_to(GUICONFIGS_DIR)
    except ValueError as err:
        raise ValueError(
            f"GUI test guiconfig_name must stay inside {GUICONFIGS_DIR}: "
            f"{guiconfig_name!r}"
        ) from err
    if not guiconfig_path.is_file():
        raise FileNotFoundError(
            f"GUI test guiconfig not found: {guiconfig_name!r} -> {guiconfig_path}"
        )
    return guiconfig_path


def _event_thread_stopped(thread) -> bool:
    from nicos.guisupport.qt import QApplication

    # FakeClientTransport.disconnect() interrupts recv_event(), but the thread
    # may still be finishing a queued Qt signal delivery from an earlier event.
    QApplication.processEvents()
    return not thread.is_alive()


def _raise_teardown_errors(teardown_errors):
    primary_error = teardown_errors[0]
    current_error = primary_error
    for extra_error in teardown_errors[1:]:
        current_error.__context__ = extra_error
        current_error = extra_error
    raise RuntimeError(
        f"GUI window teardown failed with {len(teardown_errors)} error(s)"
    ) from primary_error


def _stop_active_timers(widget) -> None:
    from nicos.guisupport.qt import QTimer

    for timer in widget.findChildren(QTimer):
        if timer.isActive():
            timer.stop()


@pytest.fixture
def fake_daemon():
    return FakeDaemon()


@pytest.fixture(scope="session", autouse=True)
def gui_runtime_resources():
    ensure_runtime_resources(RESOURCES_DIR, TEST_ROOT / "resources")


@pytest.fixture
def strict_fake_daemon(fake_daemon):
    yield
    assert fake_daemon.unknown_evals == []
    assert fake_daemon.unknown_commands == []


@pytest.fixture
def guiconfig_name(request):
    return getattr(request.module, "guiconfig_name", "base.py")


@pytest.fixture
def panel_name(request):
    return getattr(request.module, "panel_name", None)


@pytest.fixture
def panel_class(request):
    return getattr(request.module, "panel_class", None)


@pytest.fixture
def guiconfig_path(guiconfig_name):
    return _resolve_guiconfig_path(guiconfig_name)


@pytest.fixture
def gui_window_factory(monkeypatch, qtbot, fake_daemon):
    from nicos.guisupport.qt import QApplication

    windows = []

    def _build(*, guiconfig_path=None, guiconfig=None):
        if (guiconfig_path is None) == (guiconfig is None):
            raise ValueError(
                "pass exactly one of guiconfig_path or guiconfig to "
                "gui_window_factory()"
            )

        monkeypatch.setattr(
            "nicos.clients.base.ClientTransport",
            lambda: FakeClientTransport(fake_daemon),
        )

        config_source = guiconfig
        if guiconfig_path is not None:
            config_source = Path(guiconfig_path).read_text()
        config = processGuiConfig(config_source.strip())
        # Keep GUI tests independent from optional stylesheet/resource lookup.
        config.stylefile = ""

        mainwindow_cls = importString(config.options["mainwindow_class"])
        mainwindow_log = NicosLogger("mainwindow")
        # MainWindow uses NICOS logger helpers such as error(..., exc=...), so
        # this must stay a NicosLogger. Parent it into the stdlib logging tree
        # so pytest's caplog can still observe GUI warnings and errors.
        mainwindow_log.parent = logging.getLogger()
        mainwindow_log.propagate = True
        window = mainwindow_cls(mainwindow_log, config)
        window.autoconnect = False
        window.confirmexit = False

        window.show()
        qtbot.waitUntil(lambda w=window: w.isVisible(), timeout=2000)

        window.client.connect(ConnectionData("fake", 0, "test", "test"))
        qtbot.waitUntil(lambda w=window: w.client.isconnected, timeout=2000)

        windows.append(window)
        return window

    yield _build

    teardown_errors = []
    for window in windows:
        thread = getattr(window.client, "event_thread", None)
        try:
            if window.client.isconnected:
                window.client.disconnect()
                qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
            if thread is not None:
                qtbot.waitUntil(
                    lambda t=thread: _event_thread_stopped(t), timeout=2000
                )
        except Exception as err:
            teardown_errors.append(err)
        finally:
            try:
                _stop_active_timers(window)
                # The real MainWindow.closeEvent() quits the shared QApplication,
                # which breaks subsequent pytest-qt tests in the same session.
                window.hide()
                window.deleteLater()
            except Exception as err:
                teardown_errors.append(err)

    QApplication.processEvents()
    if teardown_errors:
        _raise_teardown_errors(teardown_errors)


@pytest.fixture(autouse=True)
def suppress_modal_message_boxes(monkeypatch):
    from nicos.guisupport.qt import QMessageBox

    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.warning",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.critical",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )


@pytest.fixture
def gui_window(gui_window_factory, request):
    guiconfig = getattr(request.module, "guiconfig_text", None)
    if guiconfig is not None:
        return gui_window_factory(guiconfig=guiconfig)
    return gui_window_factory(
        guiconfig_path=_resolve_guiconfig_path(
            getattr(request.module, "guiconfig_name", "base.py")
        )
    )


@pytest.fixture
def gui_window_from_name(gui_window_factory):
    def _build(guiconfig_name):
        return gui_window_factory(guiconfig_path=_resolve_guiconfig_path(guiconfig_name))

    return _build


@pytest.fixture
def gui_window_from_spec(gui_window_factory):
    def _build(guiconfig):
        if guiconfig.text is not None:
            return gui_window_factory(guiconfig=guiconfig.text)
        return gui_window_factory(guiconfig_path=_resolve_guiconfig_path(guiconfig.name))

    return _build


@pytest.fixture
def gui_panel(gui_window, panel_name, panel_class, guiconfig_name):
    if panel_class is not None:
        return get_panel_by_class(gui_window, panel_class)
    if panel_name is None:
        raise ValueError(
            "gui_panel requires module-level panel_class or panel_name, "
            f"for example in tests using {guiconfig_name!r}"
        )
    panel = gui_window.getPanel(panel_name)
    if panel is None:
        raise LookupError(
            f"panel {panel_name!r} not found in GUI test config {guiconfig_name!r}"
        )
    return panel

"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests use file-based guiconfigs under
``test/nicos_ess/gui/guiconfigs`` and default to ``base.py`` unless a test
passes an explicit ``GuiConfigSpec`` through the ``gui_window`` fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path

import pytest

from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.utils import importString
from nicos.utils.loggers import NicosLogger

from test.nicos_ess.gui.doubles import FakeClientTransport, FakeDaemon
from test.nicos_ess.gui.helpers import (
    GuiConfigSpec,
    get_panel_by_class,
    resolve_guiconfig_path,
)
from test.runtime_resources import ensure_runtime_resources


TEST_ROOT = Path(__file__).resolve().parents[2] / "root"
RESOURCES_DIR = Path(__file__).resolve().parents[3] / "resources"
_IGNORED_QT_MESSAGE_PATTERNS = (
    r"^QObject::connect: No such signal "
    r"QPlatformNativeInterface::systemTrayWindowChanged\(QScreen\*\)$",
    r"^This plugin does not support propagateSizeHints\(\)$",
)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # Process-global GUI test setup is documented in test/nicos_ess/README.md.
    # This must happen before pytest-qt creates the QApplication. The mutation
    # is process-local to the pytest run, so best-effort restoration is enough.
    config._nicos_original_qt_qpa_platform = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    # Some CI invocations disable entry-point plugin autoloading. These tests
    # require pytest-qt for both qtbot and qt_log_ignore.
    if not config.pluginmanager.hasplugin("pytest-qt"):
        config.pluginmanager.import_plugin("pytestqt.plugin")

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


def _event_thread_stopped(thread) -> bool:
    from nicos.guisupport.qt import QApplication

    # FakeClientTransport.disconnect() interrupts recv_event(), but the thread
    # may still be finishing a queued Qt signal delivery from an earlier event.
    QApplication.processEvents()
    return not thread.is_alive()


def _raise_teardown_errors(teardown_errors):
    raise ExceptionGroup(
        f"GUI window teardown failed with {len(teardown_errors)} error(s)",
        teardown_errors,
    )


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
    """Expose repository resources under the GUI test NICOS root."""
    ensure_runtime_resources(RESOURCES_DIR, TEST_ROOT / "resources")


@pytest.fixture
def strict_fake_daemon(fake_daemon):
    """Fail tests that send daemon commands the fake does not implement."""
    yield
    assert fake_daemon.unknown_commands == []


@pytest.fixture
def allow_critical_message_boxes():
    """Opt-in for tests that intentionally exercise critical dialogs."""
    return None


@pytest.fixture
def allow_warning_message_boxes():
    """Opt-in for tests that intentionally exercise warning dialogs."""
    return None


@pytest.fixture
def gui_window_factory(monkeypatch, qtbot, fake_daemon):
    """Build real ESS GUI windows connected to the in-process fake daemon."""
    from nicos.guisupport.qt import QApplication

    windows = []

    def _build(*, guiconfig_path=None, guiconfig=None):
        if (guiconfig_path is None) == (guiconfig is None):
            raise ValueError(
                "pass exactly one of guiconfig_path or guiconfig to "
                "gui_window_factory()"
            )

        # Patch exactly the transport factory used by NicosGuiClient. The GUI
        # client, window, panels, signals, and event thread stay real.
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


@dataclass(frozen=True)
class RecordedMessageBox:
    kind: str
    args: tuple
    kwargs: dict


@pytest.fixture(autouse=True)
def record_modal_message_boxes(monkeypatch, request):
    """Record static QMessageBox calls without entering a modal event loop."""
    from nicos.guisupport.qt import QMessageBox

    calls = []

    def _record(kind, answer):
        def _message_box(*args, **kwargs):
            calls.append(RecordedMessageBox(kind, args, dict(kwargs)))
            return answer

        return _message_box

    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.warning",
        _record("warning", QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.critical",
        _record("critical", QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.information",
        _record("information", QMessageBox.StandardButton.Ok),
    )
    monkeypatch.setattr(
        "nicos.guisupport.qt.QMessageBox.question",
        _record("question", QMessageBox.StandardButton.Yes),
    )

    yield calls

    unexpected_kinds = set()
    if "allow_critical_message_boxes" not in request.fixturenames:
        unexpected_kinds.add("critical")
    if "allow_warning_message_boxes" not in request.fixturenames:
        unexpected_kinds.add("warning")

    unexpected_calls = [call for call in calls if call.kind in unexpected_kinds]
    assert unexpected_calls == [], _format_unexpected_message_box_calls(
        unexpected_calls
    )


def _format_unexpected_message_box_calls(calls: list[RecordedMessageBox]) -> str:
    lines = ["unexpected QMessageBox call(s):"]
    for kind in ("critical", "warning"):
        kind_calls = [call for call in calls if call.kind == kind]
        if kind_calls:
            lines.append(f"{kind}:")
            lines.extend(f"  {_format_message_box_call(call)}" for call in kind_calls)
    return "\n".join(lines)


def _format_message_box_call(call: RecordedMessageBox) -> str:
    title = call.args[1] if len(call.args) > 1 else ""
    text = call.args[2] if len(call.args) > 2 else ""
    return f"{call.kind}: {title!r} {text!r}"


@pytest.fixture
def gui_window(request, gui_window_factory):
    """Return a window built from request.param (GuiConfigSpec) or base.py."""
    spec = getattr(request, "param", None)
    if spec is None:
        return gui_window_factory(guiconfig_path=resolve_guiconfig_path("base.py"))
    if not isinstance(spec, GuiConfigSpec):
        raise TypeError(
            "gui_window indirect params must be GuiConfigSpec instances, "
            f"got {type(spec).__name__}"
        )
    if spec.text is not None:
        return gui_window_factory(guiconfig=spec.text)
    return gui_window_factory(guiconfig_path=resolve_guiconfig_path(spec.name))


@pytest.fixture
def gui_panel(request, gui_window):
    panel_class = getattr(request, "param", None)
    if panel_class is None:
        raise ValueError("gui_panel requires an indirect panel class parameter")
    return get_panel_by_class(gui_window, panel_class)

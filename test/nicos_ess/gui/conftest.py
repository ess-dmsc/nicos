"""Shared fixtures for ESS GUI tests running against an in-process fake daemon.

Only the transport is faked: ``NicosGuiClient``, ``MainWindow``, and all panels
remain the unmodified production classes. Tests use file-based guiconfigs under
``test/nicos_ess/gui/guiconfigs`` and default to ``base.py`` unless a test
passes an explicit ``GuiConfigSpec`` through the ``gui_window`` fixture.
"""

from __future__ import annotations

import builtins
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest import CollectReport, StashKey

from nicos.clients.base import ConnectionData
from nicos.clients.gui.config import processGuiConfig
from nicos.guisupport.qt import QApplication, Qt
from nicos.utils import importString
from nicos.utils.loggers import NicosLogger
from test.nicos_ess.gui.doubles import FakeClientTransport, FakeDaemon
from test.nicos_ess.gui.helpers import (
    GuiConfigSpec,
    get_panel_by_class,
    resolve_guiconfig_path,
)

phase_report_key = StashKey[dict[str, CollectReport]]()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    rep = yield

    # store test results for each phase of a call, which can
    # be "setup", "call", "teardown"
    item.stash.setdefault(phase_report_key, {})[rep.when] = rep

    return rep


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

    config._nicos_original_xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    config._nicos_test_xdg_runtime_dir = None
    if config._nicos_original_xdg_runtime_dir is None:
        runtime_dir = Path(tempfile.mkdtemp(prefix="nicos-qt-runtime-"))
        runtime_dir.chmod(0o700)
        config._nicos_test_xdg_runtime_dir = runtime_dir
        os.environ["XDG_RUNTIME_DIR"] = str(runtime_dir)

    # The GUI writes its QSettings to a temporary folder instead of the user's
    # ~/.config. When the run ends, the folder is removed and the old
    # XDG_CONFIG_HOME comes back.
    settings_folder = tempfile.TemporaryDirectory(prefix="nicos-gui-settings-")
    original_config_home = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = settings_folder.name

    def restore_config_home():
        if original_config_home is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = original_config_home
        settings_folder.cleanup()

    config.add_cleanup(restore_config_home)

    # Some CI invocations disable entry-point plugin autoloading. These tests
    # require pytest-qt for both qtbot and qt_log_ignore.
    if not config.pluginmanager.hasplugin("pytest-qt"):
        config.pluginmanager.import_plugin("pytestqt.plugin")

    for pattern in _IGNORED_QT_MESSAGE_PATTERNS:
        config.addinivalue_line("qt_log_ignore", pattern)


def pytest_unconfigure(config):
    original_qt_qpa_platform = getattr(config, "_nicos_original_qt_qpa_platform", None)
    if original_qt_qpa_platform is None:
        os.environ.pop("QT_QPA_PLATFORM", None)
    else:
        os.environ["QT_QPA_PLATFORM"] = original_qt_qpa_platform

    original_xdg_runtime_dir = getattr(config, "_nicos_original_xdg_runtime_dir", None)
    if original_xdg_runtime_dir is None:
        os.environ.pop("XDG_RUNTIME_DIR", None)
    else:
        os.environ["XDG_RUNTIME_DIR"] = original_xdg_runtime_dir

    test_xdg_runtime_dir = getattr(config, "_nicos_test_xdg_runtime_dir", None)
    if test_xdg_runtime_dir is not None:
        shutil.rmtree(test_xdg_runtime_dir, ignore_errors=True)


def wait_until_event_thread_stopped(thread, qtbot) -> None:
    from nicos.guisupport.qt import QApplication

    # FakeClientTransport.disconnect() interrupts recv_event(), but the thread
    # may still be finishing a queued Qt signal delivery from an earlier event.
    def _stopped():
        QApplication.processEvents()
        return not thread.is_alive()

    qtbot.waitUntil(_stopped, timeout=2000)


def _raise_teardown_errors(teardown_errors):
    if len(teardown_errors) == 1:
        raise teardown_errors[0]
    message = f"GUI window teardown failed with {len(teardown_errors)} error(s)"
    if hasattr(builtins, "ExceptionGroup"):
        raise builtins.ExceptionGroup(message, teardown_errors)
    details = "\n".join(f"{type(err).__name__}: {err}" for err in teardown_errors)
    raise RuntimeError(f"{message}\n{details}") from teardown_errors[0]


def _stop_active_timers(widget) -> None:
    from nicos.guisupport.qt import QTimer

    for timer in widget.findChildren(QTimer):
        if timer.isActive():
            timer.stop()


@pytest.fixture
def c_locale():
    """Parse and format numbers the same on every machine (``.`` as decimal point)."""
    from nicos.guisupport.qt import QLocale

    previous = QLocale()
    QLocale.setDefault(QLocale.c())
    yield
    QLocale.setDefault(previous)


@pytest.fixture
def fake_daemon():
    return FakeDaemon()


@pytest.fixture(scope="session", autouse=True)
def gui_runtime_resources():
    """Expose repository resources under the GUI test NICOS root."""
    return


@pytest.fixture
def strict_fake_daemon(fake_daemon):
    """Fail tests that hit daemon requests the fake does not implement."""
    yield
    assert fake_daemon.unknown_commands == []
    assert fake_daemon.unknown_evals == []


@pytest.fixture
def allow_unknown_fake_daemon_requests():
    """Opt out for tests that intentionally exercise fake-daemon misses."""
    return None


@pytest.fixture(autouse=True)
def strict_fake_daemon_by_default(request):
    if "allow_unknown_fake_daemon_requests" not in request.fixturenames:
        request.getfixturevalue("strict_fake_daemon")
    yield


@pytest.fixture
def allow_critical_message_boxes():
    """Opt-in for tests that intentionally exercise critical dialogs."""
    return None


@pytest.fixture
def allow_warning_message_boxes():
    """Opt-in for tests that intentionally exercise warning dialogs."""
    return None


@pytest.fixture
def allow_unpatched_message_boxes():
    """Opt out for tests that do not construct GUI code or dialogs."""
    return None


@pytest.fixture
def gui_window_factory(monkeypatch, qtbot, fake_daemon, request, tmp_path):
    """Build real ESS GUI windows connected to the in-process fake daemon.

    request and tmp_path fixtures are needed for parsing test results and
    creating a screenshot of all open windows in case of a test failure.

    """
    from nicos.guisupport.qt import QApplication

    windows = []

    def _build(*, relative_path=None, guiconfig_string=None):
        if (relative_path is None) == (guiconfig_string is None):
            raise ValueError(
                "pass exactly one of relative_path or guiconfig_string to "
                "gui_window_factory()"
            )

        # Patch exactly the transport factory used by NicosGuiClient. The GUI
        # client, window, panels, signals, and event thread stay real.
        monkeypatch.setattr(
            "nicos.clients.base.ClientTransport",
            lambda: FakeClientTransport(fake_daemon),
        )

        config_source = guiconfig_string
        if relative_path is not None:
            config_source = resolve_guiconfig_path(relative_path).read_text()
        config = processGuiConfig(config_source.strip())
        # processGuiConfig() does not set stylefile; production nicos_ess.gui.main
        # resolves/applies QSS before constructing MainWindow. These tests start
        # at the window/client boundary and keep stylesheet loading outside panel
        # startup coverage.
        config.stylefile = ""

        mainwindow_cls = importString(config.options["mainwindow_class"])
        mainwindow_log = NicosLogger("mainwindow")
        # Keep this NicosLogger visible to pytest's stdlib caplog capture.
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

    # request.node is an "item" because we use the default
    # "function" scope
    report = request.node.stash[phase_report_key]
    if report["setup"].failed:
        print("setting up a test failed", request.node.nodeid)
    elif report["setup"].skipped:
        print("setting up a test skipped", request.node.nodeid)
    elif ("call" not in report) or report["call"].failed:
        print("executing test failed or skipped", request.node.nodeid)
        for window in windows:
            path = qtbot.screenshot(window)
            print(f"taking screenshot of {window.name} and storing it in {path}")

    # The real MainWindow.closeEvent() ends by quitting the process-global
    # QApplication. Patch only that session-level side effect so teardown can
    # still exercise panel requestClose(), settings save, child-window close, and
    # client disconnect behavior.
    monkeypatch.setattr(QApplication.instance(), "quit", lambda: None)

    teardown_errors = []
    for window in windows:
        thread = getattr(window.client, "event_thread", None)
        try:
            _stop_active_timers(window)
            if not window.close():
                raise AssertionError("GUI window rejected close during test teardown")
            QApplication.processEvents()
            if window.client.isconnected:
                window.client.disconnect()
                qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
            if thread is not None:
                wait_until_event_thread_stopped(thread, qtbot)
        except Exception as err:
            teardown_errors.append(err)
        finally:
            try:
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
    if "allow_unpatched_message_boxes" in request.fixturenames:
        yield []
        return

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
        return gui_window_factory(relative_path="base.py")
    if not isinstance(spec, GuiConfigSpec):
        raise TypeError(
            "gui_window indirect params must be GuiConfigSpec instances, "
            f"got {type(spec).__name__}"
        )
    if spec.source_string is not None:
        return gui_window_factory(guiconfig_string=spec.source_string)
    return gui_window_factory(relative_path=spec.relative_path)


@pytest.fixture
def gui_panel(request, gui_window):
    panel_class = getattr(request, "param", None)
    if panel_class is None:
        raise ValueError("gui_panel requires an indirect panel class parameter")
    return get_panel_by_class(gui_window, panel_class)


@pytest.fixture(autouse=True)
def no_mouse_button_held(request):
    """A button that a test leaves held hides the hover box in later tests.

    The fixture releases the button before it fails, so that only the test
    that left it held fails.
    """
    yield
    if QApplication.instance() is None:
        return
    held = QApplication.mouseButtons()
    if held == Qt.MouseButton.NoButton:
        return
    from pytestqt.qt_compat import qt_api

    from nicos.guisupport.qt import QEvent, QWidget

    # The windows of the test are closed already, and QTest needs a shown
    # window to send the release to.
    window = QWidget()
    window.show()
    buttons = {
        "left": Qt.MouseButton.LeftButton,
        "right": Qt.MouseButton.RightButton,
        "middle": Qt.MouseButton.MiddleButton,
    }
    held_names = [name for name, button in buttons.items() if held & button]
    for name in held_names:
        qt_api.QtTest.QTest.mouseRelease(window, buttons[name])
    window.close()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    pytest.fail(
        f"{request.node.nodeid} left the {' and '.join(held_names)} mouse button held"
    )


@pytest.fixture(autouse=True)
def no_saved_settings():
    """Closing a window saves its settings, and a later test would read them."""
    from nicos.guisupport.qt import QSettings

    def clear():
        if QApplication.instance() is not None:
            settings = QSettings()
            settings.clear()
            settings.sync()

    clear()
    yield
    clear()

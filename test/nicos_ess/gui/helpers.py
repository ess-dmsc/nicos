"""Helpers for ESS GUI panel startup and lifecycle tests."""

from __future__ import annotations

import logging
import pytest

from nicos.guisupport.qt import QApplication
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from nicos.utils import importString


def _minimal_guiconfig(panel_cls, **panel_kwargs):
    panel_args = [repr(panel_cls)]
    panel_args.extend(f"{name}={value!r}" for name, value in panel_kwargs.items())
    if len(panel_args) == 1:
        main_window = f"main_window = panel({panel_args[0]})"
    else:
        joined_args = ",\n    ".join(panel_args)
        main_window = f"main_window = panel(\n    {joined_args},\n)"
    return (
        f"{main_window}\n"
        "windows = []\n"
        "tools = []\n"
        'options = {\n'
        '    "facility": "ess",\n'
        '    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",\n'
        "}\n"
    )


def panel_case(
    case_id,
    panel_class,
    *,
    guiconfig_name=None,
    seed_daemon=None,
    marks=(),
    **panel_kwargs,
):
    guiconfig_text = None
    if guiconfig_name is None:
        guiconfig_text = _minimal_guiconfig(panel_class, **panel_kwargs)
    return pytest.param(
        guiconfig_name,
        guiconfig_text,
        panel_class,
        seed_daemon,
        id=case_id,
        marks=marks,
    )


def get_panel_by_class(window, panel_class):
    panel_cls = importString(panel_class) if isinstance(panel_class, str) else panel_class
    matches = [panel for panel in window.panels if type(panel) is panel_cls]
    assert len(matches) == 1, (
        f"expected one {panel_cls.__module__}.{panel_cls.__name__} panel, "
        f"found {[type(panel).__name__ for panel in window.panels]}"
    )
    return matches[0]


def _is_relevant_gui_record(record):
    pathname = record.pathname.replace("\\", "/")
    return "/nicos/" in pathname or "/nicos_ess/" in pathname


def _assert_no_errors(caplog):
    relevant_records = [
        record for record in caplog.records if _is_relevant_gui_record(record)
    ]
    errors = [record for record in relevant_records if record.levelno >= logging.ERROR]
    assert errors == [], "unexpected GUI log records:\n" + "\n".join(
        f"{record.levelname} {record.name}: {record.getMessage()}"
        for record in relevant_records
    )


def _assert_panel_is_alive(window, panel):
    assert panel in window.panels
    assert panel.isVisible() is True
    assert window.client.isconnected is True


def _build_panel(
    *,
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon=None,
):
    if seed_daemon is not None:
        seed_daemon(fake_daemon)

    caplog.clear()
    caplog.set_level(logging.INFO)

    if guiconfig_text is not None:
        window = gui_window_factory(guiconfig=guiconfig_text)
    else:
        window = gui_window_from_name(guiconfig_name)
    QApplication.processEvents()

    return window, get_panel_by_class(window, panel_class)


def assert_panel_starts_clean(
    *,
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon=None,
):
    _, panel = _build_panel(
        gui_window_factory=gui_window_factory,
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        guiconfig_text=guiconfig_text,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )
    _assert_no_errors(caplog)
    return panel


def assert_panel_survives_lifecycle_events_cleanly(
    *,
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon=None,
):
    window, panel = _build_panel(
        gui_window_factory=gui_window_factory,
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        guiconfig_text=guiconfig_text,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )
    _assert_no_errors(caplog)

    caplog.clear()

    if not fake_daemon.setups:
        fake_daemon.add_setup("system")
    loaded_setups = sorted(fake_daemon.loaded_setups)
    if not loaded_setups:
        loaded_setups = sorted(fake_daemon.setups)

    with qtbot.waitSignal(window.client.setup, timeout=2000):
        fake_daemon.push_setup(loaded_setups)
    _assert_panel_is_alive(window, panel)

    # Status payloads are (status_code, lineno); -1 means "no active line".
    with qtbot.waitSignal(window.client.status, timeout=2000):
        fake_daemon.push_status((STATUS_RUNNING, -1))
    _assert_panel_is_alive(window, panel)

    with qtbot.waitSignal(window.client.status, timeout=2000):
        fake_daemon.push_status((STATUS_IDLE, -1))
    _assert_panel_is_alive(window, panel)

    thread = getattr(window.client, "event_thread", None)
    window.client.disconnect()
    qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
    if thread is not None:
        qtbot.waitUntil(lambda t=thread: not t.is_alive(), timeout=2000)
    QApplication.processEvents()

    _assert_no_errors(caplog)
    return panel

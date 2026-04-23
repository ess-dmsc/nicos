"""Helpers for ESS GUI panel startup and lifecycle tests."""

from __future__ import annotations

import logging

from nicos.guisupport.qt import QApplication
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from nicos.utils import importString


def _build_panel(
    *,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
    seed_daemon=None,
):
    if seed_daemon is not None:
        seed_daemon(fake_daemon)

    caplog.clear()
    caplog.set_level(logging.WARNING)

    window = gui_window_from_name(guiconfig_name)
    qtbot.wait(25)
    QApplication.processEvents()

    panel_cls = importString(panel_class) if isinstance(panel_class, str) else panel_class
    matches = [panel for panel in window.panels if type(panel) is panel_cls]
    assert len(matches) == 1, (
        f"expected one {panel_cls.__module__}.{panel_cls.__name__} panel, "
        f"found {[type(panel).__name__ for panel in window.panels]}"
    )
    return window, matches[0]


def _assert_no_warnings(caplog):
    warnings = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ]
    assert warnings == [], "unexpected GUI log records:\n" + "\n".join(
        f"{record.levelname} {record.name}: {record.getMessage()}"
        for record in warnings
    )


def assert_panel_starts_clean(
    *,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
    seed_daemon=None,
):
    _, panel = _build_panel(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )
    _assert_no_warnings(caplog)
    return panel


def assert_panel_survives_lifecycle_events_cleanly(
    *,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
    seed_daemon=None,
):
    window, panel = _build_panel(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
        seed_daemon=seed_daemon,
    )
    _assert_no_warnings(caplog)

    caplog.clear()

    if not fake_daemon.setups:
        fake_daemon.add_setup("system")
    loaded_setups = sorted(fake_daemon.loaded_setups)
    if not loaded_setups:
        loaded_setups = sorted(fake_daemon.setups)

    fake_daemon.push_setup(loaded_setups)
    qtbot.wait(25)
    QApplication.processEvents()

    fake_daemon.push_status((STATUS_RUNNING, -1))
    qtbot.wait(25)
    QApplication.processEvents()

    fake_daemon.push_status((STATUS_IDLE, -1))
    qtbot.wait(25)
    QApplication.processEvents()

    thread = getattr(window.client, "event_thread", None)
    window.client.disconnect()
    qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
    if thread is not None:
        qtbot.waitUntil(lambda t=thread: not t.is_alive(), timeout=2000)
    QApplication.processEvents()

    _assert_no_warnings(caplog)
    return panel

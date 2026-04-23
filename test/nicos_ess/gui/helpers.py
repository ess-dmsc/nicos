"""Helpers for minimal ESS GUI panel startup tests."""

from __future__ import annotations

import logging

from nicos.guisupport.qt import QApplication
from nicos.utils import importString


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

    warnings = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ]
    assert warnings == []
    return matches[0]

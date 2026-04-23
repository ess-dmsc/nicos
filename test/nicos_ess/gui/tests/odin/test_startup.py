"""Startup coverage for ODIN GUI modules outside ``panels/``."""

from __future__ import annotations

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
)


def test_metrology_system_panel_starts_without_warnings_or_errors(
    gui_window_from_name, fake_daemon, caplog, qtbot
):
    assert_panel_starts_clean(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name="odin/metrology_system.py",
        panel_class="nicos_ess.odin.gui.metrology_system.MetrologySystemPanel",
    )


def test_metrology_system_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_from_name, fake_daemon, caplog, qtbot
):
    assert_panel_survives_lifecycle_events_cleanly(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name="odin/metrology_system.py",
        panel_class="nicos_ess.odin.gui.metrology_system.MetrologySystemPanel",
    )

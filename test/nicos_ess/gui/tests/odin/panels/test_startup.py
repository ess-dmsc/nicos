"""Startup coverage for ODIN panels."""

from __future__ import annotations

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
)


def test_live_panel_starts_without_warnings_or_errors(
    gui_window_from_name, fake_daemon, caplog, qtbot
):
    assert_panel_starts_clean(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name="odin/panels/live.py",
        panel_class="nicos_ess.odin.gui.panels.live.MultiLiveDataPanel",
    )


def test_live_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_from_name, fake_daemon, caplog, qtbot
):
    assert_panel_survives_lifecycle_events_cleanly(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name="odin/panels/live.py",
        panel_class="nicos_ess.odin.gui.panels.live.MultiLiveDataPanel",
    )

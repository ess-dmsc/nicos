"""Startup coverage for TBL panels."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
    panel_case,
)

_TBL_PANEL_CASES = [
    panel_case("live", "nicos_ess.tbl.gui.panels.live.MultiLiveDataPanel"),
]


@pytest.mark.parametrize(
    ("guiconfig_name", "guiconfig_text", "panel_class", "seed_daemon"),
    _TBL_PANEL_CASES,
)
def test_panel_starts_without_warnings_or_errors(
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon,
):
    assert_panel_starts_clean(
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


@pytest.mark.parametrize(
    ("guiconfig_name", "guiconfig_text", "panel_class", "seed_daemon"),
    _TBL_PANEL_CASES,
)
def test_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_factory,
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    guiconfig_text,
    panel_class,
    seed_daemon,
):
    assert_panel_survives_lifecycle_events_cleanly(
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

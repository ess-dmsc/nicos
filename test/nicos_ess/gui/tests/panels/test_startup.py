"""Startup coverage for generic ESS panels."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
    panel_case,
)


_GENERIC_PANEL_CASES = [
    panel_case("chopper", "nicos_ess.gui.panels.chopper.ChopperPanel"),
    panel_case("cmdbuilder", "nicos_ess.gui.panels.cmdbuilder.CommandPanel"),
    panel_case("console", "nicos_ess.gui.panels.console.ConsolePanel"),
    panel_case("devices", "nicos_ess.gui.panels.devices.DevicesPanel"),
    panel_case("editor", "nicos_ess.gui.panels.editor.EditorPanel"),
    panel_case("empty", "nicos_ess.gui.panels.empty.EmptyPanel"),
    panel_case("errors", "nicos_ess.gui.panels.errors.ErrorPanel"),
    panel_case("exp-panel", "nicos_ess.gui.panels.exp_panel.ExpPanel"),
    panel_case("hexapod", "nicos_ess.gui.panels.hexapod.HexapodPanel"),
    panel_case("history", "nicos_ess.gui.panels.history.HistoryPanel"),
    panel_case("history-pyqt", "nicos_ess.gui.panels.history_pyqt.HistoryPanel"),
    panel_case(
        "live-gr",
        "nicos_ess.gui.panels.live_gr.LiveDataPanel",
        marks=pytest.mark.xfail(
            reason=(
                "standalone live_gr.LiveDataPanel does not match the ESS UI "
                "and fails to initialize; we are not using this panel either way"
            ),
        ),
    ),
    panel_case(
        "live-gr-multi",
        "nicos_ess.gui.panels.live_gr.MultiLiveDataPanel",
    ),
    panel_case(
        "live-pyqt",
        "nicos_ess.gui.panels.live_pyqt.LiveDataPanel",
    ),
    panel_case(
        "live-pyqt-multi",
        "nicos_ess.gui.panels.live_pyqt.MultiLiveDataPanel",
    ),
    panel_case(
        "livedata",
        "nicos_ess.gui.panels.livedata.LiveDataPanel",
    ),
    panel_case(
        "logviewer",
        "nicos_ess.gui.panels.logviewer.LogViewerPanel",
    ),
    panel_case(
        "rheometer",
        "nicos_ess.gui.panels.rheometer.RheometerPanel",
    ),
    panel_case(
        "scans",
        "nicos_ess.gui.panels.scans.ScansPanel",
    ),
    panel_case(
        "setups",
        "nicos_ess.gui.panels.setups.SetupsPanel",
    ),
    panel_case(
        "status",
        "nicos_ess.gui.panels.status.ScriptStatusPanel",
    ),
]


@pytest.mark.parametrize(
    ("guiconfig_name", "guiconfig_text", "panel_class", "seed_daemon"),
    _GENERIC_PANEL_CASES,
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
    _GENERIC_PANEL_CASES,
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

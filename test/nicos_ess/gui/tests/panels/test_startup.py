"""Startup coverage for generic ESS panels."""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_lifecycle_events_cleanly,
)


_GENERIC_PANEL_CASES = [
    pytest.param(
        "panels/chopper.py",
        "nicos_ess.gui.panels.chopper.ChopperPanel",
        id="chopper",
    ),
    pytest.param(
        "panels/cmdbuilder.py",
        "nicos_ess.gui.panels.cmdbuilder.CommandPanel",
        id="cmdbuilder",
    ),
    pytest.param(
        "panels/console.py",
        "nicos_ess.gui.panels.console.ConsolePanel",
        id="console",
    ),
    pytest.param(
        "panels/devices.py",
        "nicos_ess.gui.panels.devices.DevicesPanel",
        id="devices",
    ),
    pytest.param(
        "panels/editor.py",
        "nicos_ess.gui.panels.editor.EditorPanel",
        id="editor",
    ),
    pytest.param(
        "panels/empty.py",
        "nicos_ess.gui.panels.empty.EmptyPanel",
        id="empty",
    ),
    pytest.param(
        "panels/errors.py",
        "nicos_ess.gui.panels.errors.ErrorPanel",
        id="errors",
    ),
    pytest.param(
        "panels/exp_panel.py",
        "nicos_ess.gui.panels.exp_panel.ExpPanel",
        id="exp-panel",
    ),
    pytest.param(
        "panels/hexapod.py",
        "nicos_ess.gui.panels.hexapod.HexapodPanel",
        id="hexapod",
    ),
    pytest.param(
        "panels/history.py",
        "nicos_ess.gui.panels.history.HistoryPanel",
        id="history",
    ),
    pytest.param(
        "panels/history_pyqt.py",
        "nicos_ess.gui.panels.history_pyqt.HistoryPanel",
        id="history-pyqt",
    ),
    pytest.param(
        "panels/live_gr.py",
        "nicos_ess.gui.panels.live_gr.LiveDataPanel",
        marks=pytest.mark.xfail(
            reason=(
                "standalone live_gr.LiveDataPanel does not match the ESS UI "
                "and fails to initialize; we are not using this panel either way"
            ),
            strict=True,
        ),
        id="live-gr",
    ),
    pytest.param(
        "panels/live_gr_multidetector.py",
        "nicos_ess.gui.panels.live_gr.MultiLiveDataPanel",
        id="live-gr-multi",
    ),
    pytest.param(
        "panels/live_pyqt.py",
        "nicos_ess.gui.panels.live_pyqt.LiveDataPanel",
        id="live-pyqt",
    ),
    pytest.param(
        "panels/live_pyqt_multidetector.py",
        "nicos_ess.gui.panels.live_pyqt.MultiLiveDataPanel",
        id="live-pyqt-multi",
    ),
    pytest.param(
        "panels/livedata.py",
        "nicos_ess.gui.panels.livedata.LiveDataPanel",
        id="livedata",
    ),
    pytest.param(
        "panels/logviewer.py",
        "nicos_ess.gui.panels.logviewer.LogViewerPanel",
        id="logviewer",
    ),
    pytest.param(
        "panels/rheometer.py",
        "nicos_ess.gui.panels.rheometer.RheometerPanel",
        id="rheometer",
    ),
    pytest.param(
        "panels/scans.py",
        "nicos_ess.gui.panels.scans.ScansPanel",
        id="scans",
    ),
    pytest.param(
        "panels/setups.py",
        "nicos_ess.gui.panels.setups.SetupsPanel",
        id="setups",
    ),
    pytest.param(
        "panels/status.py",
        "nicos_ess.gui.panels.status.ScriptStatusPanel",
        id="status",
    ),
]


@pytest.mark.parametrize(("guiconfig_name", "panel_class"), _GENERIC_PANEL_CASES)
def test_panel_starts_without_warnings_or_errors(
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
):
    assert_panel_starts_clean(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
    )


@pytest.mark.parametrize(("guiconfig_name", "panel_class"), _GENERIC_PANEL_CASES)
def test_panel_survives_normal_lifecycle_events_without_warnings_or_errors(
    gui_window_from_name,
    fake_daemon,
    caplog,
    qtbot,
    guiconfig_name,
    panel_class,
):
    assert_panel_survives_lifecycle_events_cleanly(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name=guiconfig_name,
        panel_class=panel_class,
    )

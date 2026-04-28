"""Startup coverage for ESS GUI panels.

The panel inventory is curated, not auto-discovered. Every panel class
explicitly named as a top-level panel in production ESS guiconfigs under
``nicos_ess`` should get one case here. Base implementations that are never
used as a top-level panel are intentionally excluded with an inline comment.

When adding a panel, add a ``panel_case(...)`` to the matching instrument
group. If it needs richer options than literal kwargs, check in a small
``guiconfigs/<instrument>/<panel>.py`` file and pass ``guiconfig_name=``.
"""

from __future__ import annotations

import pytest

from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_minimal_status_transitions,
    panel_case,
)


def seed_spectrometer_devices(fake_daemon):
    for name in ("hr4", "qepro"):
        fake_daemon.add_device(
            DeviceSpec(
                name=name,
                valuetype=float,
                params={
                    "_wavelengths": [400.0, 500.0, 600.0],
                    "_spectrum_array": [1.0, 2.0, 3.0],
                    "_light_array": [1.0, 1.0, 1.0],
                    "_dark_array": [0.1, 0.1, 0.1],
                    "acquireunits": "ms",
                    "status": (0, "Idle"),
                    "darkvalid": True,
                    "lightvalid": True,
                    "integrationtime": 10.0,
                    "boxcarwidth": 1,
                    "acquiremode": "single",
                },
            ),
            setup="spectrometers",
        )


STARTUP_CASE_GROUPS = [
    (
        "panels",
        [
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
            panel_case(
                "history-pyqt",
                "nicos_ess.gui.panels.history_pyqt.HistoryPanel",
            ),
            # Standalone live_gr.LiveDataPanel is a base implementation for
            # instrument-specific/multi-panel live views, not a supported ESS
            # guiconfig entry point.
            panel_case(
                "live-gr-multi",
                "nicos_ess.gui.panels.live_gr.MultiLiveDataPanel",
            ),
            panel_case("live-pyqt", "nicos_ess.gui.panels.live_pyqt.LiveDataPanel"),
            panel_case(
                "live-pyqt-multi",
                "nicos_ess.gui.panels.live_pyqt.MultiLiveDataPanel",
            ),
            panel_case("livedata", "nicos_ess.gui.panels.livedata.LiveDataPanel"),
            panel_case("logviewer", "nicos_ess.gui.panels.logviewer.LogViewerPanel"),
            panel_case("rheometer", "nicos_ess.gui.panels.rheometer.RheometerPanel"),
            panel_case("scans", "nicos_ess.gui.panels.scans.ScansPanel"),
            panel_case("setups", "nicos_ess.gui.panels.setups.SetupsPanel"),
            panel_case("status", "nicos_ess.gui.panels.status.ScriptStatusPanel"),
        ],
    ),
    (
        "dream",
        [
            panel_case(
                "comparison-panel",
                "nicos_ess.dream.gui.comparison_panel.ComparisonPanel",
            ),
        ],
    ),
    (
        "estia-panels",
        [
            panel_case("hexapod", "nicos_ess.estia.gui.panels.hexapod.HexapodPanel"),
            panel_case(
                "selene",
                "nicos_ess.estia.gui.panels.selene.SelenePanel",
                guiconfig_name="estia/selene.py",
            ),
        ],
    ),
    (
        "loki",
        [
            panel_case(
                "sample-holder-config",
                "nicos_ess.loki.gui.sample_holder_config.LokiSampleHolderPanel",
            ),
            panel_case(
                "scriptbuilder",
                "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel",
            ),
        ],
    ),
    (
        "loki-panels",
        [
            panel_case(
                "spectrometer",
                "nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel",
                seed_daemon=seed_spectrometer_devices,
            ),
        ],
    ),
    (
        "odin",
        [
            panel_case(
                "metrology-system",
                "nicos_ess.odin.gui.metrology_system.MetrologySystemPanel",
            ),
        ],
    ),
    (
        "odin-panels",
        [
            panel_case("live", "nicos_ess.odin.gui.panels.live.MultiLiveDataPanel"),
        ],
    ),
    (
        "tbl-panels",
        [
            panel_case("live", "nicos_ess.tbl.gui.panels.live.MultiLiveDataPanel"),
        ],
    ),
]


ALL_STARTUP_CASES = [
    pytest.param(
        case,
        id=f"{instrument}-{case.case_id}",
        marks=case.marks,
    )
    for instrument, cases in STARTUP_CASE_GROUPS
    for case in cases
]


@pytest.mark.parametrize("startup_case", ALL_STARTUP_CASES)
def test_panel_starts_without_warnings_or_errors(
    gui_window_factory,
    startup_case,
    fake_daemon,
    caplog,
):
    assert_panel_starts_clean(
        gui_window_factory=gui_window_factory,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
    )


@pytest.mark.parametrize("startup_case", ALL_STARTUP_CASES)
def test_panel_survives_minimal_status_transitions_without_warnings_or_errors(
    gui_window_factory,
    startup_case,
    fake_daemon,
    caplog,
    qtbot,
):
    assert_panel_survives_minimal_status_transitions(
        gui_window_factory=gui_window_factory,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
    )

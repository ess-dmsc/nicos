"""Startup coverage for ESS GUI panels.

The panel inventory is curated, not auto-discovered. Every panel class
explicitly named as a top-level panel in production ESS guiconfigs under
``nicos_ess`` should get one case here. Base implementations that are never
used as a top-level panel are intentionally excluded with an inline comment.

When adding a panel, follow the GUI startup inventory guidance in
``test/nicos_ess/README.md``. In short, add a ``panel_case(...)`` to the
matching instrument group; if it needs richer options than literal kwargs, check
in a small ``guiconfigs/<instrument>/<panel>.py`` file and pass
``guiconfig_name=``. Refresh the inventory with
``grep -R "panel(" nicos_ess --include='guiconfig.py'``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import nicos_ess
from nicos.clients.gui.config import panel, prepareGuiNamespace
from nicos.utils import importString
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    assert_panel_starts_clean,
    assert_panel_survives_minimal_status_transitions,
    panel_case,
)


def seed_spectrometer_devices(fake_daemon):
    # Shape-valid arrays/status for SpectrometerPanel startup; values are not
    # domain-significant.
    spectrum_shape = [1.0, 2.0, 3.0]
    idle_status = (0, "Idle")
    for name in ("hr4", "qepro"):
        fake_daemon.add_device(
            DeviceSpec(
                name=name,
                valuetype=float,
                params={
                    "_wavelengths": [400.0, 500.0, 600.0],
                    "_spectrum_array": spectrum_shape,
                    "_light_array": [1.0, 1.0, 1.0],
                    "_dark_array": [0.1, 0.1, 0.1],
                    "acquireunits": "ms",
                    "status": idle_status,
                    "darkvalid": True,
                    "lightvalid": True,
                    "integrationtime": 10.0,
                    "boxcarwidth": 1,
                    "acquiremode": "single",
                },
            ),
            setup="spectrometers",
        )


# Plain group names mirror production instrument package names. Groups ending
# in "-panels" cover reusable panel subpackages within an instrument package.
STARTUP_CASE_GROUPS = [
    (
        "panels",
        [
            panel_case(
                case_id="chopper",
                panel_class="nicos_ess.gui.panels.chopper.ChopperPanel",
            ),
            panel_case(
                case_id="cmdbuilder",
                panel_class="nicos_ess.gui.panels.cmdbuilder.CommandPanel",
            ),
            panel_case(
                case_id="console",
                panel_class="nicos_ess.gui.panels.console.ConsolePanel",
            ),
            panel_case(
                case_id="devices",
                panel_class="nicos_ess.gui.panels.devices.DevicesPanel",
            ),
            panel_case(
                case_id="editor",
                panel_class="nicos_ess.gui.panels.editor.EditorPanel",
            ),
            panel_case(
                case_id="empty",
                panel_class="nicos_ess.gui.panels.empty.EmptyPanel",
            ),
            panel_case(
                case_id="errors",
                panel_class="nicos_ess.gui.panels.errors.ErrorPanel",
            ),
            panel_case(
                case_id="exp-panel",
                panel_class="nicos_ess.gui.panels.exp_panel.ExpPanel",
            ),
            panel_case(
                case_id="hexapod",
                panel_class="nicos_ess.gui.panels.hexapod.HexapodPanel",
            ),
            panel_case(
                case_id="history",
                panel_class="nicos_ess.gui.panels.history.HistoryPanel",
            ),
            panel_case(
                case_id="history-pyqt",
                panel_class="nicos_ess.gui.panels.history_pyqt.HistoryPanel",
            ),
            panel_case(
                case_id="liveview",
                panel_class="nicos_ess.gui.panels.liveview.LiveViewPanel",
            ),
            panel_case(
                case_id="logviewer",
                panel_class="nicos_ess.gui.panels.logviewer.LogViewerPanel",
            ),
            panel_case(
                case_id="rheometer",
                panel_class="nicos_ess.gui.panels.rheometer.RheometerPanel",
            ),
            panel_case(
                case_id="scans",
                panel_class="nicos_ess.gui.panels.scans.ScansPanel",
            ),
            panel_case(
                case_id="setups",
                panel_class="nicos_ess.gui.panels.setups.SetupsPanel",
            ),
            panel_case(
                case_id="status",
                panel_class="nicos_ess.gui.panels.status.ScriptStatusPanel",
            ),
        ],
    ),
    (
        "dream",
        [
            panel_case(
                case_id="comparison-panel",
                panel_class="nicos_ess.dream.gui.comparison_panel.ComparisonPanel",
            ),
        ],
    ),
    (
        "estia-panels",
        [
            panel_case(
                case_id="hexapod",
                panel_class="nicos_ess.estia.gui.panels.hexapod.HexapodPanel",
            ),
            panel_case(
                case_id="selene",
                panel_class="nicos_ess.estia.gui.panels.selene.SelenePanel",
                guiconfig_name="estia/selene.py",
                # SelenePanel hides itself outside expert mode.
                expert_mode=True,
            ),
        ],
    ),
    (
        "loki",
        [
            panel_case(
                case_id="sample-holder-config",
                panel_class="nicos_ess.loki.gui.sample_holder_config."
                "LokiSampleHolderPanel",
            ),
            panel_case(
                case_id="scriptbuilder",
                panel_class="nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel",
            ),
        ],
    ),
    (
        "loki-panels",
        [
            panel_case(
                case_id="spectrometer",
                panel_class="nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel",
                seed_daemon=seed_spectrometer_devices,
            ),
        ],
    ),
    (
        "odin",
        [
            panel_case(
                case_id="metrology-system",
                panel_class="nicos_ess.odin.gui.metrology_system.MetrologySystemPanel",
            ),
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


def collect_panels(item, found):
    if isinstance(item, panel):
        found.add(item.clsname)
    elif isinstance(item, (tuple, list)):
        for child in item:
            collect_panels(child, found)


def panels_in_guiconfig(source):
    # processGuiConfig also changes the global settings group, so this runs the
    # source in the same namespace without calling processGuiConfig.
    namespace = prepareGuiNamespace()
    exec(source, namespace)
    found = set()
    collect_panels(namespace["main_window"], found)
    collect_panels(namespace.get("windows", []), found)
    return found


def guiconfig_panels():
    """Map each panel class in the production guiconfigs to the files naming it."""
    root = Path(nicos_ess.__file__).parent
    panels = {}
    for path in sorted(root.rglob("guiconfig.py")):
        for name in panels_in_guiconfig(path.read_text()):
            panels.setdefault(name, []).append(str(path.relative_to(root)))
    return panels


GUICONFIG_PANELS = guiconfig_panels()

PANELS_WITHOUT_STARTUP_CASE = {
    "nicos.clients.gui.panels.errors.ErrorPanel": "core NICOS panel",
    "nicos.clients.gui.panels.logviewer.LogViewerPanel": "core NICOS panel",
    "nicos_ess.gui.panels.samples.SamplePanel": "tested in test_samples_panel.py",
    "nicos_ess.gui.panels.xray.XrayPanel": "tested in test_xray_panel.py",
    "nicos_ess.gui.panels.dashboard.Dashboard": "has no startup case yet",
    "nicos_ess.gui.panels.remote_editor.EditorPanel": "has no startup case yet",
    "nicos_ess.freia.gui.panels.hexapod.HexapodPanel": "has no startup case yet",
}


def test_guiconfig_panels_are_found():
    liveview = "nicos_ess.gui.panels.liveview.LiveViewPanel"
    scriptbuilder = "nicos_ess.loki.gui.scriptbuilder.LokiScriptBuilderPanel"
    assert "guiconfig.py" in GUICONFIG_PANELS.get(liveview, [])
    assert GUICONFIG_PANELS.get(scriptbuilder) == ["loki/guiconfig.py"]


def test_guiconfig_panels_are_read_the_way_the_gui_reads_them():
    source = """
first = 'a.Quoted'
main_window = vbox(
    # panel("a.CommentedOut"),
    panel(first),
    tabbed(("Tab", panel(
        "a.OnTheNextLine"))),
)
windows = [window("Extra", "icon", panel("a.InAWindow"))]
"""
    assert panels_in_guiconfig(source) == {"a.Quoted", "a.OnTheNextLine", "a.InAWindow"}


def test_every_guiconfig_panel_has_a_startup_case_or_a_reason():
    with_case = {case.panel_class for _, cases in STARTUP_CASE_GROUPS for case in cases}
    missing = {
        name: files
        for name, files in GUICONFIG_PANELS.items()
        if name not in with_case and name not in PANELS_WITHOUT_STARTUP_CASE
    }
    assert missing == {}


@pytest.mark.parametrize("name", sorted(GUICONFIG_PANELS))
def test_every_panel_named_in_a_guiconfig_imports(name):
    try:
        importString(name)
    except Exception as err:
        pytest.fail(f"{name} from {GUICONFIG_PANELS[name]} does not import: {err!r}")

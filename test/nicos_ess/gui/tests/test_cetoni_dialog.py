"""The Cetoni linked-pumping dialog, opened from the real DevicesPanel."""

from __future__ import annotations

import pytest

from nicos.core import oneof
from nicos_ess.gui.dialogs.cetoni_pump import CetoniLinkedDialog
from nicos_ess.loki.devices.cetoni_pump import CetoniPumpLinkedMode
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.devices.DevicesPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)


def param_info():
    # What the daemon sends once the device has read the choices from the IOC.
    info = {pn: p.serialize() for pn, p in CetoniPumpLinkedMode.parameters.items()}
    info["pump_mode"]["type"] = oneof("Manual", "Time")
    info["first_fill_syringe"]["type"] = oneof("SP1", "SP2")
    return info


@pytest.fixture
def dialog(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.add_device(
        DeviceSpec(
            name="linked_pumping",
            valuetype=str,
            params={
                "value": "Stopped",
                "unit": "",
                "status": (200, "idle"),
                "visibility": ("namespace", "devlist"),
                "description": "Linked pumping",
                "pump_mode": "Time",
                "max_dosing_time": 5.0,
                "first_fill_syringe": "SP2",
                "flowrate": 0.5,
                "flowrate_max": 2.0,
                "total_vol": 3.0,
            },
            param_info=param_info(),
        ),
        setup="cetoni_pumps",
        loaded=True,
    )
    fake_daemon.evals["session.getDevice('linked_pumping').classes"] = [
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpLinkedMode",
        "nicos.core.device.Moveable",
    ]
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: "linked_pumping" in panel._devinfo, timeout=2000)
    dialog = panel._open_control_dialog("linked_pumping")
    yield dialog
    dialog.close()


def test_opening_polls_volatile_params_and_shows_the_settings(dialog, fake_daemon):
    sent = fake_daemon.sent_scripts("eval")
    assert isinstance(dialog, CetoniLinkedDialog)
    assert "linked_pumping.asyncPollVolatileParams()" in sent
    assert "linked_pumping.pollParams()" not in sent
    assert dialog.mode_value.currentText() == "Time"
    assert dialog.time_value.text() == "5.0"
    assert dialog.time_value.isEnabled()
    assert dialog.first_fill_value.currentText() == "SP2"
    assert dialog.flowrate_value.text() == "0.5"
    assert dialog.vol_total_value.text() == "3.0"

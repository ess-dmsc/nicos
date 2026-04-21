"""Focused ControlDialog tests for the ESS devices panel."""

from __future__ import annotations

import pytest

pytest.importorskip("pytestqt")

from nicos.clients.gui.utils import dialogFromUi as real_dialog_from_ui
from nicos.core import params
from nicos.guisupport.qt import QDialog

import nicos_ess.gui.panels.devices as devices_panel_module

from test.nicos_ess.gui.doubles import DeviceSpec


guiconfig_name = "devices.py"


def _open_motor_control_dialog(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    device_spec,
):
    fake_daemon.add_device(device_spec, setup="instrument")

    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    return panel._open_control_dialog("motor")


def _capture_limits_dialog(monkeypatch):
    captured = {}

    def wrapped_dialog_from_ui(parent, uiname):
        dlg = real_dialog_from_ui(parent, uiname)
        
        def exec_and_capture():
            captured["max_range"] = (dlg.limitMinAbs.text(), dlg.limitMaxAbs.text())
            return QDialog.DialogCode.Rejected

        dlg.exec = exec_and_capture
        return dlg

    monkeypatch.setattr(devices_panel_module, "dialogFromUi", wrapped_dialog_from_ui)
    return captured


def _motor_device_spec(userlimits, hwuserlimits, abslimits, offset):
    return DeviceSpec(
            name="motor",
            params={
                "value": 1.0,
                "target": 1.0,
                "status": (200, ""),
                "visibility": ("namespace", "devlist"),
                "description": "test motor",
                "fmtstr": "%.1f",
                "unit": "mm",
                "fixed": False,
                "classes": [
                    "nicos.core.device.Readable",
                    "nicos.core.device.Moveable",
                    "nicos.core.mixins.HasLimits",
                    "nicos.core.mixins.HasOffset",
                    "nicos.core.mixins.CanDisable",
                    "nicos.devices.abstract.CanReference",
                ],
                "userlimits": userlimits,
                "hwuserlimits": hwuserlimits,
                "limitoffsets": (0.0, 0.0),
                "abslimits": abslimits,
                "offset": offset,
            },
            param_info={
                "userlimits": {
                    "type": params.limits,
                    "unit": "main",
                    "userparam": True,
                }
            },
            valuetype=float,
        )



@pytest.mark.parametrize(
    "userlimits, hwuserlimits, abslimits, offset, expected_max_range",
    [
        pytest.param(
            (0.0, 5.5),
            (0.0, 5.5),
            (-4.7, 0.8),
            0.8,
            ("0.0", "5.5"),
            id="inverted_epics_window",
        ),
        pytest.param(
            (0.0, 5.5),
            (0.0, 5.5),
            (0.0, 5.5),
            0.0,
            ("0.0", "5.5"),
            id="same_direction_window",
        ),
    ],
)
def test_epics_motor_limits_dialog_shows_hardware_user_window(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
    userlimits,
    hwuserlimits,
    abslimits,
    offset,
    expected_max_range,
):
    captured = _capture_limits_dialog(monkeypatch)
    motor_spec = _motor_device_spec(userlimits, hwuserlimits, abslimits, offset)
    control_dialog = _open_motor_control_dialog(
        gui_window_factory,
        fake_daemon,
        guiconfig_path,
        motor_spec,
    )
    qtbot.waitUntil(control_dialog.isVisible)

    control_dialog.on_actionSetLimits_triggered()

    assert captured["max_range"] == expected_max_range

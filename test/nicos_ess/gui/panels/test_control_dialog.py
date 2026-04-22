"""ControlDialog tests for the ESS devices panel."""

from __future__ import annotations

import pytest

from nicos.core import params
from nicos.guisupport.qt import QDialog

from test.nicos_ess.gui.doubles import DeviceSpec


guiconfig_name = "devices.py"

LIMIT_PARAM = {"type": params.limits, "unit": "main"}
LIMIT_CASES = [
    pytest.param(
        "positive direction with negative offset",
        -10.0,
        (-100.0, 150.0),  # diallimits
        (-90.0, 110.0),  # current userlimits
        (-110.0, 140.0),  # hwuserlimits shown as absolute user-coordinate limits
        id="positive-direction-negative-offset",
    ),
    pytest.param(
        "positive direction with positive offset",
        25.0,
        (-100.0, 150.0),  # diallimits
        (-55.0, 145.0),  # current userlimits
        (-75.0, 175.0),  # hwuserlimits shown as absolute user-coordinate limits
        id="positive-direction-positive-offset",
    ),
    pytest.param(
        "negative direction with negative offset",
        -10.0,
        (-100.0, 150.0),  # diallimits
        (-130.0, 70.0),  # current userlimits
        (-160.0, 90.0),  # hwuserlimits shown as absolute user-coordinate limits
        id="negative-direction-negative-offset",
    ),
    pytest.param(
        "negative direction with positive offset",
        25.0,
        (-100.0, 150.0),  # diallimits
        (-95.0, 105.0),  # current userlimits
        (-125.0, 125.0),  # hwuserlimits shown as absolute user-coordinate limits
        id="negative-direction-positive-offset",
    ),
]


def _fmt(limits):
    return tuple(f"{limit:.1f}" for limit in limits)


def _motor_spec(offset, diallimits, userlimits, hwuserlimits):
    return DeviceSpec(
        name="motor",
        valuetype=float,
        params=dict(
            visibility=("namespace", "devlist"),
            fmtstr="%.1f",
            classes=["nicos.core.device.Moveable", "nicos.core.mixins.HasLimits"],
            userlimits=userlimits,
            abslimits=diallimits,
            offset=offset,
            hwuserlimits=hwuserlimits,
        ),
        param_info={
            "userlimits": {**LIMIT_PARAM, "userparam": True},
            "hwuserlimits": {**LIMIT_PARAM, "userparam": False},
        },
    )


def _device_item(panel, name):
    for setup_index in range(panel.tree.topLevelItemCount()):
        setup_item = panel.tree.topLevelItem(setup_index)
        for device_index in range(setup_item.childCount()):
            item = setup_item.child(device_index)
            if item.text(panel.col_index["NAME"]) == name:
                return item
    raise AssertionError(f"device item {name!r} not found")


def _open_control_dialog(qtbot, panel, devname):
    item = _device_item(panel, devname)
    panel.tree.setCurrentItem(item)
    panel.tree.itemActivated.emit(item, panel.col_index["NAME"])
    ldevname = devname.lower()
    qtbot.waitUntil(lambda: ldevname in panel._control_dialogs, timeout=2000)
    return panel._control_dialogs[ldevname]


def _capture_exec(monkeypatch, qtbot):
    dialogs = []

    def fake_exec(dialog):
        qtbot.addWidget(dialog)
        dialogs.append(dialog)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    return dialogs


@pytest.mark.parametrize(
    ("case_description", "offset", "diallimits", "userlimits", "hwuserlimits"),
    LIMIT_CASES,
)
def test_limits_dialog_shows_motor_limits_in_user_coordinates(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
    case_description,
    offset,
    diallimits,
    userlimits,
    hwuserlimits,
):
    fake_daemon.add_device(
        _motor_spec(offset, diallimits, userlimits, hwuserlimits),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, panel, "motor")
    limits_dialogs = _capture_exec(monkeypatch, qtbot)

    control_dialog.actionSetLimits.trigger()

    qtbot.waitUntil(lambda: len(limits_dialogs) == 1, timeout=2000)
    limits_dialog = limits_dialogs[0]

    displayed_limits = (limits_dialog.limitMin.text(), limits_dialog.limitMax.text())
    displayed_hwlimits = (
        limits_dialog.limitMinAbs.text(),
        limits_dialog.limitMaxAbs.text(),
    )
    assert displayed_limits == _fmt(userlimits), case_description
    assert displayed_hwlimits == _fmt(hwuserlimits), case_description

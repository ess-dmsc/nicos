"""ControlDialog tests for the ESS devices panel."""

from __future__ import annotations

import pytest

from nicos.core import params
from nicos.guisupport.qt import QDialog, QDialogButtonBox

from test.nicos_ess.gui.doubles import DeviceSpec


guiconfig_name = "devices.py"

LIMIT_PARAM = {"type": params.limits, "unit": "main"}
EPICS_MOTOR_LIMIT_CASES = [
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

MOVEABLE_LIMIT_CASES = [
    pytest.param(
        "normal moveable without offset",
        None,
        (-100.0, 150.0),  # abslimits
        (-100.0, 150.0),  # current userlimits
        (-100.0, 150.0),  # expected absolute limits shown by the dialog
        id="normal-moveable-without-offset",
    ),
    pytest.param(
        "normal moveable with NICOS offset",
        10.0,  # offset
        (-100.0, 150.0),  # abslimits
        (-90.0, 120.0),  # current userlimits
        (-110.0, 140.0),  # expected absolute limits shown by the dialog
        id="normal-moveable-with-offset",
    ),
]


def _fmt(limits):
    return tuple(f"{limit:.1f}" for limit in limits)


def _epics_motor_spec(offset, diallimits, userlimits, hwuserlimits):
    return DeviceSpec(
        name="epicsmotor",
        valuetype=float,
        params=dict(
            visibility=("namespace", "devlist"),
            fmtstr="%.1f",
            classes=[
                "nicos.core.device.Moveable",
                "nicos.core.mixins.HasLimits",
                "nicos.core.mixins.HasOffset",
            ],
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


def _normal_moveable_spec(offset, abslimits, userlimits):
    classes = ["nicos.core.device.Moveable", "nicos.core.mixins.HasLimits"]
    params_ = dict(
        visibility=("namespace", "devlist"),
        fmtstr="%.1f",
        classes=classes,
        userlimits=userlimits,
        abslimits=abslimits,
    )
    if offset is not None:
        classes.append("nicos.core.mixins.HasOffset")
        params_["offset"] = offset
    return DeviceSpec(
        name="normalmoveable",
        valuetype=float,
        params=params_,
        param_info={
            "userlimits": {**LIMIT_PARAM, "userparam": True},
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


def _reset_button(dialog):
    for button in dialog.buttonBox.buttons():
        if dialog.buttonBox.buttonRole(button) == QDialogButtonBox.ButtonRole.ResetRole:
            return button
    raise AssertionError("reset button not found")


def _queued_codes(fake_daemon):
    return [args[1] for cmd, args in fake_daemon.command_log if cmd == "queue"]


@pytest.mark.parametrize(
    ("case_description", "offset", "diallimits", "userlimits", "hwuserlimits"),
    EPICS_MOTOR_LIMIT_CASES,
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
        _epics_motor_spec(offset, diallimits, userlimits, hwuserlimits),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, panel, "epicsmotor")
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


@pytest.mark.parametrize(
    ("case_description", "offset", "abslimits", "userlimits", "expected_abslimits"),
    MOVEABLE_LIMIT_CASES,
)
def test_limits_dialog_shows_normal_moveable_limits_in_user_coordinates(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
    case_description,
    offset,
    abslimits,
    userlimits,
    expected_abslimits,
):
    fake_daemon.add_device(
        _normal_moveable_spec(offset, abslimits, userlimits),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, panel, "normalmoveable")
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
    assert displayed_hwlimits == _fmt(expected_abslimits), case_description


def test_reset_limits_on_epics_motor_sets_userlimits_to_hwuserlimits(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
):
    fake_daemon.add_device(
        _epics_motor_spec(
            -10.0,
            (-100.0, 150.0),  # diallimits
            (-90.0, 110.0),  # current userlimits
            (-110.0, 140.0),  # hwuserlimits
        ),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, panel, "epicsmotor")
    limits_dialogs = _capture_exec(monkeypatch, qtbot)

    control_dialog.actionSetLimits.trigger()

    qtbot.waitUntil(lambda: len(limits_dialogs) == 1, timeout=2000)
    _reset_button(limits_dialogs[0]).click()

    assert _queued_codes(fake_daemon)[-1] == (
        "set(epicsmotor, 'userlimits', (-110.0, 140.0))"
    )


def test_reset_limits_on_normal_moveable_calls_resetlimits(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
):
    fake_daemon.add_device(
        _normal_moveable_spec(
            10.0,  # offset
            (-100.0, 150.0),  # abslimits
            (-90.0, 120.0),  # current userlimits
        ),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, panel, "normalmoveable")
    limits_dialogs = _capture_exec(monkeypatch, qtbot)

    control_dialog.actionSetLimits.trigger()

    qtbot.waitUntil(lambda: len(limits_dialogs) == 1, timeout=2000)
    _reset_button(limits_dialogs[0]).click()

    assert _queued_codes(fake_daemon)[-1] == "resetlimits(normalmoveable)"

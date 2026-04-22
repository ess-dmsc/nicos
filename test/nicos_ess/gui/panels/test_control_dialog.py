"""Focused ControlDialog tests for the ESS devices panel."""

from __future__ import annotations

import pytest

from nicos.core import params
from nicos.guisupport.qt import QDialog
from nicos_ess.devices.epics.pva.motor import EpicsMotor

from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.test_devices.epics_motor.helpers import (
    ASYMM_DIAL_LIMITS,
    OFFSET_CASES,
    TARGET_DIAL_USERLIMITS,
    user_limits_from_dial_limits,
)


guiconfig_name = "devices.py"


def _device_item(panel, name):
    for setup_index in range(panel.tree.topLevelItemCount()):
        setup_item = panel.tree.topLevelItem(setup_index)
        for device_index in range(setup_item.childCount()):
            item = setup_item.child(device_index)
            if item.text(panel.col_index["NAME"]) == name:
                return item
    raise AssertionError(f"device item {name!r} not found")


def _find_visible_dialog(window, title):
    for dialog in window.findChildren(QDialog):
        if dialog.windowTitle() == title and dialog.isVisible():
            return dialog
    return None


def _open_control_dialog(qtbot, window, panel, devname):
    item = _device_item(panel, devname)
    panel.tree.setCurrentItem(item)
    panel.tree.itemActivated.emit(item, panel.col_index["NAME"])
    title = f"Control {devname}"
    qtbot.waitUntil(
        lambda w=window, wanted=title: _find_visible_dialog(w, wanted) is not None,
        timeout=2000,
    )
    dialog = _find_visible_dialog(window, title)
    assert dialog is not None
    return dialog


def _capture_limits_dialog(monkeypatch, qtbot):
    captured = []

    def fake_exec(dialog):
        qtbot.addWidget(dialog)
        captured.append(dialog)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    return captured


def _class_names(cls):
    return [base.__module__ + "." + base.__name__ for base in cls.__mro__]


def _fmt_limits(limits):
    return tuple(f"{value:.1f}" for value in limits)


def _motor_device_spec(userlimits, abslimits, offset, direction):
    hwuserlimits = user_limits_from_dial_limits(direction, offset, *abslimits)
    limitoffsets = (
        userlimits[0] - hwuserlimits[0],
        userlimits[1] - hwuserlimits[1],
    )
    return DeviceSpec(
        name="motor",
        valuetype=float,
        params={
            "value": 1.0,
            "target": 1.0,
            "status": (200, ""),
            "visibility": ("namespace", "devlist"),
            "description": "test motor",
            "fmtstr": "%.1f",
            "unit": "mm",
            "fixed": False,
            "motorpv": "SIM:M1",
            # Mirror the actual EpicsMotor class hierarchy; the DIR-related
            # inverted-limits bug only exists for EPICS motor-record devices.
            "classes": _class_names(EpicsMotor),
            "userlimits": userlimits,
            "hwuserlimits": hwuserlimits,
            "limitoffsets": limitoffsets,
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
    )


@pytest.mark.parametrize("offset", OFFSET_CASES)
@pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
def test_limits_dialog_shows_epics_motor_user_space_bounds_for_direction_and_offset_cases(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
    direction,
    offset,
):
    abslimits = ASYMM_DIAL_LIMITS
    userlimits = user_limits_from_dial_limits(
        direction, offset, *TARGET_DIAL_USERLIMITS
    )
    expected_user_limits = _fmt_limits(userlimits)
    expected_absolute_limits = _fmt_limits(
        user_limits_from_dial_limits(direction, offset, *abslimits)
    )
    fake_daemon.add_device(
        _motor_device_spec(userlimits, abslimits, offset, direction),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, window, panel, "motor")
    captured = _capture_limits_dialog(monkeypatch, qtbot)

    control_dialog.actionSetLimits.trigger()

    qtbot.waitUntil(lambda: len(captured) == 1, timeout=2000)
    limits_dialog = captured[0]

    assert (
        limits_dialog.limitMin.text(),
        limits_dialog.limitMax.text(),
    ) == expected_user_limits
    assert (
        limits_dialog.limitMinAbs.text(),
        limits_dialog.limitMaxAbs.text(),
    ) == expected_absolute_limits

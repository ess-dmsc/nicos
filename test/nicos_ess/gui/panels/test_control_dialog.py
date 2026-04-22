"""Focused ControlDialog tests for the ESS devices panel."""

from __future__ import annotations

import pytest

from nicos.core import params
from nicos.guisupport.qt import QDialog
from nicos_ess.gui.panels import devices as devices_panel_module

from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.test_devices.epics_motor.helpers import (
    ASYMM_DIAL_LIMITS,
    OFFSET_CASES,
    TARGET_DIAL_USERLIMITS,
    user_limits_from_dial_limits,
)


guiconfig_name = "devices.py"
_MISSING = object()
_LIMITED_MOVEABLE_CLASSES = [
    "nicos.core.device.Moveable",
    "nicos.core.mixins.HasLimits",
]


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


def _capture_limits_dialog(monkeypatch, qtbot, results=None):
    captured = []
    results = list(results or [QDialog.DialogCode.Rejected])

    def fake_exec(dialog):
        qtbot.addWidget(dialog)
        captured.append(dialog)
        if results:
            return results.pop(0)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    return captured


def _fmt_limits(limits):
    return tuple(f"{value:.1f}" for value in limits)


def _limited_moveable_spec(
    userlimits,
    abslimits,
    offset,
    *,
    name="motor",
    namespace=True,
):
    device_params = {
        "value": 1.0,
        "target": 1.0,
        "status": (200, ""),
        "visibility": ("namespace", "devlist") if namespace else ("devlist",),
        "description": "test motor",
        "fmtstr": "%.1f",
        "unit": "mm",
        "fixed": False,
        "classes": _LIMITED_MOVEABLE_CLASSES,
        "userlimits": userlimits,
        "abslimits": abslimits,
    }
    if offset is not _MISSING:
        device_params["offset"] = offset

    return DeviceSpec(
        name=name,
        valuetype=float,
        params=device_params,
        param_info={
            "userlimits": {
                "type": params.limits,
                "unit": "main",
                "userparam": True,
            }
        },
    )


def _queued_codes(fake_daemon):
    return [args[1] for cmd, args in fake_daemon.command_log if cmd == "queue"]


def _button_with_text(dialog, text):
    for button in dialog.buttonBox.buttons():
        if button.text() == text:
            return button
    raise AssertionError(f"button {text!r} not found")


@pytest.mark.parametrize("offset", OFFSET_CASES)
@pytest.mark.parametrize("direction", ["Pos", "Neg"], ids=["dir_pos", "dir_neg"])
def test_limits_dialog_shows_user_space_bounds_for_direction_and_offset_cases(
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
        _limited_moveable_spec(userlimits, abslimits, offset),
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


@pytest.mark.parametrize(
    ("userlimits", "expected_absolute_limits"),
    [
        pytest.param(
            user_limits_from_dial_limits("Pos", 0.0, *TARGET_DIAL_USERLIMITS),
            user_limits_from_dial_limits("Pos", 0.0, *ASYMM_DIAL_LIMITS),
            id="same_direction",
        ),
        pytest.param(
            user_limits_from_dial_limits("Neg", 0.0, *TARGET_DIAL_USERLIMITS),
            user_limits_from_dial_limits("Neg", 0.0, *ASYMM_DIAL_LIMITS),
            id="swapped_direction",
        ),
    ],
)
def test_limits_dialog_derives_user_space_bounds_when_offset_parameter_is_absent(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
    userlimits,
    expected_absolute_limits,
):
    fake_daemon.add_device(
        _limited_moveable_spec(userlimits, ASYMM_DIAL_LIMITS, _MISSING),
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
        limits_dialog.limitMinAbs.text(),
        limits_dialog.limitMaxAbs.text(),
    ) == _fmt_limits(expected_absolute_limits)


def test_control_dialog_updates_user_limit_labels_from_cache_without_conversion(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    qtbot,
):
    initial_userlimits = user_limits_from_dial_limits(
        "Neg", 0.0, *TARGET_DIAL_USERLIMITS
    )
    updated_userlimits = (-110.0, 70.0)
    fake_daemon.add_device(
        _limited_moveable_spec(initial_userlimits, ASYMM_DIAL_LIMITS, _MISSING),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, window, panel, "motor")

    assert (
        control_dialog.limitMin.text(),
        control_dialog.limitMax.text(),
    ) == _fmt_limits(initial_userlimits)

    fake_daemon.push_cache("motor/userlimits", updated_userlimits, timestamp=100.0)

    qtbot.waitUntil(
        lambda: (
            control_dialog.limitMin.text(),
            control_dialog.limitMax.text(),
        )
        == _fmt_limits(updated_userlimits),
        timeout=2000,
    )


def test_limits_dialog_accepts_user_limits_inside_derived_swapped_absolute_bounds(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
):
    userlimits = user_limits_from_dial_limits("Neg", 0.0, *TARGET_DIAL_USERLIMITS)
    newlimits = (-140.0, 90.0)
    fake_daemon.add_device(
        _limited_moveable_spec(userlimits, ASYMM_DIAL_LIMITS, _MISSING),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, window, panel, "motor")
    _capture_limits_dialog(monkeypatch, qtbot, [QDialog.DialogCode.Accepted])
    monkeypatch.setattr(
        devices_panel_module.DeviceParamEdit,
        "getValue",
        lambda self: newlimits,
    )

    control_dialog.actionSetLimits.trigger()

    assert _queued_codes(fake_daemon)[-1] == (
        'set(motor, "userlimits", (-140.0, 90.0))'
    )


def test_limits_dialog_rejects_user_limits_outside_derived_swapped_absolute_bounds(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
):
    userlimits = user_limits_from_dial_limits("Neg", 0.0, *TARGET_DIAL_USERLIMITS)
    newlimits = (-90.0, 120.0)
    warnings = []
    fake_daemon.add_device(
        _limited_moveable_spec(userlimits, ASYMM_DIAL_LIMITS, _MISSING),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, window, panel, "motor")
    _capture_limits_dialog(
        monkeypatch,
        qtbot,
        [QDialog.DialogCode.Accepted, QDialog.DialogCode.Rejected],
    )
    monkeypatch.setattr(
        devices_panel_module.DeviceParamEdit,
        "getValue",
        lambda self: newlimits,
    )
    monkeypatch.setattr(
        devices_panel_module.QMessageBox,
        "warning",
        lambda *args: warnings.append(args),
    )

    control_dialog.actionSetLimits.trigger()

    assert len(warnings) == 1
    assert not any(
        code.startswith('set(motor, "userlimits",')
        for code in _queued_codes(fake_daemon)
    )


def test_limits_dialog_reset_button_sets_derived_absolute_limits_from_gui(
    gui_window_factory,
    fake_daemon,
    guiconfig_path,
    monkeypatch,
    qtbot,
):
    userlimits = user_limits_from_dial_limits("Neg", 0.0, *TARGET_DIAL_USERLIMITS)
    fake_daemon.add_device(
        _limited_moveable_spec(userlimits, ASYMM_DIAL_LIMITS, _MISSING),
        setup="instrument",
    )
    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    control_dialog = _open_control_dialog(qtbot, window, panel, "motor")
    captured = _capture_limits_dialog(monkeypatch, qtbot)

    control_dialog.actionSetLimits.trigger()

    qtbot.waitUntil(lambda: len(captured) == 1, timeout=2000)
    _button_with_text(captured[0], "Reset to maximum range").click()

    assert _queued_codes(fake_daemon)[-1] == (
        'set(motor, "userlimits", (-150.0, 100.0))'
    )

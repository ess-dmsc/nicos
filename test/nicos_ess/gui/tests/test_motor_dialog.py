"""The motor dialog, opened from the real DevicesPanel on the fake daemon."""

from __future__ import annotations

import pytest

from nicos.guisupport.qt import Qt
from nicos.protocols.cache import cache_dump
from nicos_ess.gui.dialogs.motor import MotorDialog
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    answer_dialogs,
    get_panel_by_class,
    set_device_value,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.devices.DevicesPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)

EPICS_MOTOR = "nicos_ess.devices.epics.pva.motor.EpicsMotor"
# Params taken from an error report which we are using to reproduce the issue in test.
BLADE_PARAMS = {
    "value": 1.0,
    "unit": "mm",
    "status": (200, ""),
    "visibility": ("namespace", "devlist"),
    "description": "Upper blade",
    "target": 1.0,
    "speed": 1.0,
    "offset": 0.8,
    "abslimits": (-4.7, 0.8),
    "hwuserlimits": (0.0, 5.5),
    "userlimits": (0.0, 5.5),
    "fmtstr": "%.3f",
}


@pytest.fixture
def open_dialog(gui_window_factory, fake_daemon, qtbot, c_locale):
    opened = []

    def _open(classes, **params):
        fake_daemon.add_device(
            DeviceSpec(
                name="blade", valuetype=float, params={**BLADE_PARAMS, **params}
            ),
            setup="slits",
            loaded=True,
        )
        fake_daemon.evals["session.getDevice('blade').classes"] = classes
        window = gui_window_factory(guiconfig_string=guiconfig_string)
        panel = get_panel_by_class(window, PANEL)
        qtbot.waitUntil(lambda: "blade" in panel._devinfo, timeout=2000)
        dlg = panel._open_control_dialog("blade")
        opened.append(dlg)
        return dlg

    yield _open
    for dlg in opened:
        dlg.close()


@pytest.fixture
def dialog(open_dialog):
    return open_dialog([EPICS_MOTOR, "nicos.core.device.Moveable"])


def open_limits_dialog(dialog, monkeypatch, fill=None, accept=False):
    shown = {}

    def read_and_fill(dlg):
        shown["range"] = (dlg.limitMinAbs.text(), dlg.limitMaxAbs.text())
        if fill is not None:
            fill(dlg)

    answer_dialogs(monkeypatch, read_and_fill, accept)
    dialog.on_btn_set_limits_clicked()
    return shown


def test_hardware_limits_are_the_record_user_window(dialog):
    assert isinstance(dialog, MotorDialog)
    assert dialog.txt_hw_limits_from.text() == "0.000"
    assert dialog.txt_hw_limits_to.text() == "5.500"


def test_limits_dialog_shows_record_window_as_maximum_range(dialog, monkeypatch):
    shown = open_limits_dialog(dialog, monkeypatch)
    assert shown["range"] == ("0.000", "5.500")


def test_accepted_limits_go_to_the_daemon(dialog, fake_daemon, monkeypatch, qtbot):
    open_limits_dialog(dialog, monkeypatch, accept=True)
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [("set", "blade", "userlimits", (0.0, 5.5))]


def test_reset_sets_userlimits_to_record_window(
    dialog, fake_daemon, monkeypatch, qtbot
):
    open_limits_dialog(dialog, monkeypatch, lambda dlg: dlg.btn_reset.click())
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [("set", "blade", "userlimits", (0.0, 5.5))]


def test_epics_motor_subclass_gets_motor_dialog(open_dialog):
    dlg = open_dialog(
        ["nicos_ess.devices.epics.pva.motor.SmaractPiezoMotor", EPICS_MOTOR]
    )
    assert isinstance(dlg, MotorDialog)


@pytest.mark.parametrize(
    "trigger, function",
    [
        (lambda dlg: dlg.btn_reset.click(), "reset"),
        (lambda dlg: dlg.actionHome.trigger(), "home"),
        (lambda dlg: dlg.actionRelease.trigger(), "release"),
        (lambda dlg: dlg.actionEnable.trigger(), "enable"),
        (lambda dlg: dlg.actionDisable.trigger(), "disable"),
    ],
)
def test_device_command_buttons(dialog, fake_daemon, qtbot, trigger, function):
    trigger(dialog)
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [(function, "blade")]


def test_relative_move_steps_from_current_value(dialog, fake_daemon, qtbot):
    qtbot.keyClicks(dialog.txt_rmove, "0.5")
    qtbot.mouseClick(dialog.btn_rmove_plus, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.btn_rmove_minus, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: len(fake_daemon.sent_calls()) == 2)
    assert fake_daemon.sent_calls() == [("maw", "blade", 1.5), ("maw", "blade", 0.5)]


def test_move_sends_typed_target(dialog, fake_daemon, qtbot):
    qtbot.keyClicks(dialog.txt_target, "2.5")
    qtbot.mouseClick(dialog.btn_move, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    [(function, device, target)] = fake_daemon.sent_calls()
    assert (function, device, float(target)) == ("move", "blade", 2.5)


def test_stop_is_not_queued_behind_running_script(dialog, fake_daemon, qtbot):
    qtbot.mouseClick(dialog.btn_stop, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls("exec")))
    assert fake_daemon.sent_calls("exec") == [("stop", "blade")]
    assert fake_daemon.sent_calls() == []


def test_adjust_offset_to_entered_value(dialog, fake_daemon, monkeypatch, qtbot):
    answer_dialogs(monkeypatch, lambda dlg: set_device_value(dlg, 2.0))
    dialog.btn_set_offset.click()
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [("adjust", "blade", 2.0)]


def test_cancelled_new_value_sends_nothing(dialog, fake_daemon, monkeypatch, qtbot):
    answer_dialogs(monkeypatch, accept=False)
    dialog.btn_set_offset.click()
    dialog.actionSetPosition.trigger()
    qtbot.wait(50)
    assert fake_daemon.sent_calls() == []


def test_set_hardware_position(dialog, fake_daemon, monkeypatch, qtbot):
    answer_dialogs(monkeypatch, lambda dlg: set_device_value(dlg, 2.0))
    dialog.actionSetPosition.trigger()
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [("blade.setPosition", 2.0)]


def test_set_hardware_position_creates_device_outside_namespace(
    open_dialog, fake_daemon, monkeypatch, qtbot
):
    dialog = open_dialog([EPICS_MOTOR], visibility=("devlist",))
    answer_dialogs(monkeypatch, lambda dlg: set_device_value(dlg, 2.0))
    dialog.actionSetPosition.trigger()
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [
        ("CreateDevice", "blade"),
        ("blade.setPosition", 2.0),
    ]


def test_fix_sends_reason(dialog, fake_daemon, monkeypatch, qtbot):
    monkeypatch.setattr(
        "nicos_ess.gui.dialogs.motor.QInputDialog.getText",
        lambda *args: ("blade is broken", True),
    )
    dialog.actionFix.trigger()
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [("fix", "blade", "blade is broken")]


def test_hardware_limits_follow_the_record(dialog):
    dialog.on_cache(float("inf"), "hwuserlimits", "=", cache_dump((1.0, 4.0)))
    assert dialog.txt_hw_limits_from.text() == "1.000"
    assert dialog.txt_hw_limits_to.text() == "4.000"


def test_unit_change_updates_unit_labels(dialog):
    dialog.on_cache(float("inf"), "unit", "=", cache_dump("deg"))
    assert dialog.txt_target_units.text() == "deg"
    dialog.on_cache(float("inf"), "unit", "=", "")
    assert dialog.txt_target_units.text() == ""

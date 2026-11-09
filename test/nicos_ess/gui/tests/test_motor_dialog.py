"""The motor dialog, opened from the real DevicesPanel on the fake daemon."""

from __future__ import annotations

import pytest

from nicos.guisupport.qt import QDialog
from nicos_ess.gui.dialogs.motor import MotorDialog
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.devices.DevicesPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)

# Params taken from an error report which we are using to reproduce the issue in test.
EPICS_MOTOR = "nicos_ess.devices.epics.pva.motor.EpicsMotor"
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
def open_dialog(gui_window_factory, fake_daemon, qtbot):
    opened = []

    def _open(classes):
        fake_daemon.add_device(
            DeviceSpec(name="blade", valuetype=float, params=dict(BLADE_PARAMS)),
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


def scripts(fake_daemon):
    return [args[1] for command, args in fake_daemon.command_log if command == "queue"]


def run_limits_dialog(dialog, monkeypatch, action):
    shown = {}

    def fake_exec(dlg):
        shown["range"] = (dlg.limitMinAbs.text(), dlg.limitMaxAbs.text())
        return action(dlg)

    monkeypatch.setattr(QDialog, "exec", fake_exec)
    dialog.on_btn_set_limits_clicked()
    return shown


def click_reset(dlg):
    dlg.btn_reset.click()
    return QDialog.DialogCode.Rejected


def test_hardware_limits_are_the_record_user_window(dialog):
    assert isinstance(dialog, MotorDialog)
    assert dialog.txt_hw_limits_from.text() == "0.000"
    assert dialog.txt_hw_limits_to.text() == "5.500"


def test_limits_dialog_shows_record_window_as_maximum_range(dialog, monkeypatch):
    shown = run_limits_dialog(
        dialog, monkeypatch, lambda dlg: QDialog.DialogCode.Rejected
    )
    assert shown["range"] == ("0.000", "5.500")


def test_accepted_limits_go_to_the_daemon(dialog, fake_daemon, monkeypatch, qtbot):
    run_limits_dialog(dialog, monkeypatch, lambda dlg: QDialog.DialogCode.Accepted)
    qtbot.waitUntil(lambda: any("userlimits" in s for s in scripts(fake_daemon)))
    assert any("(0.0, 5.5)" in s for s in scripts(fake_daemon))


def test_reset_sets_userlimits_to_record_window(
    dialog, fake_daemon, monkeypatch, qtbot
):
    run_limits_dialog(dialog, monkeypatch, click_reset)
    qtbot.waitUntil(lambda: any("userlimits" in s for s in scripts(fake_daemon)))
    assert not any("resetlimits" in s for s in scripts(fake_daemon))
    assert any("(0.0, 5.5)" in s for s in scripts(fake_daemon))


def test_epics_motor_subclass_gets_motor_dialog(open_dialog):
    dlg = open_dialog(
        ["nicos_ess.devices.epics.pva.motor.SmaractPiezoMotor", EPICS_MOTOR]
    )
    assert isinstance(dlg, MotorDialog)

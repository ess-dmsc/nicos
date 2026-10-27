"""The chopper dialog, opened from the real DevicesPanel on the fake daemon."""

from __future__ import annotations

import pytest

from nicos_ess.gui.dialogs.chopper import ChopperDialog
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.devices.DevicesPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)

PARK_CHOICES = ("Null", "ParkOpen", "ParkClosed", "ParkSP", "DisablePark")


@pytest.fixture
def dialog(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.add_device(
        DeviceSpec(
            name="mini_chopper",
            valuetype=tuple,
            params={
                "value": (14.0, 90.0),
                "unit": "Hz deg",
                "status": (200, "Rotating; Rotation: In Phase"),
                "visibility": ("namespace", "devlist"),
                "description": "The mini-chopper",
                "in_phase": "In phase",
                "total_delay": 17857142.86,
                "park_status": "Not Parked",
                "position": 0.0,
                "last_message": "Rotation: In Phase",
                "delay_mean": -230.4,
                "delay_stddev": 254.4,
                "delay_fwhm": 599.1,
            },
        ),
        setup="choppers",
        loaded=True,
    )
    device = "session.getDevice('mini_chopper')"
    fake_daemon.evals[f"{device}.classes"] = [
        "nicos_ess.devices.epics.chopper.EssChopper",
        "nicos.core.device.Moveable",
    ]
    fake_daemon.evals[f"{device}.parameters['park_command'].type.vals"] = PARK_CHOICES
    for key, value in {
        "mini_chopper/state": "Rotating",
        "mini_chopper/speed_readback": 14.0,
        "mini_chopper/speed_setpoint": 14.0,
        "mini_chopper/delay": 1e9 / 14 / 4,
    }.items():
        fake_daemon.set_cache(key, value)

    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: "mini_chopper" in panel._devinfo, timeout=2000)
    dialog = panel._open_control_dialog("mini_chopper")
    yield dialog
    dialog.close()


def scripts(fake_daemon):
    return [args[1] for command, args in fake_daemon.command_log if command == "queue"]


def test_the_disc_opens_a_chopper_dialog(dialog):
    assert isinstance(dialog, ChopperDialog)
    assert dialog.state.text() == "Rotating"
    assert dialog.status_text.text() == "Rotating; Rotation: In Phase"
    assert dialog.speed.text() == "14.000 Hz"
    assert dialog.phase.text() == "90.000 deg"
    assert dialog.readbacks["delay_stddev"].text() == "254.4 ns"
    assert dialog.readbacks["in_phase"].text() == "In phase"
    assert dialog.readbacks["position"].text() == "0.0 deg"


def test_the_park_choices_are_the_iocs(dialog):
    park = [dialog.park_choice.itemText(i) for i in range(dialog.park_choice.count())]
    assert tuple(park) == PARK_CHOICES


def test_cache_updates_reach_the_dialog(dialog, fake_daemon, qtbot):
    fake_daemon.push_cache("mini_chopper/speed_readback", 7.0, timestamp=10.0)
    fake_daemon.push_cache("mini_chopper/state", "Coasting", timestamp=10.0)
    fake_daemon.push_cache(
        "mini_chopper/status", (240, "Trip; Interlock"), timestamp=10.0
    )

    qtbot.waitUntil(lambda: dialog.speed.text() == "7.000 Hz", timeout=2000)
    qtbot.waitUntil(lambda: dialog.state.text() == "Coasting", timeout=2000)
    qtbot.waitUntil(
        lambda: dialog.status_text.text() == "Trip; Interlock", timeout=2000
    )


def test_the_buttons_send_the_commands(dialog, fake_daemon, qtbot):
    dialog.speed_target.setText("7")
    dialog.btn_speed.click()
    dialog.phase_target.setText("120.5")
    dialog.btn_phase.click()
    dialog.btn_stop.click()
    dialog.park_choice.setCurrentText("ParkClosed")
    dialog.btn_park.click()
    dialog.park_angle.setText("42")
    dialog.btn_park_angle.click()
    dialog.btn_reset.click()

    expected = [
        "move(mini_chopper.speed, 7.0)",
        "move(mini_chopper.phase, 120.5)",
        "move(mini_chopper.speed, 0)",
        "mini_chopper.park('ParkClosed')",
        "move(mini_chopper.position, 42.0)",
        "reset(mini_chopper)",
    ]
    qtbot.waitUntil(lambda: len(scripts(fake_daemon)) == len(expected), timeout=2000)
    assert scripts(fake_daemon) == expected


def test_nothing_is_sent_without_a_target_or_choice(dialog, fake_daemon):
    assert dialog.park_choice.currentIndex() == -1
    dialog.btn_speed.click()
    dialog.btn_phase.click()
    dialog.btn_park.click()
    dialog.btn_park_angle.click()

    assert scripts(fake_daemon) == []

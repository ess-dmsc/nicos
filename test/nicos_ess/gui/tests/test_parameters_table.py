"""What the device dialogs ask the daemon to poll, on the fake daemon."""

from __future__ import annotations

import pytest

from nicos_ess.gui.panels import parameters_table
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.devices.DevicesPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)


@pytest.fixture
def dialog(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.add_device(
        DeviceSpec(
            name="tas",
            valuetype=float,
            params={
                "value": 1.5,
                "unit": "mm",
                "status": (200, "idle"),
                "visibility": ("namespace", "devlist"),
                "description": "A device",
                "speed": 2.0,
                "classes": ["nicos.core.device.Moveable"],
            },
            param_info={
                "speed": {"userparam": True, "settable": True, "unit": "main/s"},
                "unit": {"userparam": True, "settable": False, "unit": None},
            },
        ),
        setup="motors",
        loaded=True,
    )
    device = "session.getDevice('tas')"
    fake_daemon.evals[f"{device}.classes"] = ["nicos.core.device.Moveable"]
    fake_daemon.evals[f"{device}.valueInfo()"] = ()
    fake_daemon.evals[f"{device}.pollParams()"] = None
    fake_daemon.evals[f"{device}.pollParams('speed')"] = None
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: "tas" in panel._devinfo, timeout=2000)
    dialog = panel._open_control_dialog("tas")
    yield dialog
    dialog.close()


def pick_from_context_menu(monkeypatch, table, param, label):
    def exec_(menu, *args):
        return next(a for a in menu.actions() if a.text() == label)

    monkeypatch.setattr(parameters_table.QMenu, "exec", exec_)
    item = table.paramItems[param]
    table.on_context_menu(table.tree_widget.visualItemRect(item).center())


def test_opening_the_dialog_polls_volatile_params_without_blocking(dialog, fake_daemon):
    sent = fake_daemon.sent_scripts("eval")
    assert "tas.asyncPollVolatileParams()" in sent
    assert "tas.pollParams()" not in sent


def test_refresh_polls_the_selected_parameter(dialog, fake_daemon, monkeypatch):
    pick_from_context_menu(monkeypatch, dialog.param_table, "speed", "Refresh")

    sent = fake_daemon.sent_scripts("eval")
    assert sent[-1] == "session.getDevice('tas').pollParams('speed')"


def test_refresh_all_polls_every_parameter(dialog, fake_daemon, monkeypatch):
    pick_from_context_menu(monkeypatch, dialog.param_table, "speed", "Refresh all")

    sent = fake_daemon.sent_scripts("eval")
    assert sent[-1] == "session.getDevice('tas').pollParams()"

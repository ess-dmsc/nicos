"""Tests for the real ESS Dashboard panel driven by the shared fake daemon."""

from __future__ import annotations

import pytest

from nicos.clients.base import ConnectionData
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from test.nicos_ess.gui.helpers import get_panel_by_class

DASHBOARD = "nicos_ess.gui.panels.dashboard.Dashboard"

guiconfig_string = f"""
main_window = vbox(
    panel("{DASHBOARD}"),
    panel("nicos_ess.gui.panels.console.ConsolePanel"),
)
windows = []
tools = []
options = {{
    "facility": "ess",
    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",
}}
"""


def _requests(fake_daemon, command):
    return [args for name, args in fake_daemon.command_log if name == command]


@pytest.mark.parametrize(
    "daemon_status, shown",
    [(STATUS_IDLE, "IDLE"), (STATUS_RUNNING, "RUNNING")],
    ids=["idle", "running"],
)
def test_dashboard_shows_the_status_from_one_getstatus(
    gui_window_factory, fake_daemon, daemon_status, shown
):
    fake_daemon.status = (daemon_status, -1)

    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, DASHBOARD)

    assert panel.status_text.text().strip() == shown
    assert len(_requests(fake_daemon, "getstatus")) == 1
    assert len(_requests(fake_daemon, "getmessages")) == 1
    assert len(_requests(fake_daemon, "getdataset")) == 1


def test_dashboard_shows_the_daemon_status_after_a_reconnect(
    gui_window_factory, fake_daemon, qtbot
):
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, DASHBOARD)

    event_thread = window.client.event_thread
    window.client.disconnect()
    qtbot.waitUntil(lambda: not event_thread.is_alive(), timeout=2000)
    assert panel.status_label.text() == "DISCONNECTED"

    fake_daemon.status = (STATUS_RUNNING, -1)
    window.client.connect(ConnectionData("fake", 0, "test", "test"))
    qtbot.waitUntil(lambda: window.client.isconnected, timeout=2000)

    assert panel.status_text.text().strip() == "RUNNING"

"""Tests for the real ESS ConsolePanel driven by the shared fake daemon."""

from __future__ import annotations

from logging import INFO

from nicos.clients.gui.utils import modePrompt
from nicos.core import MAINTENANCE, MASTER
from test.nicos_ess.gui.helpers import _minimal_guiconfig, get_panel_by_class


guiconfig_text = _minimal_guiconfig("nicos_ess.gui.panels.console.ConsolePanel")
panel_class = "nicos_ess.gui.panels.console.ConsolePanel"


def test_console_replays_backlog_and_reacts_to_live_events(
    gui_window_factory, fake_daemon, qtbot
):
    """Backlog queries and live daemon events should both reach the panel."""
    backlog_message = ("nicos", 1.0, INFO, "Backlog line\n", None, 1)
    live_message = ("nicos", 2.0, INFO, "Live line\n", None, 2)
    sim_message = ("nicos", 3.0, INFO, "Sim line\n", None, "0")

    fake_daemon.mode = MAINTENANCE
    fake_daemon.add_message(backlog_message)

    window = gui_window_factory(guiconfig=guiconfig_text)
    panel = get_panel_by_class(window, panel_class)

    qtbot.waitUntil(
        lambda p=panel: "Backlog line" in p.outView.getOutputString(), timeout=2000
    )
    assert panel.promptLabel.text() == modePrompt(MAINTENANCE)

    fake_daemon.push_message(live_message)
    fake_daemon.push_simmessage(sim_message)
    fake_daemon.push_mode(MASTER)

    qtbot.waitUntil(
        lambda p=panel: "Live line" in p.outView.getOutputString(), timeout=2000
    )
    qtbot.waitUntil(
        lambda p=panel: "Sim line" in p.outView.getOutputString(), timeout=2000
    )
    qtbot.waitUntil(
        lambda p=panel: p.promptLabel.text() == modePrompt(MASTER), timeout=2000
    )

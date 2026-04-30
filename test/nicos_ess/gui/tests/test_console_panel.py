"""Tests for the real ESS ConsolePanel driven by the shared fake daemon."""

from __future__ import annotations

from logging import INFO

from nicos.clients.gui.utils import modePrompt
from nicos.core import MAINTENANCE, MASTER
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_text,
)


guiconfig_text = single_panel_guiconfig_text(
    "nicos_ess.gui.panels.console.ConsolePanel"
)


def _daemon_message(text, *, timestamp, request_id):
    return ("nicos", timestamp, INFO, text, None, request_id)


def test_console_replays_backlog_and_reacts_to_live_events(
    gui_window_factory, fake_daemon, qtbot
):
    """Backlog queries and live daemon events should both reach the panel."""
    backlog_message = _daemon_message("Backlog line\n", timestamp=1.0, request_id=1)
    live_message = _daemon_message("Live line\n", timestamp=2.0, request_id=2)
    sim_message = _daemon_message("Sim line\n", timestamp=3.0, request_id="0")

    fake_daemon.mode = MAINTENANCE
    fake_daemon.add_message(backlog_message)

    window = gui_window_factory(guiconfig_text=guiconfig_text)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.console.ConsolePanel")

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

"""Tests for the real ESS ExpPanel driven by the shared fake daemon."""

from __future__ import annotations

from nicos.guisupport.qt import Qt
from test.nicos_ess.gui.doubles.fake_transport import EXP_PANEL_PROPOSAL_EVAL
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

EXP_PANEL = "nicos_ess.gui.panels.exp_panel.ExpPanel"
guiconfig_string = single_panel_guiconfig_string(EXP_PANEL)


def _proposal_evals(fake_daemon):
    return [
        args
        for command, args in fake_daemon.command_log
        if command == "eval" and args[0] == EXP_PANEL_PROPOSAL_EVAL
    ]


def test_connect_reads_the_proposal_info_once(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.set_cache("exp/propinfo", {"proposal": "123"})
    fake_daemon.set_cache("sample/samples", {})
    fake_daemon.evals[EXP_PANEL_PROPOSAL_EVAL] = ("123", "Title", [], [], "abort")

    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, EXP_PANEL)

    assert panel.proposalNum.text() == "123"
    assert len(_proposal_evals(fake_daemon)) == 1

    fake_daemon.evals[EXP_PANEL_PROPOSAL_EVAL] = ("456", "Other", [], [], "abort")
    fake_daemon.push_cache("exp/propinfo", {"proposal": "456"})
    qtbot.waitUntil(lambda: panel.proposalNum.text() == "456", timeout=2000)
    assert len(_proposal_evals(fake_daemon)) == 2


def test_apply_sends_the_edited_experiment_to_the_daemon(
    gui_window_factory, fake_daemon, qtbot
):
    new_experiment = (
        "Exp.new(title='New title', localcontacts=[], users=[], proposal='456')"
    )
    fake_daemon.evals[EXP_PANEL_PROPOSAL_EVAL] = ("123", "Old title", [], [], "abort")
    fake_daemon.evals[new_experiment] = None
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, EXP_PANEL)

    panel.proposalNum.clear()
    qtbot.keyClicks(panel.proposalNum, "456")
    panel.propTitle.clear()
    qtbot.keyClicks(panel.propTitle, "New title")
    qtbot.keyClick(panel.errorAbortBox, Qt.Key.Key_Space)
    qtbot.mouseClick(panel.btn_apply, Qt.MouseButton.LeftButton)

    assert ("eval", (new_experiment, False)) in fake_daemon.command_log
    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()), timeout=2000)
    assert fake_daemon.sent_calls() == [("SetErrorAbort", False)]

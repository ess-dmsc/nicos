"""Tests for the ESS SamplePanel driven by the shared fake daemon."""

import pytest

from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.samples.SamplePanel"
SAMPLES = [
    {"samplename": "name1", "property1": "value1"},
    {"samplename": "name2"},
]


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.evals["session.experiment.get_samples()"] = SAMPLES
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: panel.list.count() == len(SAMPLES))
    return panel


def test_selecting_a_sample_shows_its_name_and_properties(panel):
    panel.list.setCurrentRow(0)

    assert panel.txt_sample_name.text() == "name1"
    assert panel.table.item(0, 0).text() == "property1"
    assert panel.table.item(0, 1).text() == "value1"


def test_apply_sends_edited_samples_to_daemon(panel, fake_daemon, qtbot):
    panel.list.setCurrentRow(0)

    panel.table.item(0, 1).setText("value2")
    panel.btn_apply_changes.click()

    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [
        (
            "Exp.sample.set_samples",
            {
                0: {"samplename": "name1", "property1": "value2"},
                1: {"samplename": "name2"},
            },
        )
    ]


def test_discard_changes_resets_sample_properties(panel):
    panel.list.setCurrentRow(0)
    panel.table.item(0, 1).setText("value2")

    panel.btn_discard_changes.click()

    assert panel.table.item(0, 1).text() == "value1"


def test_discard_changes_resets_sample_name(panel):
    panel.list.setCurrentRow(0)
    panel.txt_sample_name.textEdited.emit("new_name")
    assert panel.list.item(0).text() == "new_name"

    panel.btn_discard_changes.click()

    assert panel.txt_sample_name.text() == "name1"
    assert panel.list.item(0).text() == "name1"


def test_apply_and_discard_only_shown_when_there_are_changes(panel):
    panel.list.setCurrentRow(0)

    assert panel.btn_apply_changes.isHidden()
    assert panel.btn_discard_changes.isHidden()

    panel.txt_sample_name.textEdited.emit("new_name")

    assert not panel.btn_apply_changes.isHidden()
    assert not panel.btn_discard_changes.isHidden()

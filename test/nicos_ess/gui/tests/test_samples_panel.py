"""Tests for the ESS SamplePanel driven by the shared fake daemon."""

import pytest

from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.samples.SamplePanel"
SAMPLES = [
    {"name": "name1", "property1": "value1"},
    {"name": "name2"},
]


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.evals["session.experiment.get_samples()"] = SAMPLES
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: panel.tree.topLevelItemCount() == len(SAMPLES))
    return panel


def test_selecting_a_sample_shows_its_name_and_properties(panel):
    panel.tree.setCurrentItem(panel.tree.topLevelItem(0))

    assert panel.sample_edit.text() == "name1"
    assert panel.table.item(0, 0).text() == "property1"
    assert panel.table.item(0, 1).text() == "value1"


def test_apply_sends_edited_samples_to_daemon(panel, fake_daemon, qtbot):
    panel.tree.setCurrentItem(panel.tree.topLevelItem(0))

    panel.table.item(0, 1).setText("value2")
    panel.btn_apply_changes.click()

    qtbot.waitUntil(lambda: bool(fake_daemon.sent_calls()))
    assert fake_daemon.sent_calls() == [
        (
            "Exp.set_samples",
            [{"name": "name1", "property1": "value2"}, {"name": "name2"}],
        )
    ]

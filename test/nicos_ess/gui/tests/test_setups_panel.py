"""Tests for plug-and-play visibility in the ESS SetupsPanel."""

from __future__ import annotations

from nicos.guisupport.qt import Qt
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.setups.SetupsPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)


def _visible_pnp_setups(panel):
    return {
        panel.pnpSetups.item(i).text()
        for i in range(panel.pnpSetups.count())
        if not panel.pnpSetups.item(i).isHidden()
    }


def _open_panel(gui_window_factory, fake_daemon):
    for name in ("lakeshore", "magnet"):
        fake_daemon.add_setup(name, group="plugplay")
    fake_daemon.add_setup("julabo", group="plugplay", loaded=True)
    fake_daemon.set_cache("se_presence/value", ["lakeshore"])
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    return get_panel_by_class(window, PANEL)


def test_present_and_loaded_plugplay_setups_are_listed(
    gui_window_factory, fake_daemon, qtbot
):
    panel = _open_panel(gui_window_factory, fake_daemon)

    qtbot.waitUntil(lambda: panel.pnpSetups.count() == 3, timeout=2000)
    assert _visible_pnp_setups(panel) == {"julabo", "lakeshore"}


def test_presence_updates_change_the_list(gui_window_factory, fake_daemon, qtbot):
    panel = _open_panel(gui_window_factory, fake_daemon)
    qtbot.waitUntil(lambda: panel.pnpSetups.count() == 3, timeout=2000)

    fake_daemon.push_cache("se_presence/value", ["magnet"])

    qtbot.waitUntil(
        lambda: _visible_pnp_setups(panel) == {"julabo", "magnet"}, timeout=2000
    )


def test_loaded_and_ticked_setups_stay_listed_when_equipment_goes(
    gui_window_factory, fake_daemon, qtbot
):
    panel = _open_panel(gui_window_factory, fake_daemon)
    qtbot.waitUntil(lambda: panel.pnpSetups.count() == 3, timeout=2000)
    lakeshore = panel.pnpSetups.findItems("lakeshore", Qt.MatchFlag.MatchExactly)[0]
    lakeshore.setCheckState(Qt.CheckState.Checked)

    fake_daemon.push_cache("se_presence/value", [])

    qtbot.waitUntil(
        lambda: _visible_pnp_setups(panel) == {"julabo", "lakeshore"}, timeout=2000
    )


def test_clicking_a_plugplay_setup_offers_its_aliases(
    gui_window_factory, fake_daemon, qtbot
):
    fake_daemon.add_setup(
        "julabo",
        group="plugplay",
        alias_config={"T": {"T_julabo": 100}},
    )
    fake_daemon.set_cache("se_presence/value", ["julabo"])
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: panel.pnpSetups.count() == 1, timeout=2000)
    julabo = panel.pnpSetups.item(0)
    julabo.setCheckState(Qt.CheckState.Checked)

    panel.pnpSetups.itemClicked.emit(julabo)

    assert "T" in panel._aliasWidgets

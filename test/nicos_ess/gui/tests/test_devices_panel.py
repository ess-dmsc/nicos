"""Tests for the real ESS DevicesPanel driven by the shared fake daemon."""

from __future__ import annotations

from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_text,
)


guiconfig_text = single_panel_guiconfig_text(
    "nicos_ess.gui.panels.devices.DevicesPanel"
)

VISIBLE_DEVICE_PARAMS = {
    "value": 1.0,
    "status": (200, ""),
    "visibility": ("namespace", "devlist"),
}
FORMATTED_VALUE_PARAMS = {
    **VISIBLE_DEVICE_PARAMS,
    "fmtstr": "%.1f",
    "unit": "mm",
}


def _tas_device(params):
    return DeviceSpec(name="tas", valuetype=float, params=params)


def _setup_item(panel, name):
    for index in range(panel.tree.topLevelItemCount()):
        item = panel.tree.topLevelItem(index)
        if item.text(panel.col_index["NAME"]) == name:
            return item
    raise AssertionError(f"setup item {name!r} not found")


def _device_item(panel, name):
    for setup_index in range(panel.tree.topLevelItemCount()):
        setup_item = panel.tree.topLevelItem(setup_index)
        for device_index in range(setup_item.childCount()):
            item = setup_item.child(device_index)
            if item.text(panel.col_index["NAME"]) == name:
                return item
    raise AssertionError(f"device item {name!r} not found")


def test_device_appears_after_connect(gui_window_factory, fake_daemon, qtbot):
    """A device registered before connect shows up in the visible tree."""
    fake_daemon.add_device(
        _tas_device(VISIBLE_DEVICE_PARAMS),
        setup="instrument",
        loaded=True,
    )

    window = gui_window_factory(guiconfig_text=guiconfig_text)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.devices.DevicesPanel")

    qtbot.waitUntil(lambda p=panel: p.tree.topLevelItemCount() == 1, timeout=2000)

    setup_item = _setup_item(panel, "instrument")
    assert setup_item.childCount() == 1
    assert setup_item.child(0).text(panel.col_index["NAME"]) == "tas"


def test_cache_event_updates_panel(gui_window_factory, fake_daemon, qtbot):
    """Cache events flow through the real event thread into the visible tree."""
    fake_daemon.add_device(
        _tas_device(FORMATTED_VALUE_PARAMS),
        setup="instrument",
        loaded=True,
    )

    window = gui_window_factory(guiconfig_text=guiconfig_text)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.devices.DevicesPanel")
    item = _device_item(panel, "tas")

    # These exact strings prove the seeded fmtstr/unit are honored.
    qtbot.waitUntil(
        lambda tree_item=item: tree_item.text(panel.col_index["VALUE"]) == "1.0 mm",
        timeout=2000,
    )

    fake_daemon.push_cache("tas/value", 7.5, timestamp=100.0)

    # These exact strings prove the seeded fmtstr/unit are honored.
    qtbot.waitUntil(
        lambda tree_item=item: tree_item.text(panel.col_index["VALUE"]) == "7.5 mm",
        timeout=2000,
    )

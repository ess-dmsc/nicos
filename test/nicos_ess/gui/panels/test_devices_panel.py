"""Tests for the real ESS DevicesPanel driven by the shared fake daemon."""

from __future__ import annotations

from test.nicos_ess.gui.doubles import DeviceSpec


guiconfig_name = "devices.py"


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


def test_device_appears_after_connect(
    gui_window_factory, fake_daemon, guiconfig_path, qtbot
):
    """A device registered before connect shows up in the visible tree."""
    fake_daemon.add_device(
        DeviceSpec(
            name="tas",
            valuetype=float,
            params={
                "value": 1.0,
                "status": (200, ""),
                "visibility": ("namespace", "devlist"),
            },
        ),
        setup="instrument",
    )

    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")

    qtbot.waitUntil(lambda p=panel: p.tree.topLevelItemCount() == 1, timeout=2000)

    setup_item = _setup_item(panel, "instrument")
    assert setup_item.childCount() == 1
    assert setup_item.child(0).text(panel.col_index["NAME"]) == "tas"


def test_cache_event_updates_panel(
    gui_window_factory, fake_daemon, guiconfig_path, qtbot
):
    """Cache events flow through the real event thread into the visible tree."""
    fake_daemon.add_device(
        DeviceSpec(
            name="tas",
            valuetype=float,
            params={
                "value": 1.0,
                "status": (200, ""),
                "visibility": ("namespace", "devlist"),
                "fmtstr": "%.1f",
                "unit": "mm",
            },
        ),
        setup="instrument",
    )

    window = gui_window_factory(guiconfig_path=guiconfig_path)
    panel = window.getPanel("Devices")
    item = _device_item(panel, "tas")

    qtbot.waitUntil(
        lambda tree_item=item: tree_item.text(panel.col_index["VALUE"]) == "1.0 mm",
        timeout=2000,
    )

    fake_daemon.push_cache("tas/value", 7.5, timestamp=100.0)

    qtbot.waitUntil(
        lambda tree_item=item: tree_item.text(panel.col_index["VALUE"]) == "7.5 mm",
        timeout=2000,
    )

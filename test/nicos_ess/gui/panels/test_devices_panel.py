"""Tests for the real ESS DevicesPanel driven by the shared fake daemon."""

from __future__ import annotations

import pytest

pytest.importorskip("pytestqt")

from test.nicos_ess.gui.doubles import DeviceSpec


guiconfig_name = "devices.py"


def test_device_appears_after_connect(gui_window_factory, fake_daemon, guiconfig_path):
    """A device registered before connect shows up in the panel tree."""
    fake_daemon.add_device(
        DeviceSpec(
            name="tas",
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

    assert "tas" in panel._devitems
    assert panel._dev2setup.get("tas") == "instrument"


def test_cache_event_updates_panel(
    gui_window_factory, fake_daemon, guiconfig_path, qtbot
):
    """Cache events flow through the real event thread into the panel slot."""
    fake_daemon.add_device(
        DeviceSpec(
            name="tas",
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

    fake_daemon.push_cache("tas/value", 7.5, timestamp=100.0)

    qtbot.waitUntil(lambda: panel._devinfo["tas"].value == 7.5, timeout=2000)

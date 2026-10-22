"""The real ChopperPanel driven by the shared fake daemon: cache keys to the drawing."""

from __future__ import annotations

import numpy as np
import pytest

from nicos_ess.devices.chopper_math import parked_rotation_deg
from nicos_ess.gui.panels.chopper import ALL_CHOPPERS, delay_error_stats
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.gui.panels.chopper.ChopperPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)

# HEIMDAL TPSC-102, as a controller's get_chopper_gui_info() returns it.
INFO = {
    "chopper": "tpsc",
    "speed_key": "tpsc_speed/value",
    "total_delay_key": "tpsc_total_delay/value",
    "park_angle_key": "tpsc_park_angle/value",
    "delay_errors_key": "tpsc_delay_errors/raw_errors",
    "slit_edges": [[0.0, 5.2]],
    "beam_position": 15.2,
    "resolver_sign": 1,
    "tdc_resolver_position": 341.9,
    "guide_position": "DOWN",
    "legacy_spd_sign": True,
    "visual_geometry_verified": False,
}


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.evals[ALL_CHOPPERS] = {"tpsc": dict(INFO)}
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: len(panel.chopper_widget.chopper_data) == 1, timeout=2000)
    return panel


def _rotation(panel):
    return panel.chopper_widget.rotation(panel.chopper_widget.chopper_data[0])


def test_cache_values_drive_the_drawing(panel, fake_daemon, qtbot):
    fake_daemon.push_cache("tpsc_speed/value", 0.0, timestamp=1.0)
    fake_daemon.push_cache("tpsc_park_angle/value", 329.3, timestamp=1.0)
    parked = parked_rotation_deg(INFO, 329.3)
    qtbot.waitUntil(lambda: _rotation(panel) == pytest.approx(parked), timeout=2000)

    # Spinning: the phase that centres the window (lab phase 18.85 minus 6.25 lag).
    fake_daemon.push_cache("tpsc_speed/value", 70.0, timestamp=2.0)
    delay_ns = 12.6 / 360.0 / 70.0 * 1e9
    fake_daemon.push_cache("tpsc_total_delay/value", delay_ns, timestamp=2.0)
    qtbot.waitUntil(lambda: _rotation(panel) == pytest.approx(parked), timeout=2000)

    fake_daemon.push_cache("tpsc_speed/value", None, timestamp=3.0)
    qtbot.waitUntil(lambda: _rotation(panel) is None, timeout=2000)


def test_values_are_restored_after_a_reconnect(panel, fake_daemon, qtbot):
    """As seen with the real daemon: on reconnect the client re-sends the registered
    keys before the panel has reloaded its choppers, so those values are dropped."""
    fake_daemon.push_cache("tpsc_speed/value", 0.0, timestamp=1.0)
    fake_daemon.push_cache("tpsc_park_angle/value", 329.3, timestamp=1.0)
    qtbot.waitUntil(lambda: _rotation(panel) is not None, timeout=2000)

    panel.on_client_disconnect()
    for key in ("tpsc_speed/value", "tpsc_park_angle/value"):
        panel.on_keyChange(key, fake_daemon.cache[key], 2.0, False)  # too early
    fake_daemon.evals[ALL_CHOPPERS] = {"tpsc": dict(INFO)}  # the daemon sends copies
    panel._load_choppers()

    assert _rotation(panel) == pytest.approx(parked_rotation_deg(INFO, 329.3))


def test_unverified_geometry_is_announced(panel):
    warning = panel._unverified_geometry_warning
    assert not warning.isHidden()
    assert "tpsc" in warning.text()


def test_delay_errors_reach_the_selected_disc(panel, fake_daemon, qtbot):
    panel.chopper_widget._selected_chopper = "tpsc"
    samples = np.array([0.0, 100.0, 100.0, 200.0, 400.0])
    fake_daemon.push_cache("tpsc_delay_errors/raw_errors", samples, timestamp=5.0)
    qtbot.waitUntil(lambda: "tpsc" in panel._latest, timeout=2000)
    assert panel._latest["tpsc"]["mean"] == pytest.approx(samples.mean())
    assert list(panel._trends["tpsc"])[-1][0] == 5.0


def test_delay_error_stats():
    stats = delay_error_stats([0.0, 100.0, 100.0, 200.0, 400.0])
    assert stats["mean"] == pytest.approx(160.0)
    assert stats["stddev"] == pytest.approx(np.std([0, 100, 100, 200, 400]))
    assert list(stats["y"]) == [1, 2, 1, 1]
    assert stats["fwhm"] == pytest.approx(400.0)
    assert delay_error_stats([]) is None
    single = delay_error_stats([50.0, 50.0])
    assert list(single["y"]) == [2]
    assert single["fwhm"] == pytest.approx(100.0)


# The same disc, as an EssChopper's get_chopper_gui_info() returns it.
ESS_CHOPPER_INFO = {
    **INFO,
    "speed_key": "tpsc/speed_readback",
    "total_delay_key": "tpsc/total_delay",
    "park_angle_key": "tpsc/park_position",
    "delay_errors_key": None,
}


def test_an_ess_chopper_drives_the_drawing(gui_window_factory, fake_daemon, qtbot):
    fake_daemon.evals[ALL_CHOPPERS] = {"tpsc": dict(ESS_CHOPPER_INFO)}
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(lambda: len(panel.chopper_widget.chopper_data) == 1, timeout=2000)

    fake_daemon.push_cache("tpsc/speed_readback", 0.0, timestamp=1.0)
    fake_daemon.push_cache("tpsc/park_position", 329.3, timestamp=1.0)
    parked = parked_rotation_deg(ESS_CHOPPER_INFO, 329.3)
    qtbot.waitUntil(lambda: _rotation(panel) == pytest.approx(parked), timeout=2000)

    fake_daemon.push_cache("tpsc/speed_readback", 70.0, timestamp=2.0)
    delay_ns = 12.6 / 360.0 / 70.0 * 1e9
    fake_daemon.push_cache("tpsc/total_delay", delay_ns, timestamp=2.0)
    qtbot.waitUntil(lambda: _rotation(panel) == pytest.approx(parked), timeout=2000)

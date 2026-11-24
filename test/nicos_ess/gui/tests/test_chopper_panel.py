"""The real ChopperPanel driven by the shared fake daemon: cache keys to the drawing."""

from __future__ import annotations

import numpy as np
import pytest

from nicos.guisupport.qt import Qt
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


SAMPLES = np.array([0.0, 100.0, 100.0, 200.0, 400.0])
PEAKED = np.array([50, 250, 250, 250, 250, 350, 350, 350, 350, 550], dtype=float)


def _click_tpsc(panel, qtbot):
    centres, _radius = panel.chopper_widget.layout_discs()
    qtbot.mouseClick(
        panel.chopper_widget, Qt.MouseButton.LeftButton, pos=centres[0].toPoint()
    )
    assert panel.histogram.name == "Delay errors of tpsc"


def _push_delay_errors(panel, fake_daemon, qtbot, samples, timestamp):
    fake_daemon.push_cache("tpsc_delay_errors/raw_errors", samples, timestamp=timestamp)
    qtbot.waitUntil(
        lambda: (
            panel.histogram.received == timestamp
            and panel.histogram.frame.data.sum() == len(samples)
        ),
        timeout=2000,
    )


def test_delay_errors_fill_the_histogram_of_the_clicked_disc(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 5.0)
    assert list(panel.histogram.frame.data) == [1, 2, 1, 1]
    facts = panel.histogram.frame.meta["facts"]
    assert facts[0] == "mean 160 ns"
    assert panel.trend.name == "Delay error trend of tpsc"


def test_marks_show_the_mean_and_one_deviation_either_side(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 5.0)
    mean, spread = SAMPLES.mean(), SAMPLES.std()
    assert [mark.value() for mark in panel.marks] == pytest.approx(
        [mean, mean - spread, mean + spread]
    )
    assert all(mark.isVisible() for mark in panel.marks)


def test_fwhm_fill_covers_the_bins_above_half_maximum(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    _push_delay_errors(panel, fake_daemon, qtbot, PEAKED, 5.0)
    assert list(panel.fwhm.xData) == [200, 300, 400]
    assert list(panel.fwhm.yData) == [4, 4]
    assert panel.fwhm.isVisible()


def test_trend_uses_the_right_axis_for_the_spread(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 5.0)
    assert list(panel.trend.overlay_curves) == ["std. dev.", "FWHM"]
    assert panel.trend.plot.getAxis("right").isVisible()


def test_old_data_is_flagged_in_the_tooltip(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    # The timestamps are from 1970, so the data counts as old.
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 5.0)
    for view in (panel.histogram, panel.trend):
        assert "h old" in view.title_item.toolTip()


def test_period_follows_the_readings(panel, fake_daemon, qtbot):
    _click_tpsc(panel, qtbot)
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 5.0)
    assert panel.histogram.period == panel.trend.period == 0
    _push_delay_errors(panel, fake_daemon, qtbot, SAMPLES, 15.0)
    assert panel.histogram.period == panel.trend.period == 10


def test_delay_error_stats():
    stats = delay_error_stats([0.0, 100.0, 100.0, 200.0, 400.0])
    assert stats["mean"] == pytest.approx(160.0)
    assert stats["stddev"] == pytest.approx(np.std([0, 100, 100, 200, 400]))
    assert list(stats["y"]) == [1, 2, 1, 1]
    assert list(stats["edges"]) == [0, 100, 200, 300, 400]
    assert stats["fwhm"] == pytest.approx(400.0)
    single = delay_error_stats([50.0, 50.0])
    assert list(single["y"]) == [2]
    assert single["fwhm"] == pytest.approx(100.0)


@pytest.mark.parametrize(
    "samples",
    [
        [],
        [np.nan],
        ["a", 100.0],
        [100.0, [2.0]],
        [{"x": 1}],
        [10**400],
        [-1e308, 1e308],
        [5e24 + i for i in range(9)],
    ],
)
def test_samples_without_a_real_delay_error_give_no_stats(samples):
    assert delay_error_stats(samples) is None


@pytest.mark.parametrize(
    "speed", ["fast", 10**400, [1, 2]], ids=["text", "huge", "list"]
)
def test_a_speed_that_is_not_a_number_is_unknown(panel, fake_daemon, qtbot, speed):
    fake_daemon.push_cache("tpsc_speed/value", 0.0, timestamp=1.0)
    fake_daemon.push_cache("tpsc_park_angle/value", 329.3, timestamp=1.0)
    qtbot.waitUntil(lambda: _rotation(panel) is not None, timeout=2000)

    fake_daemon.push_cache("tpsc_speed/value", speed, timestamp=2.0)
    qtbot.waitUntil(lambda: _rotation(panel) is None, timeout=2000)


def test_fwhm_counts_only_the_bins_above_half_maximum():
    peaked = delay_error_stats(PEAKED)
    assert list(peaked["y"]) == [1, 0, 4, 4, 0, 1]
    assert peaked["fwhm"] == pytest.approx(200.0)
    assert (peaked["left"], peaked["right"]) == (200, 400)


def test_bins_stay_on_a_fixed_grid():
    assert list(delay_error_stats([30.0, 270.0])["edges"]) == [0, 100, 200, 300]


def test_bins_cover_only_the_bulk_of_the_samples():
    rng = np.random.default_rng(0)
    stray = delay_error_stats([*rng.normal(0, 300, 1000), -3e6, 4e6])
    assert stray["outside"] == 2
    assert stray["edges"][0] > -1e4
    assert stray["edges"][-1] < 1e4
    assert 600 < stray["fwhm"] < 800  # The FWHM of a Gaussian is 2.35 σ.


# The same disc, as an EssChopper's get_chopper_gui_info() returns it.
ESS_CHOPPER_INFO = {
    **INFO,
    "speed_key": "tpsc/speed_readback",
    "total_delay_key": "tpsc/total_delay",
    "park_angle_key": "tpsc/park_position",
    "delay_errors_key": "tpsc/delay_errors",
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

    panel.chopper_widget._selected_chopper = "tpsc"
    samples = np.array([0.0, 100.0, 100.0, 200.0, 400.0])
    fake_daemon.push_cache("tpsc/delay_errors", samples, timestamp=3.0)
    qtbot.waitUntil(lambda: "tpsc" in panel._latest, timeout=2000)
    assert panel._latest["tpsc"]["mean"] == pytest.approx(samples.mean())

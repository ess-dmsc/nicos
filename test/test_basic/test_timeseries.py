"""Exercise downsampling through the production history buffer."""

from pathlib import Path
from time import time

import numpy as np
import pytest

from nicos.guisupport.timeseries import TimeSeries


class SeriesUpdates:
    """Record the signal payload without needing a GUI or event loop."""

    def __init__(self):
        self.timeSeriesUpdate = self
        self.count = 0
        self.last_series = None

    def emit(self, series):
        self.count += 1
        self.last_series = series


@pytest.mark.parametrize("count", [128000, 128001, 320001])
@pytest.mark.parametrize("pattern", ["line", "spike"])
def test_full_history_buffer_keeps_accepting_values(count, pattern):
    updates = SeriesUpdates()
    # ESS history.View uses window=None when slidingWindow is unchecked, and
    # forwards cache timestamps/values through newValue() to addValue(). Use
    # the production limits: growth from 500 reaches 128000 before rollover.
    series = TimeSeries("temperature", 2, None, None, updates)
    series.initEmpty()
    start = 1_700_000_000.0
    spike_index = 64000

    # Two-second cache updates are replayed without waiting three days in real
    # time. A slow temperature ramp or brief excursion is valid device data.
    # The background changes every sample: the cache suppresses identical values.
    for index in range(count):
        value = (
            100 if pattern == "spike" and index == spike_index else 20 + index * 0.0001
        )
        series.addValue(start + index * 2, float(value))

    assert updates.count == count
    assert updates.last_series is series
    assert series.real_n == series.n
    assert 0 < series.n <= series.data.shape[0]
    assert series.data.shape[0] <= 2 * series.maxsize
    assert series.x[0] == start
    assert series.x[-1] == start + (count - 1) * 2
    assert np.all(np.diff(series.x) > 0)
    indices = (series.x - start) / 2
    if pattern == "line":
        np.testing.assert_allclose(series.y, 20 + indices * 0.0001)
    else:
        assert series.y.max() == 100
        np.testing.assert_allclose(
            series.y, np.where(indices == spike_index, 100, 20 + indices * 0.0001)
        )


def test_one_hour_sliding_window_stays_bounded_during_long_session():
    updates = SeriesUpdates()
    # These are NicosTimePlot's production defaults: a 3600s window and 2s
    # interval. Unlike a non-sliding history view, old samples are discarded.
    series = TimeSeries("temperature", 2, None, 3600, updates)
    series.initEmpty()
    start = 1_700_000_000.0
    count = 128001

    for index in range(count):
        series.addValue(start + index * 2, 20 + index * 0.0001)

    assert updates.count == count
    assert series.x[-1] == start + (count - 1) * 2
    assert series.x[-1] - series.x[0] <= 3600
    assert series.n <= 1801
    assert series.data.shape[0] < series.maxsize
    np.testing.assert_allclose(series.y, 20 + (series.x - start) / 2 * 0.0001)


@pytest.mark.parametrize("count", [399, 400, 401, 1800])
def test_html_monitor_downsampling_preserves_paired_endpoints(count):
    from nicos.services.monitor.html import Plot

    plot = Plot(window=3600, width=400, height=200)
    now = time()
    timestamps = now - (count - 1) * 2 + np.arange(count) * 2
    values = 20 + np.arange(count) * 0.0001

    try:
        curve = plot.addcurve("temperature", timestamps[0])
        for timestamp, value in zip(timestamps, values, strict=True):
            plot.updatevalues(curve, float(timestamp), float(value))
        # getHTML() passes these same accumulated curve values to downsampling.
        x, y = plot.maybeDownsamplePlotdata(plot.data[curve])
    finally:
        Path(plot.tempfile).unlink()

    assert len(x) == len(y) == min(count, plot.width)
    np.testing.assert_allclose(y, 20 + (np.asarray(x) - timestamps[0]) / 2 * 0.0001)
    if count > plot.width:
        assert x[0] == timestamps[0]
        assert x[-1] == timestamps[-1]
        assert np.all(np.diff(x) > 0)
    else:
        np.testing.assert_array_equal(x, timestamps)
        np.testing.assert_array_equal(y, values)
    np.testing.assert_array_equal(plot.data[curve][0], timestamps)
    np.testing.assert_array_equal(plot.data[curve][1], values)

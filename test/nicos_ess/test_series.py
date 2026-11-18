"""Tests for the time series of readings."""

import time
import tracemalloc

import numpy as np
import pytest

from nicos_ess.utilities.series import Series

session_setup = None


def test_an_older_point_is_ignored():
    series = Series()

    series.add(1.0, 10.0)
    series.add(2.0, 20.0)
    series.add(1.5, 99.0)

    assert series.arrays().tolist() == [[1.0, 2.0], [10.0, 20.0]]


def test_a_point_at_the_same_time_replaces_the_last_one():
    series = Series()

    series.add(1.0, 10.0)
    series.add(2.0, 20.0)
    series.add(2.0, 21.0)

    assert series.arrays().tolist() == [[1.0, 2.0], [10.0, 21.0]]
    assert series.last_value == 21.0


def test_points_are_appended_after_a_replacement():
    series = Series()

    series.add(1.0, 10.0)
    series.add(1.0, 11.0)
    series.add(2.0, 20.0)

    assert series.arrays().tolist() == [[1.0, 2.0], [11.0, 20.0]]


def test_empty():
    series = Series()

    assert len(series) == 0
    assert np.isnan(series.last_value)
    assert series.arrays().shape == (2, 0)


def test_only_the_latest_points_are_kept():
    series = Series(maxlen=3)

    for when in range(10):
        series.add(float(when), when * 10.0)

    assert series.arrays()[1].tolist() == [70.0, 80.0, 90.0]


def test_only_the_latest_points_are_kept_after_many_wraps():
    series = Series(maxlen=3)

    for when in range(200):
        series.add(float(when), when * 10.0)
        latest = range(max(0, when - 2), when + 1)
        assert series.arrays().tolist() == [
            [float(time) for time in latest],
            [time * 10.0 for time in latest],
        ]

    assert len(series) == 3


def test_all_points_are_kept_when_the_storage_grows():
    series = Series(maxlen=1000)

    for when in range(500):
        series.add(float(when), when * 10.0)

    times, values = series.arrays()
    assert len(series) == 500
    assert times.tolist() == [float(when) for when in range(500)]
    assert values.tolist() == [when * 10.0 for when in range(500)]


def test_a_block_adds_only_the_points_after_the_last_one():
    series = Series()
    series.add(1.0, 10.0)
    series.add(2.0, 20.0)

    series.add(np.arange(5.0), np.arange(5.0) * 100)

    assert series.arrays().tolist() == [
        [1.0, 2.0, 3.0, 4.0],
        [10.0, 200.0, 300.0, 400.0],
    ]


def test_a_block_longer_than_the_series_keeps_its_latest_points():
    series = Series(maxlen=3)
    series.add(0.0, 0.0)

    series.add(np.arange(1.0, 11.0), np.arange(1.0, 11.0))
    series.add(np.arange(9.0, 13.0), np.arange(9.0, 13.0))

    assert series.arrays().tolist() == [[10.0, 11.0, 12.0]] * 2


def test_a_block_that_does_not_fit_leaves_the_series_alone():
    series = Series()
    series.add(1.0, 10.0)

    with pytest.raises(ValueError):
        series.add(np.arange(3.0), np.arange(4.0))
    with pytest.raises(ValueError):
        series.add("soon", 1.0)

    assert series.arrays().tolist() == [[1.0], [10.0]]


def test_adding_to_a_full_series_takes_no_longer_when_the_series_is_long():
    def seconds_for_adds(maxlen):
        series = Series(maxlen=maxlen)
        series.add(np.arange(float(maxlen)), np.zeros(maxlen))
        start = time.perf_counter()
        for when in range(maxlen, maxlen + 5000):
            series.add(float(when), 1.0)
        return time.perf_counter() - start

    short = min(seconds_for_adds(100) for _ in range(3))
    long = min(seconds_for_adds(100_000) for _ in range(3))

    assert long < 5 * short


def test_clear_gives_back_the_memory_of_the_points():
    tracemalloc.start()
    try:
        series = Series()
        series.add(np.arange(100_000.0), np.zeros(100_000))
        used = tracemalloc.get_traced_memory()[0]
        series.clear()
        freed = used - tracemalloc.get_traced_memory()[0]
    finally:
        tracemalloc.stop()

    assert freed > 1_000_000


def test_clear():
    series = Series()
    series.add(5.0, 50.0)
    series.add(6.0, 60.0)

    series.clear()

    assert len(series) == 0
    assert np.isnan(series.last_value)
    series.add(1.0, 10.0)
    assert series.arrays().tolist() == [[1.0], [10.0]]

import time

import numpy as np

from nicos_ess.gui.history_series import HistorySeries


def test_readings_are_stored_as_they_happened():
    series = HistorySeries("mot", None, interval=1)

    series.load([(100.0, 1.0), (200.0, 2.0)])
    assert series.add(5000.0, 3.0)

    np.testing.assert_array_equal(series.x, [100.0, 200.0, 5000.0])
    np.testing.assert_array_equal(series.y, [1.0, 2.0, 3.0])


def test_fast_readings_coalesce_but_keep_the_latest_value():
    series = HistorySeries("mot", None, interval=5)

    for index in range(20):
        series.add(float(index), float(index))

    np.testing.assert_array_equal(series.x, [0.0, 4.0, 8.0, 12.0, 16.0, 19.0])
    np.testing.assert_array_equal(series.y, series.x)


def test_first_reading_after_a_pause_is_kept():
    series = HistorySeries("mot", None, interval=5)
    for index in range(20):
        series.add(float(index), float(index))

    series.add(1000.0, 7.0)
    series.add(1001.0, 8.0)

    np.testing.assert_array_equal(series.x[-3:], [19.0, 1000.0, 1001.0])
    np.testing.assert_array_equal(series.y[-3:], [19.0, 7.0, 8.0])


def test_a_sliding_window_keeps_the_reading_in_force_at_its_start():
    series = HistorySeries("mot", None, interval=0, window=100)

    series.load([(0.0, 1.0), (10.0, 2.0), (500.0, 3.0)])
    series.add(560.0, 4.0)

    np.testing.assert_array_equal(series.x, [10.0, 500.0, 560.0])
    np.testing.assert_array_equal(series.y, [2.0, 3.0, 4.0])
    series.add(1000.0, 5.0)
    np.testing.assert_array_equal(series.x, [560.0, 1000.0])
    np.testing.assert_array_equal(series.y, [4.0, 5.0])


def test_too_many_readings_thin_the_older_half_but_keep_the_ends():
    series = HistorySeries("mot", None, interval=0)
    series.maxsize = 1000

    for index in range(5000):
        series.add(float(index), float(index))

    assert series.n == 1000
    assert series.x[0] == 0.0
    np.testing.assert_array_equal(series.x[-750:], np.arange(4250.0, 5000.0))
    assert np.all(np.diff(series.x[:250]) > 1)
    np.testing.assert_array_equal(series.y, series.x)


def test_thinning_drops_repeated_values_first():
    series = HistorySeries("mot", None, interval=0)
    series.maxsize = 100

    for index in range(150):
        series.add(float(index), float(index // 10))

    np.testing.assert_array_equal(np.unique(series.y), np.arange(15.0))
    np.testing.assert_array_equal(series.x[:10], np.arange(0.0, 100.0, 10.0))
    assert series.n == 61


def test_expression_transforms_values_and_drops_failures():
    series = HistorySeries("x", "x[1] * 2", interval=0)

    assert series.add(0.0, [1, 2])
    assert not series.add(1.0, None)
    # 3.5[1] raises a TypeError, so the expression fails for this reading.
    assert not series.add(2.0, 3.5)
    assert series.add(3.0, [0, 5])

    np.testing.assert_array_equal(series.x, [0.0, 3.0])
    np.testing.assert_array_equal(series.y, [4.0, 10.0])


def test_strings_map_to_numbers_in_order_of_first_appearance():
    states = HistorySeries("shutter", None, interval=0, mapping={"closed": 0})

    states.load([(0.0, "closed"), (1.0, "open"), (2.0, np.int64(0))])

    np.testing.assert_array_equal(states.y, [0.0, 1.0, 0.0])
    assert states.title == "shutter (0=closed, 1=open)"


def test_title_shows_unit_when_nothing_is_mapped():
    series = HistorySeries("x", None, interval=0, unit="mm")

    assert series.title == "x (mm)"


def test_identity_mapping_is_left_out_of_title():
    speed = HistorySeries("speed", None, 0, unit="Hz", mapping={"0": 0, "14": 14})

    assert speed.title == "speed (Hz)"


def test_readings_older_than_the_newest_are_rejected():
    series = HistorySeries("mot", None, interval=0)
    series.add(10.0, 1.0)

    assert not series.add(5.0, 2.0)
    np.testing.assert_array_equal(series.y, [1.0])


def test_a_reading_from_the_future_does_not_block_later_readings():
    series = HistorySeries("mot", None, interval=0)

    assert series.add(time.time() + 86400, 99.0)
    assert series.add(time.time(), 1.0)
    assert series.y[-1] == 1.0
    assert series.x[-1] <= time.time()


def test_an_integer_beyond_the_float_range_is_dropped():
    series = HistorySeries("mot", None, interval=0)
    doubled = HistorySeries("mot*2", "x*2", interval=0)

    for each in (series, doubled):
        assert not each.add(1.0, 10**400)
        assert each.add(2.0, 5.0)
    assert (series.y[-1], doubled.y[-1]) == (5.0, 10.0)


def test_strings_beyond_the_limit_share_one_other_state():
    states = {f"state {index}": index for index in range(25)}
    messages = HistorySeries("log", None, interval=0, mapping=states)

    for index in range(1000):
        messages.add(float(index), f"message {index}")
    messages.add(1000.0, "state 3")

    assert messages.n == 1001
    assert messages.y.max() == len(states) + messages.maxstrings
    assert len(messages.label) < 30 * (len(states) + messages.maxstrings)
    assert messages.y[-1] == 3.0


def test_a_sliding_window_keeps_the_readings_since_the_window_start():
    series = HistorySeries("mot", None, interval=0, window=100)

    for t in range(10_000):
        series.add(float(t), 2.0 * t)
        assert series.n == min(t, 100) + 1
        assert series.x[0] == max(t - 100, 0)

    np.testing.assert_array_equal(series.x, np.arange(9899.0, 10_000.0))
    np.testing.assert_array_equal(series.y, 2 * series.x)


def test_an_unlisted_state_is_distinct_from_configured_states():
    series = HistorySeries("valve", None, 0, mapping={"closed": 0, "open": 2})
    series.load([(10, "closed"), (20, "open"), (30, "moving")])

    assert series.y[:2].tolist() == [0, 2]
    assert series.y[2] not in series.y[:2]

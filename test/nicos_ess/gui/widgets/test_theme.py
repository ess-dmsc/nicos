import time

import numpy as np
import pytest

from nicos.guisupport.qt import QApplication, QFont
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    TICK_SCALE,
    CompactAxisItem,
    TimeAxisItem,
    base_pixel_size,
    css_size,
    label_room,
    scaled_font,
)


@pytest.fixture
def sixteen_pixel_text(qtbot):
    """The tick labels depend on the text size, so the axis tests use the
    16 px that the NICOS style sheet sets and not the default font of the
    machine."""
    app = QApplication.instance()
    sheet = app.styleSheet()
    app.setStyleSheet("QWidget { font-size: 16px; }")
    yield
    app.setStyleSheet(sheet)


def compact_axis(integers, log, low, high):
    axis = CompactAxisItem(orientation="left")
    axis.integers = integers
    axis.setLogMode(False, log)
    axis.setRange(low, high)
    return axis


def test_short_time_spans_keep_the_time_of_day_and_tick_at_round_times(qtbot):
    noon = time.mktime((2026, 11, 14, 12, 0, 5, 0, 0, -1))
    axis = TimeAxisItem(orientation="bottom")

    assert axis.tickStrings([noon], 1, 5) == ["12:00:05"]
    assert axis.tickStrings([noon + 0.5], 1, 0.5) == ["12:00:05.5"]
    (spacing, values), *_ = axis.tickValues(noon - 4.7, noon + 0.3, 600)
    assert spacing == 1
    assert [round(v - noon, 3) for v in values] == [-4, -3, -2, -1, 0]


def test_plot_text_follows_the_style_sheet_not_the_application_font(qtbot):
    app = QApplication.instance()
    sheet, font = app.styleSheet(), app.font()
    small = QFont(font)
    small.setPixelSize(11)
    app.setFont(small)
    app.setStyleSheet("QWidget { font-size: 20px; }")
    try:
        assert base_pixel_size() == 20
        assert scaled_font(TICK_SCALE).pixelSize() == 16
        assert css_size(TICK_SCALE) == "16px"
    finally:
        app.setStyleSheet(sheet)
        app.setFont(font)


@pytest.mark.parametrize(
    "log, integers, low, high, size, labels",
    [
        (
            True,
            False,
            np.log10(200),
            np.log10(400),
            300,
            ["200", "250", "300", "350", "400"],
        ),
        (False, False, -60e3, 70e3, 79, ["-50k", "0", "50k"]),
        # A short integer axis gets labels between the ends too.
        (False, True, -0.5, 500.5, 60, ["0", "200", "400"]),
    ],
)
def test_axes_label_round_values(
    sixteen_pixel_text, log, integers, low, high, size, labels
):
    axis = compact_axis(integers, log, low, high)

    (spacing, values), *_ = axis.tickValues(low, high, size)

    assert axis.tickStrings(values, 1, spacing) == labels


@pytest.mark.parametrize(
    "low, high",
    [(0.0, 1e-310), (5e-324, 1e-323), (1e300, 1.7e308), (-1.7e308, 1.7e308)],
)
def test_tiny_and_huge_spans_get_finite_ticks(sixteen_pixel_text, low, high):
    axis = compact_axis(False, False, low, high)

    levels = axis.tickValues(low, high, 40)

    values = [v for _spacing, ticks in levels for v in ticks]
    assert np.isfinite([spacing for spacing, _ticks in levels]).all()
    assert all(low <= v <= high for v in values)
    for spacing, ticks in levels:
        assert len(axis.tickStrings(ticks, 1, spacing)) == len(ticks)


def test_labels_in_a_compact_plot_stay_readable(sixteen_pixel_text):
    low, high, size = 0.31, 0.92, 55
    axis = compact_axis(False, False, low, high)

    (spacing, values), *_ = axis.tickValues(low, high, size)

    assert axis.tickStrings(values, 1, spacing) == ["0.4", "0.6", "0.8"]
    # The labels are at least one text height apart.
    assert spacing * size / (high - low) >= label_room(axis, "0") / 2.5


@pytest.mark.parametrize(
    "low, high, labels",
    [
        (-0.5, 127.5, ["0", "20", "40", "60", "80", "100", "120"]),
        (-40.5, 87.5, ["-40", "-20", "0", "20", "40", "60", "80"]),
    ],
)
def test_pixel_labels_never_show_minus_zero(sixteen_pixel_text, low, high, labels):
    axis = compact_axis(True, False, low, high)

    (spacing, values), *_ = axis.tickValues(low, high, 400)

    assert spacing == 20
    assert axis.tickStrings(values, 1, spacing) == labels

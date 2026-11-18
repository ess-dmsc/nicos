"""Tests for FrameView, which plots a labelled N-D array on a shared canvas."""

from __future__ import annotations

import gc
import json
import re
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pyqtgraph as pg
import pytest

from nicos.guisupport.qt import (
    QApplication,
    QEvent,
    QMenu,
    QPoint,
    QPointF,
    Qt,
    sip,
)
from nicos_ess.gui.widgets.pyqtgraph import frame_plot
from nicos_ess.gui.widgets.pyqtgraph.frame_format import (
    bin_index,
    edges_of,
    facts,
    format_position,
    pointer_at,
    readable,
    total_of,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_format import (
    clock as time_of_day,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import HELD, FrameView
from nicos_ess.gui.widgets.pyqtgraph.theme import compact_number
from nicos_ess.utilities.frame_reduction import reduce
from nicos_ess.utilities.frame_views import axis, view_label
from nicos_ess.utilities.live_frame import Coord, Frame
from test.nicos_ess.gui.helpers import menu_action, mouse_held, mouse_move
from test.nicos_ess.gui.widgets.frames import (
    FakeClick,
    FakeWheel,
    cube,
    curve,
    histogram,
    image,
    make_view,
    wait_exposed,
)

# esslivedata sends monitor spectra in ms
MS = ("time_of_arrival", np.linspace(0, 71, 101), "ms")
# just-bin-it sends them in ns
NS = ("tof", np.linspace(0, 7.1e7, 715), "ns")


@pytest.fixture(autouse=True)
def stop_the_age_timer():
    """The age timer and its set of views would otherwise live on into later tests."""
    yield
    frame_plot._VIEWS_WITH_AGE.clear()
    if frame_plot._age_timer.cache_info().currsize:
        frame_plot._age_timer().stop()
        frame_plot._age_timer.cache_clear()


NOW = 1.8e9


@pytest.fixture
def clock(monkeypatch):
    """Stop the clock of the plots at NOW so that an age in the title is exact."""
    monkeypatch.setattr(frame_plot, "time", SimpleNamespace(time=lambda: NOW))


def y_range(view):
    QApplication.processEvents()
    return view.plot.vb.viewRange()[1]


def title_parts(view):
    return view.title_item.toolTip().split("\n")


def wait_until_steady(read):
    """Process Qt events until *read* gives the same value three times in a row."""
    values = []
    for _ in range(100):
        QApplication.processEvents()
        values = [*values[-2:], read()]
        if len(values) == 3 and values[0] == values[1] == values[2]:
            return values[-1]
    raise AssertionError("The layout did not settle.")


def test_a_histogram_is_drawn_as_steps_with_errors(view):
    view.show_frame(histogram())

    assert view.curve.line.opts["stepMode"] == "center"
    assert list(view.curve.errors.opts["top"]) == [1.0, 2.0, 3.0]
    assert "Σ 14 counts" in title_parts(view)
    view.show_frame(replace(histogram(), counts=False))
    assert "mean 4.667 counts" in title_parts(view)


def test_the_parts_that_come_and_go_are_last_in_the_title(view, clock):
    view.show_frame(histogram(meta=dict(time=NOW - 30, saturated=3)))
    title = title_parts(view)

    assert "Σ 14 counts" in title
    # The other parts stay in place when these come and go.
    assert title[-3:] == ["3 px saturated", "30 s old", "Monitor histogram"]


def test_an_age_below_two_periods_is_hidden_because_it_would_blink(view, clock):
    view.show_frame(histogram(meta=dict(time=NOW - 9)))
    assert "9 s old" in title_parts(view)
    view.period = 21
    view.show_frame(histogram(meta=dict(time=NOW - 9)))
    assert not any(part.endswith(" old") for part in title_parts(view))


def test_a_frozen_plot_keeps_its_picture_and_title_until_it_thaws(view):
    view.show_frame(histogram())
    view.set_frozen(True)
    view.show_frame(histogram(data=np.full(3, 1000.0)))

    assert list(view.curve.line.yData) == [1.0, 4.0, 9.0]
    assert {"Σ 14 counts", "frozen"} <= set(title_parts(view))
    view.set_frozen(False)
    assert list(view.curve.line.yData) == [1000.0, 1000.0, 1000.0]
    assert "Σ 3,000 counts" in title_parts(view)
    assert "frozen" not in title_parts(view)


def test_an_image_sits_on_the_edges_of_its_coordinate(view):
    edges = Coord(("x",), np.array([10.0, 20.0, 30.0, 40.0]))
    view.show_frame(image(1.0, coords={"x": edges}))
    rect = view.layer.image.mapRectToParent(view.layer.image.boundingRect())

    assert (rect.left(), rect.right()) == (10.0, 40.0)


def test_a_y_axis_with_a_unit_grows_upwards_and_rows_grow_downwards(view):
    ys = {"y": Coord(("y",), np.array([0.0, 1.0, 2.0]), "mm")}
    view.show_frame(image(1.0, coords=ys))
    assert not view.plot.vb.yInverted()
    # just-bin-it sends edges without a unit
    rows = {"y": Coord(("y",), np.array([0.0, 1.0, 2.0]))}
    view.show_frame(image(1.0, coords=rows))
    assert view.plot.vb.yInverted()
    # daqlite also shows the first camera row at the top
    view.show_frame(image(1.0, (64, 48)))
    assert view.plot.vb.yInverted()
    view.set_full_profiles(True)
    assert view.profiles.strips["y"].yInverted()


def test_camera_pixels_are_square_and_detector_channels_fill_the_plot(view):
    view.show_frame(image(1.0, (64, 48)))
    assert view.plot.vb.state["aspectLocked"]
    view.show_frame(image(1.0, (15, 900), ("arc/tube", "channel/pixel")))
    assert not view.plot.vb.state["aspectLocked"]


def test_uneven_bins_are_drawn_as_a_mesh_and_even_bins_as_an_image(view):
    uneven = Coord(("x",), np.array([0.0, 1.0, 3.0, 7.0]))
    view.show_frame(image(1.0, coords={"x": uneven}))
    assert view.layer.mesh.isVisible() and not view.layer.image.isVisible()
    even = Coord(("x",), np.array([0.0, 1.0, 2.0, 3.0]))
    view.show_frame(image(1.0, coords={"x": even}))
    assert view.layer.image.isVisible() and not view.layer.mesh.isVisible()


def test_a_log_scale_leaves_values_that_are_not_positive_blank(view):
    view.show_frame(Frame(np.array([[1.0, 10.0], [100.0, 0.0]]), ("y", "x")))
    view.set_log(True)

    np.testing.assert_array_equal(view.layer.image.image[0], [0.0, 1.0])
    assert view.layer.image.image[1, 0] == pytest.approx(2.0)
    assert np.isnan(view.layer.image.image[1, 1])


def test_a_cube_is_summed_over_a_window_or_shown_as_a_curve(view):
    view.show_frame(cube())
    np.testing.assert_array_equal(view.layer.image.image, cube().data.sum(axis=0))
    view.set_window("wavelength", (1, 3))
    np.testing.assert_array_equal(view.layer.image.image, cube().data[1:3].sum(0))
    view.set_window("wavelength", (2, 3))

    assert view.step_window(1) and view.step_window(1)
    np.testing.assert_array_equal(view.layer.image.image, cube().data[3])
    view.set_choice("wavelength")
    view.show_frame(replace(cube(), data=cube().data * 2))
    np.testing.assert_array_equal(view.curve.line.yData, 2 * cube().data.sum((1, 2)))


def test_the_value_under_the_pointer_is_shown_beside_it(view):
    view.show_frame(histogram())
    vb = view.plot.vb
    vb.setRange(xRange=(0, 3e3), yRange=(0, 10), padding=0)
    QApplication.processEvents()
    title = view.title_item.text

    assert view.hover_at(vb.mapViewToScene(pg.Point(1500.0, 5.0)))
    box = view.hover_box.label.toPlainText()

    assert "tof 1,000–2,000 us" in box and "4 ± 2 counts" in box
    assert view.hover == "tof 1,000–2,000 us: 4 ± 2 counts"
    assert view.title_item.text == title and view.pointer_line.isVisible()
    # zooming changes which bin is under the pointer
    vb.setRange(xRange=(0, 4.2e3), padding=0)
    assert view.hover.startswith("tof 2,000–3,000 us")
    view.show_frame(curve(*MS))
    QApplication.processEvents()

    assert not view.hover.startswith("tof")
    view.hover_at(QPointF(-1e9, -1e9))
    assert not view.hover_box.isVisible() and not view.pointer_line.isVisible()


def test_numbers_read_short_on_axes_and_in_full_under_the_pointer():
    assert compact_number(1.58e10, 1e8) == "15.8G"
    ticks = [compact_number(5.7343e6 + i * 10, 10) for i in range(3)]
    assert len(set(ticks)) == 3
    assert readable(460213.4) == "460,213"
    assert [readable(v) for v in (2.477e5, 1234.5, 1.1581e9)] == [
        "247,700",
        "1,234",
        "1.158G",
    ]
    camera = Frame(np.zeros((2, 2048)), ("y", "x"))

    assert format_position(axis(camera, "x"), 1167) == "1167"
    binned = replace(camera, binned={"x": 4})
    assert format_position(axis(binned, "x"), 3) == "12–15"
    text = facts(replace(cube(), binned={"y": 4, "x": 4}), 0.0)

    assert "4×20×24, shown 4×5×6" in text


def test_times_read_as_times_of_day():
    t = 1.8e9
    times = Frame(
        np.ones(2),
        ("time",),
        coords={"time": Coord(("time",), np.array([t, t + 2]), "datetime64[s]")},
        meta={"start_time": t},
    )

    ax = axis(times, "time")

    assert format_position(ax, 0) == time_of_day(t)
    assert format_position(ax, 0, 2) == f"{time_of_day(t - 1)}–{time_of_day(t + 3)}"
    assert facts(times, 1.0) == ["mean 1", "2 points", f"since {time_of_day(t)}"]


def test_single_bins_and_ranges_across_zero_read_as_ranges():
    single = Frame(np.ones(1), ("x",), coords={"x": Coord(("x",), np.ones(1), "mm")})
    across = axis(curve("x", np.array([-1.0, 0.0, 1.0, 2.0]), "mm"), "x")

    assert format_position(axis(single, "x"), 0) == "0.5–1.5 mm"
    assert format_position(across, 0, 3) == "-1 to 2 mm"


def test_the_total_of_counts_is_their_sum_and_of_other_values_their_mean():
    integers = Frame(np.array([1, 2, 3, 6]), ("x",))

    assert total_of(integers) == 3.0
    assert total_of(replace(integers, counts=True)) == 12.0


def test_times_beyond_the_calendar_read_as_a_dash():
    huge = Frame(
        np.ones(2),
        ("time",),
        coords={
            "time": Coord(("time",), np.array([2**62, 2**62 + 2**12]), "datetime64[s]")
        },
        meta={"start_time": 1e300},
    )

    assert facts(huge, 1.0)[-1] == "since –"
    assert pointer_at(huge, 2.0**62) == ("time –", (0,))


def test_the_pointer_finds_bins_on_falling_axes_and_none_on_empty_ones():
    falling = np.array([3.0, 2.0, 1.0, 0.0])

    assert [bin_index(falling, v) for v in (2.5, 0.5, 3.5)] == [0, 2, None]
    assert pointer_at(Frame(np.zeros(0), ("x",)), 0.5) is None


def test_the_menus_of_a_plot_go_with_its_canvas(qtbot):
    frame_view = FrameView("out")
    canvas = frame_plot.FrameCanvas(frame_view)
    canvas.show()
    frame_view.show_frame(cube())
    menus = [frame_view.plot_menu.menu, frame_view.axis_menu]
    sip.delete(canvas)
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert all(sip.isdeleted(menu) for menu in menus)


def test_the_plot_menu_is_ours_only_and_opens_from_the_title(view, monkeypatch):
    view.show_frame(cube())
    menu = view.plot_menu.menu
    menu.aboutToShow.emit()
    menu.aboutToShow.emit()  # showing the menu again must not add the actions twice
    texts = [a.text() for a in menu.actions()]

    assert texts.count("Log scale") == 1 and "View All" not in texts
    opened = []
    monkeypatch.setattr(view.plot_menu, "open", opened.append)
    view.title_item.menu_requested.emit(QPoint(5, 5))

    assert opened == [QPoint(5, 5)]


@pytest.mark.parametrize("data", [image(1.0, (8, 8)), histogram()])
def test_a_right_click_on_the_axes_or_beside_the_plot_opens_the_plot_menu(
    view, qtbot, monkeypatch, data
):
    view.show_frame(data)
    wait_exposed(qtbot, view.canvas)
    opened = []
    monkeypatch.setattr(view.plot_menu, "open", opened.append)
    left, bottom = (view.plot.getAxis(side) for side in ("left", "bottom"))
    places = [
        left.mapToScene(left.width() / 2, left.height() / 2),
        bottom.mapToScene(bottom.width() / 2, bottom.height() / 2),
        # This is the corner between the two axes.
        bottom.mapToScene(-left.width() / 2, bottom.height() / 2),
        # An image keeps its shape, so the card has room beside it.
        view.item.mapToScene(3, view.item.size().height() / 2),
    ]
    viewport = view.canvas.viewport()
    for place in places:
        at = view.canvas.mapFromScene(place)
        qtbot.mouseMove(viewport, at)
        qtbot.mouseClick(viewport, Qt.MouseButton.RightButton, pos=at)
    assert len(opened) == len(places)


def test_a_zoom_holds_for_the_same_quantities_and_is_dropped_for_others(view):
    """A zoom set on esslivedata's spectrum in ms would show only a few ns of
    just-bin-it's spectrum."""
    view.show_frame(curve(*MS))
    view.plot.vb.setXRange(10, 30, padding=0)
    # dragging the plot emits this signal
    view.plot.vb.sigRangeChangedManually.emit([True, False])
    view.show_frame(curve(*MS, values=np.ones(100)))

    assert HELD["zoomed"] in title_parts(view)
    assert np.allclose(view.plot.vb.viewRange()[0], (10, 30))
    view.show_frame(curve(*NS))
    QApplication.processEvents()

    assert not view.zoomed() and view.plot.vb.viewRange()[0][1] >= 7.1e7
    assert HELD["zoomed"] not in title_parts(view)


def test_a_curve_wider_than_pyqtgraph_can_show_gets_a_finite_range(view):
    view.show_frame(curve("x", np.linspace(1e300, 1.7e308, 4), "mm"))
    view.canvas.grab()

    assert np.isfinite(view.plot.vb.viewRange()).all()


def test_fixed_colours_hold_for_the_same_quantities_and_over_time(view):
    view.show_frame(image(1.0, (8, 8), ("dim_1", "dim_2")))
    view.layer.set_levels(0, 5)
    view.show_frame(image(2.0, (8, 8), ("dim_1", "dim_2")))

    assert not view.layer.follow and view.layer.levels == (0, 5)
    # the history shows the same data, so the levels are kept
    view.set_show_history(True)
    view.set_show_history(False)
    assert not view.layer.follow and view.layer.levels == (0, 5)
    view.show_frame(image(3.0, (8, 8)))

    assert view.layer.follow


def test_the_colour_bar_wheel_fixes_the_colours_until_scale_to_each_image(view):
    view.show_frame(image(3.0, (8, 8)))
    bar = view.layer.colorbar
    wheel = FakeWheel(bar.vb.mapViewToScene(pg.Point(0.5, 1.0)))
    bar.wheel(wheel)

    assert wheel.accepted
    assert not view.layer.follow and HELD["colours fixed"] in title_parts(view)
    menu_action(view.plot_menu, "Scale to each image").trigger()
    assert view.layer.follow and HELD["colours fixed"] not in title_parts(view)


def test_reset_zoom_keeps_fixed_colours(view):
    view.show_frame(image(3.0, (8, 8)))
    view.plot.vb.setRange(yRange=(100, 200))
    view.layer.set_levels(0, 1)
    menu_action(view.plot_menu, "Reset zoom").trigger()

    assert not view.zoomed()
    assert not view.layer.follow and view.layer.levels == (0, 1)


def test_a_zoom_is_dropped_when_another_view_is_chosen(view):
    view.show_frame(cube())
    view.plot.vb.setRange(yRange=(100, 200))
    assert view.zoomed()
    view.set_choice(view.choices()[1])
    assert not view.zoomed()


# A plot moved to another view gets its state as it is, a restart from JSON.
@pytest.mark.parametrize("kept", [dict, lambda s: json.loads(json.dumps(s))])
def test_saved_colour_levels_are_dropped_when_the_data_changed_kind(view, qtbot, kept):
    view.show_frame(image(7.0, (4, 5), ("y", "x")))
    view.layer.set_levels(0, 10)
    view.measure.set_length_scale(0.5, "mm")
    state = kept(view.state())

    same, other = make_view(qtbot), make_view(qtbot)
    same.restore(state)
    same.show_frame(image(8.0, (4, 5), ("y", "x")))
    assert not same.layer.follow and same.layer.levels == (0, 10)
    # The next session sends raw camera values without a unit under the name.
    other.restore(state)
    other.show_frame(image(3e4, (4, 5), ("y", "x"), unit=""))
    assert other.layer.follow
    assert same.measure.length_scale == (0.5, "mm")


def test_length_and_log_scale_are_reset_when_the_data_changes_kind(view):
    view.show_frame(image(7.0, (4, 5), ("y", "x")))
    view.measure.set_length_scale(0.5, "mm")
    view.set_log(True)
    view.show_frame(image(8.0, (4, 5), ("y", "x")))
    assert view.log and view.measure.length_scale == (0.5, "mm")
    view.show_frame(image(3e4, (4, 5), ("y", "x"), unit=""))

    assert not view.log and view.measure.length_scale is None
    assert not view.layer.log and view.state()["length_scale"] is None


@pytest.mark.parametrize("hold", ["zoom", "levels"])
def test_a_held_plot_follows_new_units_and_fits_its_window(view, hold):
    view.show_frame(cube())
    view.set_window("wavelength", (3, 4))
    if hold == "zoom":
        view.plot.vb.disableAutoRange()
    else:
        view.layer.set_mode("manual")
    assert view.held() == [{"zoom": "zoomed", "levels": "colours fixed"}[hold]]
    # The workflow changed and now sends fewer bins, normalised.
    edges = {"wavelength": Coord(("wavelength",), np.linspace(1, 5, 3), "angstrom")}
    fewer = replace(cube(), data=np.ones((2, 5, 6)), unit="counts/s", coords=edges)
    view.show_frame(fewer)

    assert view.windows == {"wavelength": (1, 2)}
    assert not view.zoomed() and view.layer.follow


def test_the_chosen_view_waits_for_data_of_its_kind(view, qtbot):
    view.show_frame(cube())
    view.set_choice("wavelength")
    view.show_frame(image(1.0, (5, 6)))  # Another source sends under the same name.
    assert view.state()["view"] == "wavelength"
    view.show_frame(cube())
    assert view_label(view.choice) == "wavelength"
    # The same across sessions, livedata then just-bin-it then livedata.
    livedata = image(5.0, (15, 90), ("arc/tube", "channel/pixel"))
    first, jbi, again = (make_view(qtbot) for _ in range(3))
    first.show_frame(livedata)
    first.set_choice("channel/pixel")
    jbi.restore(first.state())
    jbi.show_frame(image(5.0, (15, 90), ("y", "x")))
    again.restore(jbi.state())
    again.show_frame(livedata)
    assert again.state()["view"] == "channel/pixel"


def test_the_chosen_window_waits_for_data_with_its_dim(view, qtbot):
    view.show_frame(cube())
    view.set_window("wavelength", (1, 3))
    view.show_frame(image(1.0, (5, 6)))  # Another source sends under the same name.
    assert view.state()["windows"] == {"wavelength": [1, 3]}
    later = make_view(qtbot)
    later.restore(json.loads(json.dumps(view.state())))
    for plot in (view, later):
        plot.show_frame(cube())
        assert plot.windows == {"wavelength": (1, 3)}


@pytest.mark.parametrize(
    "state",
    [
        dict.fromkeys(["style", "overlays", "colors", "windows", "view", "legend"]),
        {"style": "x", "overlays": 3, "colors": []},
        {"length_scale": "mm", "strip_depth": "a", "view": ["y"], "quantities": 5},
        {"length_scale": [None, 2], "history": "no", "quantities": [[1], "K"]},
        {"windows": {"wavelength": [2, 1], "y": "1", "x": [0, 1.5]}},
        {"windows": [1, 2]},
    ],
)
def test_damaged_saved_settings_are_left_out(view, state):
    view.restore(state)
    fresh = FrameView("out").state()
    assert {key: view.state()[key] for key in state} == {
        key: fresh[key] for key in state
    }
    view.show_frame(cube())
    assert view.windows == {} and view.measure.length_scale is None
    # These must not raise.
    view.set_choice("y × x")
    view.show_frame(histogram())


@pytest.mark.parametrize("depth", [float("nan"), float("inf"), -0.5, 0])
def test_a_strip_depth_from_a_damaged_file_is_left_out(view, depth):
    view.restore({"strip_depth": depth, "profiles": True})
    view.show_frame(cube())

    assert view.full_profiles and view.state()["strip_depth"] is None


def test_restored_settings_apply_with_the_first_frame_and_profiles_are_saved(view):
    view.restore({"view": "wavelength", "log": True, "windows": {"y": [1, 2]}})
    # the restored view is kept until a frame arrives
    assert view.state()["view"] == "wavelength"
    assert view.state()["windows"] == {"y": [1, 2]}
    view.show_frame(cube())

    assert (view.choice, view.log) == (("wavelength",), True)
    view.set_choice(view.choices()[0])
    menu_action(view.plot_menu, "Whole-image profiles").trigger()
    other = FrameView("out")
    other.restore(view.state())

    assert other.full_profiles


def test_hovering_and_new_data_move_no_plot(qtbot):
    canvas = pg.GraphicsLayoutWidget()
    qtbot.addWidget(canvas)
    canvas.resize(1000, 600)
    views = [FrameView(f"out{i}") for i in range(4)]
    for i, frame_view in enumerate(views):
        canvas.ci.addItem(frame_view.item, row=i // 2, col=i % 2)
        frame_view.show_frame(histogram())
    canvas.show()
    wait_exposed(qtbot, canvas)
    places = lambda: [v.item.geometry().getRect() for v in views]  # noqa: E731
    before = wait_until_steady(places)
    vb = views[0].plot.vb
    assert views[0].hover_at(vb.mapViewToScene(pg.Point(1500.0, 5.0)))
    views[1].show_frame(histogram(title="A much longer title " * 5))

    assert wait_until_steady(places) == before


def test_hovering_over_time_before_the_first_frame_shows_nothing(view):
    view.set_show_history(True)  # as restored from the saved settings
    QApplication.processEvents()

    assert view.hover_at(view.plot.vb.mapViewToScene(pg.Point(0.5, 0.5))) is False
    assert view.hover == "" and not view.hover_box.isVisible()


def test_single_values_and_any_total_are_drawn_over_time(view, qtbot):
    for i, value in enumerate([3.0, 5.0, 4.0]):
        view.show_frame(image(value, (1,), ("dim_0",), meta=dict(time=1e3 + i)))
    assert view.history_shown()
    assert list(view.curve.line.yData) == [3.0, 5.0, 4.0]
    vb = view.plot.vb
    wait_until_steady(lambda: (vb.sceneBoundingRect().getRect(), str(vb.viewRange())))
    view.hover_at(view.plot.vb.mapViewToScene(pg.Point(1e3 + 1, 5.0)))
    assert view.hover.startswith("time ") and view.hover.endswith(": 5 counts")
    view.show_frame(image(6.0, (), ()))
    assert view.curve.line.yData[-1] == 6.0
    other = make_view(qtbot)
    other.show_frame(histogram(), 10.0)
    other.show_frame(histogram(data=np.ones(3)), 11.0)
    other.set_show_history(True)

    assert list(other.curve.line.yData) == [14.0, 3.0]
    other.show_frame(histogram(), 12.0)
    other.show_frame(histogram(), 100.0)
    # the NaN breaks the line during the pause between counts
    assert np.isnan(other.curve.line.yData[3])
    other.set_show_history(False)
    other.plot.addItem(mark := pg.InfiniteLine())
    other.show_frame(curve("time", np.arange(4) + 1.7e9, "datetime64[s]"))
    # items added by the owner survive the switch to a time axis
    assert mark in other.plot.items
    assert isinstance(other.plot.getAxis("bottom"), pg.DateAxisItem)


def test_a_single_value_is_drawn_over_time_even_with_over_time_off(view):
    view.show_frame(image(3.0, (), ()), 1.0)
    view.set_show_history(False)  # the user unchecks Show > Over time
    view.show_frame(image(4.0, (), ()), 2.0)
    assert list(view.curve.line.yData) == [3.0, 4.0]
    # The setting was saved for a curve and the same name now sends one value.
    view.restore({"history": False})
    view.show_frame(image(5.0, (), ()), 3.0)
    assert view.curve.line.yData[-1] == 5.0


def test_a_single_value_has_no_over_time_entry_but_keeps_the_setting(view):
    view.restore({"history": False})
    view.show_frame(image(3.0, (), ()), 1.0)
    menu = view.plot_menu.menu
    menu.aboutToShow.emit()
    menus = [menu, *menu.findChildren(QMenu)]
    assert "Over time" not in [a.text() for m in menus for a in m.actions()]
    # The same name sends a curve later.
    view.show_frame(histogram(), 2.0)

    assert not view.history_shown() and view.state()["history"] is False
    assert not menu_action(view.plot_menu, "Over time").isChecked()


def test_log_scale_after_a_frame_of_only_nan_draws_its_axes(view, qtbot):
    """pytest-qt fails the test if a paint raises."""
    wait_exposed(qtbot, view.canvas)
    view.show_frame(curve("tof", np.linspace(0, 1e3, 5), "us", np.full(4, 448.0)))
    view.canvas.grab()
    # A normalised output sends NaN before the monitor counts.
    view.show_frame(curve("tof", np.linspace(0, 1e3, 11), "us", np.full(10, np.nan)))
    view.canvas.grab()
    view.set_log(True)
    view.canvas.grab()
    view.show_frame(curve("tof", np.linspace(0, 1e3, 4), "us", np.array([1.0, 5, 3])))
    view.canvas.grab()

    assert all(view.plot.getAxis(side).isVisible() for side in ("left", "bottom"))
    low, high = y_range(view)  # the range is in log10
    assert low <= 0 and np.log10(5) <= high < 2


def test_other_curves_in_the_same_unit_are_overlaid(view):
    view.set_overlay("monitor_2", True)
    view.set_overlay("other", True)
    metres = {"tof": Coord(("tof",), np.array([0.0, 1.0, 2.0, 3.0]), "m")}
    view.overlay_frames = {
        "monitor_2": histogram(data=np.full(3, 7.0), name="monitor_2", unit="events"),
        "other": histogram(coords=metres),
    }
    view.show_frame(histogram())

    assert list(view.overlay_curves) == ["monitor_2"]
    labels = [label.text for _item, label in view.legend.items]
    assert labels == ["out", "monitor_2 (right axis)"]
    assert view.plot.getAxis("right").labelText == "events"
    view.set_overlay("monitor_2", False)
    view.redraw()
    assert not view.legend.isVisible()
    assert not view.plot.getAxis("right").isVisible()
    view.overlay_frames = {name: histogram(name=name) for name in "xy"}
    for name, on in (("x", True), ("y", True), ("x", False), ("x", True)):
        view.set_overlay(name, on)
        view.show_frame(histogram())
    x, y = (view.overlay_curves[name].line.opts["pen"].color() for name in "xy")
    assert x != y


def test_one_unit_per_axis_the_right_one_zooms_with_the_left(view, qtbot):
    units = ("counts", "events", "K", "events")
    view.show_frames([histogram(name=f"c{i}", unit=u) for i, u in enumerate(units)])

    assert sorted(view.overlay_curves) == ["c1", "c3"]
    assert view.plot.getAxis("right").labelText == "events"
    assert "c2 in another unit" in view.title_item.text
    QApplication.processEvents()
    low, high = view.right.viewRange()[1]
    view.plot.vb.scaleBy((1, 0.5))
    new_low, new_high = view.right.viewRange()[1]
    assert new_high - new_low == pytest.approx((high - low) / 2)
    # dragging the right axis acts on the main view
    assert view.plot.getAxis("right").linkedView() is view.plot.vb
    view.follow_data()
    qtbot.waitUntil(lambda: view.right.state["autoRange"][1])


def test_an_empty_frame_hides_the_curves_axes_legend_and_hover(view):
    units = ("counts", "events")
    view.show_frames([histogram(name=f"c{i}", unit=u) for i, u in enumerate(units)])
    QApplication.processEvents()
    view.hover_at(view.plot.vb.mapViewToScene(pg.Point(1500.0, 5.0)))
    assert view.hover == "tof 1,000–2,000 us: c0 4 ± 2 counts · c1 4 ± 2 events"
    view.show_frame(histogram(data=np.zeros(0), coords={}, errors=None))

    assert view.hover == "" and not view.hover_box.isVisible()
    assert view.empty_note.isVisible()
    assert not view.plot.vb.childGroup.isVisible() and not view.right.isVisible()
    assert not view.legend.isVisible()
    assert not view.plot.getAxis("left").isVisible()
    assert not view.plot.getAxis("bottom").isVisible()


def test_a_new_plot_shows_no_axes():
    view = FrameView("new")
    assert view.empty_note.isVisible()
    assert not view.plot.getAxis("left").isVisible()
    assert not view.plot.getAxis("bottom").isVisible()


def test_values_a_log_scale_cannot_show_are_counted_compact_too(view, qtbot):
    view.set_log(True)
    first = histogram(data=np.array([-1.0, 0.0, 9.0]))
    view.show_frames([first, histogram(name="b", unit="events")])

    assert "2 values ≤ 0 not shown" in view.title_item.text
    # an axis that is created on a log plot also gets log mode
    assert view.plot.getAxis("right").logMode
    view.canvas.resize(300, 200)

    qtbot.waitUntil(lambda: view.compact)
    assert not any(
        view.plot.getAxis(side).label.isVisible() for side in ("left", "right")
    )
    # a late plot keeps the unit in the title and drops the bins
    view.lagging, view.age = True, lambda: 30
    view.update_title()
    assert "counts" in view.title_item.text and "bins" not in view.title_item.text
    view.show_frame(image(0.0))
    view.set_log(True)  # The log scale was chosen for the curves.

    assert "6 values ≤ 0 not shown" in view.title_item.toolTip()


def test_a_long_legend_takes_rows_and_hides_from_the_menu_only(view, qtbot):
    names = [f"a_long_curve_name_{i}" for i in range(4)]
    view.show_frames([histogram(name=name) for name in names])

    qtbot.waitUntil(lambda: view.legend.rowCount > 1)
    assert view.item.width() <= view.canvas.width()
    sample, _label = view.legend.items[1]
    sample.mouseClickEvent(FakeClick(sample.scenePos()))
    assert view.overlay_curves[names[1]].line.isVisible()
    menu_action(view.plot_menu, "Legend").trigger()
    menu_action(view.plot_menu, "Points").trigger()
    assert not view.legend.isVisible()
    assert view.overlay_curves[names[1]].symbols and view.curve.symbols
    other = FrameView("out")
    other.restore(view.state())
    assert (other.show_legend, other.style) == (False, {"points": True})


def test_corrections_subtract_divide_and_skip_another_binning(view):
    view.show_frame(image(10.0))
    view.take_reference("background")
    view.show_frame(image(30.0))
    view.take_reference("flat field")
    view.set_correction("subtract", True)
    view.set_correction("divide", True)
    view.show_frame(image(20.0))
    np.testing.assert_array_equal(view.image.data, image(0.5).data)
    view.hover_at(view.plot.vb.mapViewToScene(pg.Point(1.0, 1.0)))
    assert view.hover.endswith(": 0.5")
    assert "mean 0.5" in view.title_item.toolTip()
    # the same shape with other pixels gets no correction
    view.show_frame(image(15.0, binned=dict(y=2, x=2)))
    np.testing.assert_array_equal(view.image.data, image(15.0).data)
    view.show_frame(image(15.0, (4, 6)))
    np.testing.assert_array_equal(view.image.data, image(15.0, (4, 6)).data)

    assert "taken at another binning" in view.title_item.toolTip()
    view.set_correction("shown", "background")
    np.testing.assert_array_equal(view.image.data, image(15.0, (4, 6)).data)
    view.set_correction(None, None)

    assert view.corrections.references["background"] is None
    view.set_correction("subtract", True)
    # references are not saved, so a restart has nothing to subtract
    assert "subtract" not in str(view.state())


def test_a_reference_is_taken_from_the_image_that_is_shown(view):
    view.show_frame(image(10.0))
    view.set_frozen(True)
    view.set_choice("x")  # a frozen plot keeps its picture
    view.take_reference("background")
    np.testing.assert_array_equal(
        view.corrections.references["background"], image(10.0).data
    )
    view.set_frozen(False)
    view.show_frame(Frame(np.zeros(0), ("tof",), unit="counts", counts=True))
    view.take_reference("flat field")  # nothing is shown, so nothing is taken
    assert view.corrections.references["flat field"] is None


def test_an_empty_frame_leaves_only_the_entries_that_apply_in_the_menu(view):
    view.show_frame(image(10.0))
    menu = view.plot_menu.menu
    menu.aboutToShow.emit()
    assert "Colours" in [a.text() for a in menu.actions()]
    view.show_frame(Frame(np.zeros((0, 0)), ("y", "x"), unit="counts", counts=True))
    menu.aboutToShow.emit()
    texts = [a.text() for a in menu.actions()]

    assert "Log scale" in texts
    assert not {"Colours", "Corrections", "Whole-image profiles"} & set(texts)
    assert not any(text.startswith("Measure") for text in texts)


def test_references_are_forgotten_when_the_data_changes_unit(view):
    view.show_frame(image(10.0))
    view.take_reference("background")
    view.set_correction("subtract", True)
    # A camera sends raw values of the same shape under the same name.
    view.show_frame(image(3e4, unit=""))
    np.testing.assert_array_equal(view.image.data, image(3e4).data)
    assert view.corrections.references["background"] is None


@pytest.mark.parametrize("counts", [True, False])
def test_counts_are_drawn_from_zero_other_values_over_their_range(view, counts):
    """An integrating beam monitor reads ADC values that sit on a pedestal,
    so the signal starts at the pedestal instead of at 0."""
    values = 3000.0 + 24000 * np.exp(-(((np.arange(50) - 10) / 4.0) ** 2))
    spectrum = curve("tof", np.linspace(0, 71, 51), "ms", values)
    view.show_frame(replace(spectrum, unit="ADC counts", counts=counts))

    assert (y_range(view)[0] <= 0) == counts
    view.set_log(True)
    low, high = y_range(view)  # the range is in log10

    assert low > 3 and high < 5


def test_all_zero_and_empty_data_are_drawn_from_zero_up(view):
    view.show_frame(curve(*MS, values=np.zeros(100)))
    low, high = y_range(view)

    assert -0.1 < low <= 0 < high
    view.show_frame(replace(cube(), data=np.zeros((4, 5, 6))))

    assert view.layer.levels == (0.0, 1.0)
    view.show_frame(image(0.0, (0, 0)))

    assert view.empty_note.isVisible() and view.title_parts() == []


def test_an_image_with_profiles_survives_its_cell_getting_narrow(view):
    """The margins that keep the image square were computed for the old size.
    They must not squeeze the image out of a much narrower cell."""
    view.canvas.resize(700, 300)
    view.show_frame(image(1.0, (5, 5)))
    view.set_full_profiles(True)
    QApplication.processEvents()
    view.canvas.resize(230, 300)
    for _ in range(3):
        QApplication.processEvents()

    assert view.plot.width() <= 230 and view.plot.vb.width() > 20
    assert all(s.image_axis.integers for s in view.profiles.strips.values())
    assert view.compact
    left = view.profiles.strips["y"].image_axis

    assert not left.label.isVisible()
    assert "counts" in view.title_item.toolTip()
    assert view.full_profiles and view.profiles.profiles


def test_the_box_names_every_curve_under_the_pointer_the_nearest_bold(view, qtbot):
    frames = [histogram(name=f"c{i}", data=np.full(3, 10.0 * i)) for i in range(20)]
    view.show_frames(frames)
    view.canvas.resize(900, 700)
    vb = view.plot.vb
    vb.setRange(xRange=(0, 3e3), yRange=(0, 200), padding=0)
    plot_area = lambda: vb.sceneBoundingRect().getRect()  # noqa: E731
    wait_until_steady(plot_area)

    view.hover_at(vb.mapViewToScene(pg.Point(1500.0, 71.0)))
    box = view.hover_box.label

    assert view.hover.startswith("tof 1,000–2,000 us: c0 0 ± 2 counts · c1 10 ")
    assert re.search(r"font-weight:\s*[67]00[^>]*>c7<", box.toHtml())
    # with room for fewer rows the box keeps the nearest curves
    view.canvas.resize(900, 250)
    wait_until_steady(plot_area)
    view.hover_at(vb.mapViewToScene(pg.Point(1500.0, 71.0)))
    text = box.toPlainText()
    assert "c7" in text and "c19" not in text and "more" in text
    # when neither side fits, the box goes above or below the pointer
    view.canvas.resize(250, 250)
    wait_until_steady(plot_area)
    view.hover_at(at := vb.mapViewToScene(pg.Point(1500.0, 71.0)))
    assert not view.hover_box.sceneBoundingRect().contains(at)


def test_a_canvas_paints_after_an_image_became_a_curve_and_an_image_again(qtbot):
    coords = {
        "x": Coord(("x",), np.arange(41), "datetime64[s]"),
        "y": Coord(("y",), np.array([3.0, 3.0]), "mm"),
    }
    data = -np.linspace(1.0, 99.0, 40).reshape(40, 1)
    frame = Frame(data, ("x", "y"), unit="counts", counts=True, coords=coords)
    frame_view = FrameView("out")
    canvas = frame_plot.FrameCanvas(frame_view)
    qtbot.addWidget(canvas)
    canvas.resize(500, 350)
    canvas.show()
    frame_view.show_frame(frame, NOW)
    for choice in [("y", "x"), ("y",), ("y", "x")]:
        frame_view.set_choice(choice)
        QApplication.processEvents()

    assert not canvas.grab().isNull()


def test_new_data_that_rebuilds_the_plot_during_a_drag_raises_nothing(qtbot, recwarn):
    frame_view = FrameView("out")
    canvas = frame_plot.FrameCanvas(frame_view)
    qtbot.addWidget(canvas)
    canvas.show()
    frame_view.show_frame(image(1.0, shape=(40, 40)))
    QApplication.processEvents()
    vb = frame_view.plot.vb
    start, end = (
        canvas.mapFromScene(vb.mapViewToScene(pg.Point(v, v))) for v in (10, 30)
    )
    with mouse_held(qtbot, canvas.viewport(), start, end):
        frame_view.show_frame(histogram())
        frame_view.show_frame(image(1.0, shape=(40, 40)))
        gc.collect()  # Otherwise the old plot is deleted at a random time.
        mouse_move(qtbot, canvas.viewport(), start)

    # pyqtgraph turns an error in a drag event into a warning.
    assert not [w for w in recwarn if "has been deleted" in str(w.message)]


def test_skipping_a_background_preserves_the_raw_uncertainties(view):
    view.show_frame(image(2))
    view.take_reference("background")
    view.set_correction("subtract", True)
    raw = image(10, binned={"x": 2}, errors=np.ones((2, 3)))

    view.show_frame(raw)

    np.testing.assert_array_equal(view.image.data, raw.data)
    np.testing.assert_array_equal(view.view.errors, raw.errors)


def test_a_flat_field_ratio_has_no_adc_unit_in_the_readout(view):
    view.show_frame(image(10, unit="ADU", counts=False))
    view.take_reference("flat field")
    view.set_correction("divide", True)
    view.show_frame(image(5, unit="ADU", counts=False))

    view.hover_at(view.plot.vb.mapViewToScene(pg.Point(1.0, 1.0)))
    assert "0.5" in view.hover
    assert "ADU" not in view.hover


def test_the_last_reduced_bin_ends_at_the_sensor_edge():
    frame = Frame(np.ones(513), ("x",), counts=True)
    reduced = reduce(frame, 256)

    assert reduced.data.sum() == 513
    assert edges_of(axis(reduced, "x"))[-1] == 512.5

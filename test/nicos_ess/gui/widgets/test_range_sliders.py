"""Tests for the range sliders under a plot and the menus on its axis labels."""

import numpy as np
import pytest

from nicos.guisupport.qt import QPoint, QPointF, Qt, QWheelEvent
from nicos_ess.utilities.live_frame import Coord, Frame
from test.nicos_ess.gui.helpers import menu_action, mouse_drag
from test.nicos_ess.gui.widgets.frames import cube, make_view, wait_exposed

LEFT = Qt.MouseButton.LeftButton


def tof_cube(bins=100):
    data = np.arange(bins * 4 * 5, dtype=np.int32).reshape(bins, 4, 5)
    tof = Coord(("tof",), np.linspace(0.0, 71.0, bins + 1), "ms")
    return Frame(data, ("tof", "y", "x"), "counts", True, coords={"tof": tof})


@pytest.fixture
def view(view, qtbot):
    """The shared empty view with a time-of-flight cube and a window over it."""
    view.show_frame(tof_cube())
    view.set_window("tof", (20, 40))
    wait_exposed(qtbot, view.canvas)
    return view


def at_bin(view, b, row=0, shift=0.0):
    """Return the point on the canvas over the bin edge *b* of a slider row."""
    sliders = view.sliders
    x = sliders.bin_x(sliders.rows[row], b) + shift
    y = (row + 0.5) * sliders.row_height
    return view.canvas.mapFromScene(sliders.mapToScene(QPointF(x, y)))


def label_centre(view, side):
    label = view.plot.getAxis(side).label
    return view.canvas.mapFromScene(label.sceneBoundingRect().center())


def wheel(view, at, modifiers=Qt.KeyboardModifier.ShiftModifier, up=True):
    viewport = view.canvas.viewport()
    event = QWheelEvent(
        QPointF(at),
        QPointF(viewport.mapToGlobal(at)),
        QPoint(),
        QPoint(0, 120 if up else -120),
        Qt.MouseButton.NoButton,
        modifiers,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    view.canvas.wheelEvent(event)


def test_a_slider_shows_the_window_in_the_unit_of_the_coordinate(view):
    [row] = view.sliders.rows
    assert (row.dim, row.size, row.window) == ("tof", 100, (20, 40))
    assert row.text == "14.2–28.4 ms"
    np.testing.assert_array_equal(
        view.layer.image.image, tof_cube().data[20:40].sum(axis=0)
    )


@pytest.mark.parametrize(
    "window, text", [((2000, 2001), "35.50–35.52 ms"), ((0, 4000), "0.00–71.00 ms")]
)
def test_the_slider_text_has_the_decimals_that_tell_neighbouring_bins_apart(
    qtbot, window, text
):
    view = make_view(qtbot)
    view.show_frame(tof_cube(4000))
    view.set_window("tof", window)
    assert view.sliders.rows[0].text == text


def test_a_window_over_all_bins_is_dropped(view):
    view.set_window("tof", (0, 100))
    assert view.windows == {}
    assert view.sliders.rows[0].window == (0, 100)


def test_only_dims_that_are_not_drawn_get_a_slider(view):
    view.set_choice("tof")
    assert [r.dim for r in view.sliders.rows] == ["y", "x"]


@pytest.mark.parametrize(
    "frame",
    [Frame(np.ones((3, 4)), ("y", "x")), Frame(np.ones(4), ("x",))],
    ids=["image", "curve"],
)
def test_a_frame_that_draws_all_its_dims_hides_the_sliders(view, frame):
    assert [r.dim for r in view.sliders.rows] == ["tof"]
    view.show_frame(frame)
    assert view.sliders.rows == []
    assert not view.sliders.isVisible()


def test_a_new_plot_leaves_no_room_for_sliders_it_does_not_have(qtbot):
    view = make_view(qtbot)
    view.show_frame(Frame(np.ones((3, 4)), ("y", "x")))
    assert not view.sliders.isVisible()
    assert view.sliders.maximumHeight() == 0


def test_a_dragged_handle_moves_one_end(view, qtbot):
    viewport = view.canvas.viewport()
    mouse_drag(qtbot, viewport, at_bin(view, 40, shift=2), at_bin(view, 60, shift=2))
    assert view.windows == {"tof": (20, 60)}
    mouse_drag(qtbot, viewport, at_bin(view, 20, shift=-2), at_bin(view, 5, shift=-2))
    assert view.windows == {"tof": (5, 60)}
    # The low end stops one bin before the high end.
    mouse_drag(qtbot, viewport, at_bin(view, 5, shift=-2), at_bin(view, 90))
    assert view.windows == {"tof": (59, 60)}


def test_a_dragged_window_keeps_its_width(view, qtbot):
    mouse_drag(qtbot, view.canvas.viewport(), at_bin(view, 30), at_bin(view, 50))
    assert view.windows == {"tof": (40, 60)}
    mouse_drag(qtbot, view.canvas.viewport(), at_bin(view, 50), at_bin(view, 99))
    assert view.windows == {"tof": (80, 100)}


def test_a_click_on_the_track_centres_the_window_there(view, qtbot):
    qtbot.mouseClick(view.canvas.viewport(), LEFT, pos=at_bin(view, 80))
    assert view.windows == {"tof": (70, 90)}
    # A drag that starts on the track moves the window from there.
    mouse_drag(qtbot, view.canvas.viewport(), at_bin(view, 10), at_bin(view, 30))
    assert view.windows == {"tof": (20, 40)}


def test_a_double_click_on_the_slider_takes_all_bins(view, qtbot):
    solo = []
    view.solo_requested.connect(lambda: solo.append(True))
    viewport, at = view.canvas.viewport(), at_bin(view, 30)
    qtbot.mouseDClick(viewport, LEFT, pos=at)
    qtbot.mouseRelease(viewport, LEFT, pos=at)
    assert view.windows == {} and not solo


def test_shift_and_wheel_over_the_plot_move_the_window_by_one_bin(view):
    centre = view.canvas.mapFromScene(view.plot.vb.sceneBoundingRect().center())
    wheel(view, centre)
    wheel(view, centre)
    assert view.windows == {"tof": (22, 42)}
    wheel(view, at_bin(view, 10), Qt.KeyboardModifier.NoModifier, up=False)
    assert view.windows == {"tof": (21, 41)}
    view.set_window("tof", None)
    wheel(view, centre)
    assert view.windows == {}


def four_dims(qtbot):
    data = np.random.default_rng(0).poisson(3, (6, 7, 4, 5))
    view = make_view(qtbot)
    view.show_frame(Frame(data, ("wavelength", "tof", "y", "x"), "counts", True))
    view.set_window("wavelength", (1, 2))
    view.set_window("tof", (2, 5))
    return view, data


def test_a_4d_frame_gets_a_slider_for_each_dim_that_is_not_drawn(qtbot):
    view, data = four_dims(qtbot)
    assert [r.dim for r in view.sliders.rows] == ["wavelength", "tof"]
    assert [r.text for r in view.sliders.rows] == ["1", "2–4"]
    np.testing.assert_array_equal(view.layer.image.image, data[1, 2:5].sum(axis=0))


def test_stepping_moves_the_window_that_was_set_last(qtbot):
    view, _data = four_dims(qtbot)
    assert view.step_window(1)
    assert view.windows == {"wavelength": (1, 2), "tof": (3, 6)}
    assert [r.text for r in view.sliders.rows] == ["1", "3–5"]


def click_axis_label(view, qtbot, monkeypatch, side):
    """Click the label on *side* and return the entries of the axis menu
    that the click opened."""
    opened = []
    monkeypatch.setattr(view.axis_menu, "popup", opened.append)
    qtbot.mouseClick(view.canvas.viewport(), LEFT, pos=label_centre(view, side))
    return {a.text(): a for a in view.axis_menu.actions()} if opened else None


def test_a_left_click_on_an_axis_label_chooses_the_dim_on_that_axis(qtbot, monkeypatch):
    view = make_view(qtbot)
    view.show_frame(cube())
    wait_exposed(qtbot, view.canvas)
    entries = click_axis_label(view, qtbot, monkeypatch, "bottom")
    assert list(entries) == ["y", "x", "wavelength"]
    entries["wavelength"].trigger()

    assert view.choice == ("y", "wavelength")
    assert view.layer.image.image.shape == (5, 4)
    assert [r.dim for r in view.sliders.rows] == ["x"]
    assert menu_action(view.plot_menu, "wavelength × y").isChecked()


def test_choosing_the_dim_of_the_other_axis_swaps_the_axes(qtbot, monkeypatch):
    view = make_view(qtbot)
    view.show_frame(cube())
    wait_exposed(qtbot, view.canvas)
    assert view.choice == ("y", "x")
    click_axis_label(view, qtbot, monkeypatch, "left")["x"].trigger()

    assert view.choice == ("x", "y")
    assert view.layer.image.image.shape == (6, 5)
    assert view.state()["view"] == "x × y"


def test_a_right_click_on_an_axis_label_or_a_slider_opens_the_plot_menu(
    view, qtbot, monkeypatch
):
    opened = []
    monkeypatch.setattr(view.plot_menu, "open", opened.append)
    places = [label_centre(view, side) for side in ("bottom", "left")]
    for at in [*places, at_bin(view, 30), at_bin(view, 80)]:
        qtbot.mouseClick(view.canvas.viewport(), Qt.MouseButton.RightButton, pos=at)
    assert len(opened) == 4
    assert view.axis_menu.actions() == []
    assert view.windows == {"tof": (20, 40)}


def test_an_image_of_two_dims_offers_only_the_swap(qtbot, monkeypatch):
    view = make_view(qtbot)
    view.show_frame(Frame(np.ones((3, 4)), ("y", "x")))
    wait_exposed(qtbot, view.canvas)
    assert list(click_axis_label(view, qtbot, monkeypatch, "bottom")) == ["y", "x"]


def test_a_curve_axis_has_no_menu(qtbot, monkeypatch):
    view = make_view(qtbot)
    view.show_frame(Frame(np.ones(4), ("x",)))
    wait_exposed(qtbot, view.canvas)
    assert view.plot.getAxis("bottom").label.isVisible()
    assert click_axis_label(view, qtbot, monkeypatch, "bottom") is None


def test_a_compact_plot_opens_the_axis_menu_from_the_whole_axis(qtbot, monkeypatch):
    view = make_view(qtbot)
    view.canvas.resize(250, 200)
    view.show_frame(cube())
    wait_exposed(qtbot, view.canvas)
    qtbot.waitUntil(lambda: view.compact)
    opened = []
    monkeypatch.setattr(view.axis_menu, "popup", opened.append)
    left = view.plot.getAxis("left")
    at = view.canvas.mapFromScene(left.mapToScene(left.boundingRect().center()))
    qtbot.mouseClick(view.canvas.viewport(), LEFT, pos=at)
    assert len(opened) == 1

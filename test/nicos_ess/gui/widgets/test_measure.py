"""Tests for measurements on an image and the profiles next to the image.

The user places the measurements, they are shown next to what they measure,
and they are never sent anywhere.
"""

import re

import numpy as np
import pyqtgraph as pg
import pytest

from nicos.guisupport.qt import (
    QApplication,
    QEvent,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPoint,
    sip,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameView
from nicos_ess.gui.widgets.pyqtgraph.measure_editor import measure_menu
from nicos_ess.utilities.live_frame import Coord, Frame
from test.nicos_ess.gui.helpers import mouse_drag
from test.nicos_ess.gui.widgets.frames import (
    FakeClick,
    image,
    menu_widget,
    millimetres,
)


@pytest.fixture
def image_view(view):
    view.show_frame(Frame(np.arange(12.0).reshape(3, 4), ("y", "x"), unit="counts"))
    return view


def drag(view, kind, start, end):
    view.arm(kind)
    return view.measure.measure_between(kind, pg.Point(*start), pg.Point(*end), True)


def form_of(menu):
    """Return the fields of a measurement menu keyed by the text of their row."""
    form = menu_widget(menu, "position")
    role = QFormLayout.ItemRole.LabelRole
    return {
        form.layout().itemAt(row, role).widget().text(): field
        for row, field in enumerate(form.fields)
    }


def shown_statistics(menu):
    return [
        label.text() for label in menu_widget(menu, "statistics").findChildren(QLabel)
    ]


def process_events():
    for _ in range(10):
        QApplication.processEvents()


def test_a_box_sums_whole_bins_and_is_typed_in(image_view):
    assert drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    box = image_view.measure.tools["box"]

    assert box.stats["sum"] == 5 + 6
    assert box.text.startswith("mean")
    menu = measure_menu(image_view.measure, "box")
    fields = form_of(menu)
    fields["x from"].setText("0")  # Pixel 0 starts at the edge -0.5.
    fields["x from"].editingFinished.emit()

    assert box.points()[0][0] == pytest.approx(-0.5)
    assert fields["x from"].text() == "0"
    assert "15 counts" in shown_statistics(menu)


def test_a_box_dragged_by_hand_snaps_to_bin_edges(image_view):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    box = image_view.measure.tools["box"]
    box.items[0].setPos((1.3, 0.2))
    (x0, y0), (x1, y1) = box.points()

    assert (x0, x1, y0, y1) == pytest.approx((1.5, 3.5, 0.5, 1.5))


def test_a_narrow_label_shows_the_short_result(image_view, qtbot):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    box = image_view.measure.tools["box"]
    image_view.canvas.resize(1600, 800)
    qtbot.waitUntil(lambda: box.label.textItem.toPlainText() == box.text)

    assert box.short() != box.text
    image_view.canvas.resize(150, 400)
    qtbot.waitUntil(lambda: box.label.textItem.toPlainText() == box.short())
    assert box.label.isVisible()


def test_a_crosshair_reads_the_value_and_draws_its_profiles(image_view):
    image_view.arm("crosshair")

    assert image_view.profiles.strips == {}
    assert image_view.measure.measure_at(2.3, 1.2)
    assert image_view.measure.tools["crosshair"].stats["value"] == 6.0
    at = image_view.plot.vb.mapViewToScene(pg.Point(2.3, 1.2))
    image_view.hover_at(at)
    assert image_view.measure.tools["crosshair"].text == image_view.hover
    profiles = image_view.profiles
    row = profiles.profiles["x", "crosshair"][2]
    np.testing.assert_array_equal(row, [4, 5, 6, 7])
    np.testing.assert_array_equal(profiles.profiles["y", "crosshair"][2], [2, 6, 10])
    image_view.plot.vb.setXRange(1, 2, padding=0)

    assert profiles.strips["x"].viewRange()[0] == pytest.approx([1, 2])
    assert not image_view.plot.getAxis("bottom").isVisible()
    image_view.measure.clear()

    assert profiles.profiles == {} and profiles.strips == {}
    assert image_view.plot.getAxis("bottom").isVisible()


def test_full_profiles_are_mean_rows_and_columns_and_stay(image_view):
    image_view.set_full_profiles(True)
    profiles = image_view.profiles
    np.testing.assert_array_equal(profiles.profiles["x", "full"][2], [4, 5, 6, 7])
    np.testing.assert_array_equal(profiles.profiles["y", "full"][2], [1.5, 5.5, 9.5])

    low, high = profiles.strips["x"].viewRange()[1]
    assert 3.5 < low < 4 and 7 < high < 7.5
    image_view.show_frame(
        Frame(data=4500 + np.arange(12.0).reshape(3, 4), dims=("y", "x"))
    )
    low, high = profiles.strips["x"].viewRange()[1]
    assert 4500 < low < 4504 and 4507 < high < 4510
    image_view.arm("crosshair")
    image_view.measure.measure_at(2.0, 1.0)
    image_view.measure.clear()

    assert set(profiles.profiles) == {("x", "full"), ("y", "full")}
    image_view.set_full_profiles(False)

    assert profiles.profiles == {}


def test_a_strip_axis_without_room_for_ticks_labels_the_data_ends(image_view):
    image_view.set_full_profiles(True)
    image_view.show_frame(
        Frame(data=4500 + np.arange(12.0).reshape(3, 4), dims=("y", "x"))
    )
    axis = image_view.profiles.strips["x"].axes[0]

    assert len(axis.tickValues(4500, 4900, 300)[0][1]) > 2
    ends = [[v for _s, v in axis.tickValues(4500, 4510, n)] for n in (30, 9)]
    # Without room for ticks, the axis labels only the data ends that fit. How
    # many fit depends on the font.
    assert 4507 in ends[0][0] and set(ends[0][0]) <= {4504, 4507}
    assert ends[1] == []


def test_measurements_keep_their_pixels_through_other_views(image_view):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    box = image_view.measure.tools["box"]
    image_view.set_choice(("x",))
    image_view.set_choice(("y", "x"))

    assert box.items[0].getViewBox() is image_view.plot.vb
    assert box.points() == pytest.approx([(0.5, 0.5), (2.5, 1.5)])
    assert box.stats["sum"] == 5 + 6


def test_measurements_keep_their_pixels_through_new_data(image_view):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    edges = Coord(("x",), np.arange(5.0) * 10, "mm")
    image_view.show_frame(
        Frame(np.arange(12.0).reshape(3, 4), ("y", "x"), coords={"x": edges})
    )
    box = image_view.measure.tools["box"]

    assert [p[0] for p in box.points()] == pytest.approx([10, 30])
    assert box.stats["sum"] == 5 + 6


def test_a_wide_line_averages_and_a_known_length_sets_the_scale(view):
    data = np.arange(12.0).reshape(3, 4) ** 2
    view.show_frame(Frame(data, ("y", "x"), unit="counts"))
    drag(view, "line", (0, 1), (3, 1))
    menu = measure_menu(view.measure, "line")
    width = form_of(menu)["width"]

    assert float(width.text()) == 1
    _item, _distance, values = view.profiles.profiles["line", "line"]
    np.testing.assert_allclose(values, data[1])
    width.setText("3")  # A width of 3 covers rows 0 to 2.
    width.editingFinished.emit()
    _item, _distance, values = view.profiles.profiles["line", "line"]
    np.testing.assert_allclose(values, data.mean(axis=0))
    length, unit = menu_widget(menu, "length scale").findChildren(QLineEdit)
    unit.setText("µm")
    length.setText("30")
    length.editingFinished.emit()
    line = view.measure.tools["line"]

    assert "30 µm" in shown_statistics(menu)
    assert "length 30 µm" in line.label.toPlainText()
    assert "1 px = 10 µm" in view.title_item.text


def test_a_click_on_a_label_opens_its_menu_while_drawing(image_view, qtbot):
    opened = []
    image_view.measure.open_menu = lambda k, _at: opened.append(k)
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    image_view.arm("crosshair")
    label = image_view.measure.tools["box"].label
    image_view.plot.vb.mouseClickEvent(
        FakeClick(label.mapToScene(label.boundingRect().center()))
    )

    # The menu only opens once no double-click can follow.
    qtbot.waitUntil(lambda: opened == ["box"])
    assert "crosshair" not in image_view.measure.tools
    # Switching to a curve detaches the measurement labels.
    image_view.set_choice(image_view.choices()[-1])
    assert image_view.measure.label_at(label.sceneBoundingRect().center()) is None


def test_one_measurement_goes_from_its_menu(image_view):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    image_view.measure.measure_at(1.0, 1.0)
    menu = measure_menu(image_view.measure, "box")
    next(a for a in menu.actions() if a.text() == "Remove").trigger()
    assert list(image_view.measure.tools) == ["crosshair"]
    assert ("x", "box") not in image_view.profiles.profiles


def test_a_line_across_two_quantities_has_no_length(view):
    view.show_frame(Frame(data=np.ones((15, 900)), dims=("tube", "pixel")))
    drag(view, "line", (0, 0), (600, 8))

    assert "length" not in view.measure.tools["line"].label.toPlainText()
    distance = view.profiles.profiles["line", "line"][1]
    np.testing.assert_allclose(distance[[0, -1]], [0, np.hypot(600, 8)])
    strip = view.profiles.strips["line"]
    assert not strip.yInverted()
    view.hover_at(strip.mapViewToScene(pg.Point(300, 1)))
    shown = re.fullmatch(r"distance (\S+) px: line 1", view.hover)
    step = distance[1] - distance[0]
    assert float(shown[1]) == pytest.approx(300, abs=step)


def test_nothing_is_measured_on_a_curve(view):
    view.show_frame(Frame(data=np.arange(3.0), dims=("x",)))

    assert not drag(view, "box", (0, 0), (1, 1))
    assert view.measure.tools == {}


def test_measurements_find_uneven_bins_and_whole_tubes(view):
    """The bins are 0-1, 1-2, 2-4, 4-8 and 8-16, and each column holds its
    own index."""
    edges = Coord(("x",), np.array([0, 1, 2, 4, 8, 16.0]), "µs")
    view.show_frame(
        Frame(np.tile(np.arange(5.0), (3, 1)), ("y", "x"), coords={"x": edges})
    )
    drag(view, "box", (1.2, 0), (5, 2))  # The box covers the centres 1.5 and 3.
    box = view.measure.tools["box"]

    assert box.stats["mean"] == 1.5
    assert [p[0] for p in box.points()] == pytest.approx([1, 4])
    view.show_frame(
        Frame(np.repeat(np.arange(15.0)[:, None], 40, 1), ("tube", "pixel"))
    )
    drag(view, "box", (10, 3), (30, 11))
    box = view.measure.tools["box"]

    assert [p[1] for p in box.points()] == pytest.approx([2.5, 11.5])
    assert box.stats["mean"] == pytest.approx(7)


@pytest.mark.parametrize("kind", ["box", "line"])
def test_the_image_stays_put_while_a_measurement_is_drawn(view, qtbot, kind):
    """The strips for the profiles only appear when the mouse is released."""
    view.canvas.resize(700, 500)
    view.show_frame(Frame(np.random.rand(40, 40), ("y", "x")))
    view.arm(kind)
    process_events()
    image = view.plot.vb
    before, seen = (image.sceneBoundingRect(), image.viewRange()), []
    drawn = view.measure.measure_between

    def measure_between(kind, start, end, done):
        placed = drawn(kind, start, end, done=done)
        seen.append((done, image.sceneBoundingRect(), image.viewRange()))
        return placed

    view.measure.measure_between = measure_between

    def at(x, y):
        return view.canvas.mapFromScene(image.mapViewToScene(pg.Point(x, y)))

    mouse_drag(qtbot, view.canvas.viewport(), at(10, 10), at(30, 25))

    assert any(not done for done, _rect, _range in seen)
    assert all((rect, rng) == before for done, rect, rng in seen if not done)
    assert ("line" if kind == "line" else "x", kind) in view.profiles.profiles
    shape = view.measure.tools[kind]
    first, end = shape.points()
    mouse_drag(qtbot, view.canvas.viewport(), at(*end), at(35, 35))
    assert shape.points()[0] == pytest.approx(first) and shape.points()[1][0] > 32


def test_a_live_update_due_after_the_plot_is_deleted_does_nothing(qtbot):
    canvas = pg.GraphicsLayoutWidget()
    view = FrameView("out")
    canvas.ci.addItem(view.item)
    canvas.show()
    view.show_frame(Frame(np.random.rand(40, 40), ("y", "x")))
    view.arm("box")
    # A box that is still being drawn updates its label at most 20 times per
    # second, so this update is due after the plot is gone.
    view.measure.measure_between("box", pg.Point(5, 5), pg.Point(20, 20), False)
    canvas.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert sip.isdeleted(view.measure.tools["box"].label)
    qtbot.wait(200)


def test_profiles_come_and_go_in_one_layout(qtbot, image_view):
    """The layout settles at once, so nothing moves a frame later."""
    image_view.canvas.resize(800, 500)
    process_events()

    def where():
        items = (image_view.plot.vb, image_view.layer.colorbar)
        return [item.sceneBoundingRect().getRect() for item in items]

    for change in (
        lambda: image_view.set_full_profiles(True),
        lambda: image_view.set_full_profiles(False),
        lambda: image_view.measure.measure_at(1.0, 1.0),
        image_view.measure.clear,
    ):
        change()
        first = where()
        for _ in range(10):
            QApplication.processEvents()
            assert where() == first


def drag_grip_up(qtbot, image_view, pixels):
    canvas = image_view.canvas
    grip = image_view.profiles.strips["x"].grip
    start = canvas.mapFromScene(grip.sceneBoundingRect().center())
    mouse_drag(qtbot, canvas.viewport(), start, start - QPoint(0, pixels))
    return start


def test_a_dragged_strip_depth_is_kept_at_once(qtbot, image_view):
    image_view.set_full_profiles(True)
    process_events()
    profiles, before = image_view.profiles, image_view.profiles.depth
    kept = []
    image_view.changed.connect(lambda: kept.append(image_view.state()["strip_depth"]))
    drag_grip_up(qtbot, image_view, 15)

    assert len(kept) == 1 and kept[0] is not None
    profiles.strips["x"].grip.mouseClickEvent(FakeClick(None, double=True))
    assert kept[-1] is None
    assert profiles.depth == before


def test_strips_line_up_with_the_image(image_view):
    image_view.canvas.resize(800, 400)  # The square image gets margins.
    image_view.set_full_profiles(True)
    process_events()
    image = image_view.plot.vb.sceneBoundingRect()
    x = image_view.profiles.strips["x"].sceneBoundingRect()
    edge = image_view.profiles.strips["x"].grip.sceneBoundingRect()

    assert (x.left(), x.right()) == pytest.approx((image.left(), image.right()), abs=1)
    assert edge.top() == pytest.approx(image.bottom(), abs=2)


def test_a_strip_edge_follows_the_pointer_and_keeps_its_share(qtbot, image_view):
    canvas = image_view.canvas
    canvas.resize(800, 400)
    image_view.set_full_profiles(True)
    process_events()
    profiles, before = image_view.profiles, image_view.profiles.depth
    start = drag_grip_up(qtbot, image_view, 15)
    grip = profiles.strips["x"].grip

    assert profiles.depth == pytest.approx(before + 15, abs=2)
    moved = canvas.mapFromScene(grip.sceneBoundingRect().center())
    assert moved.y() == pytest.approx(start.y() - 15, abs=2)
    share = profiles.depth / profiles.smaller()
    canvas.resize(600, 300)
    process_events()
    assert profiles.depth == pytest.approx(share * profiles.smaller(), abs=1)


@pytest.mark.parametrize("solo", [False, True])
def test_a_depth_dragged_while_solo_is_not_kept(qtbot, image_view, solo):
    """A plot shown alone uses the strip depth of the grid when the others
    come back."""
    image_view.canvas.resize(800, 400)
    image_view.set_full_profiles(True)
    process_events()
    profiles, before = image_view.profiles, image_view.profiles.depth
    image_view.set_solo(solo)
    drag_grip_up(qtbot, image_view, 15)

    assert profiles.depth == pytest.approx(before + 15, abs=2)
    assert (image_view.state()["strip_depth"] is None) == solo
    image_view.set_solo(False)
    if solo:
        assert profiles.depth == before
    else:
        assert profiles.depth == pytest.approx(before + 15, abs=2)


def test_a_dragged_strip_depth_is_capped_at_a_share_of_the_side(image_view):
    image_view.canvas.resize(800, 400)
    image_view.set_full_profiles(True)
    process_events()
    profiles = image_view.profiles
    profiles.set_depth(0.5)

    assert profiles.depth == int(0.15 * profiles.smaller())


def test_a_double_click_on_a_strip_shows_the_plot_alone(image_view):
    image_view.set_full_profiles(True)
    process_events()
    solo = []
    image_view.solo_requested.connect(lambda: solo.append(True))
    strip = image_view.profiles.strips["x"]
    at = strip.mapViewToScene(pg.Point(2.0, np.mean(strip.viewRange()[1])))
    strip.mouseClickEvent(FakeClick(at, double=True))

    assert solo == [True]


def test_a_strip_reads_out_like_the_image(image_view):
    image_view.set_full_profiles(True)
    process_events()
    strip = image_view.profiles.strips["x"]
    at = strip.mapViewToScene(pg.Point(2.0, np.mean(strip.viewRange()[1])))
    image_view.hover_at(at)

    assert image_view.hover == "x 2: mean 6 counts"


def test_a_line_away_from_the_origin_has_its_own_length(view):
    coords = millimetres([0, 10, 20, 30, 40])
    view.show_frame(image(1.0, (3, 4), counts=False, coords=coords))
    drag(view, "line", (10, 15), (30, 15))
    line = view.measure.tools["line"]

    assert line.stats["length"] == "20 mm"
    distance = view.profiles.profiles["line", "line"][1]
    np.testing.assert_allclose(distance[[0, -1]], [0, 20])


def test_a_crosshair_reads_descending_coordinates_up_to_the_last_pixel(view):
    data, coords = np.arange(12.0).reshape(3, 4), millimetres([40, 30, 20, 10, 0])
    view.show_frame(image(data, data.shape, counts=False, coords=coords))
    view.arm("crosshair")

    assert view.measure.measure_at(35, 5)
    assert view.measure.tools["crosshair"].stats["value"] == 0
    assert view.measure.measure_at(0, 25)
    assert view.measure.tools["crosshair"].stats["value"] == 11


def test_a_box_without_width_measures_the_bin_it_is_in(image_view):
    drag(image_view, "box", (1.2, 0.5), (1.2, 1.5))

    assert image_view.measure.tools["box"].stats["sum"] == 1 + 5


def test_the_box_fields_on_pixel_axes_name_the_first_and_last_pixel(image_view):
    drag(image_view, "box", (0.5, 0.5), (2.5, 1.5))
    menu = measure_menu(image_view.measure, "box")
    fields = form_of(menu)

    assert [fields[f"x {end}"].text() for end in ("from", "to")] == ["1", "2"]


def test_a_line_keeps_its_pixels_and_width_through_new_coordinates(image_view):
    drag(image_view, "line", (0.5, 1), (2.5, 1))
    line = image_view.measure.tools["line"]
    line.place([0.5, 1, 2.5, 1, 2])
    coords = millimetres([0, 10, 20, 30, 40])
    image_view.show_frame(image(1.0, (3, 4), counts=False, coords=coords))

    assert line.points() == pytest.approx([(10, 15), (30, 15)])
    assert line.items[0].get_width() == pytest.approx(20)

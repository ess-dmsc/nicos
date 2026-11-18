import re

import numpy as np
import pyqtgraph as pg
import pytest

from nicos.guisupport.qt import (
    QApplication,
    QEvent,
    QFileDialog,
    QLocale,
    QMenu,
    Qt,
)
from nicos_ess.gui.widgets.pyqtgraph import export
from nicos_ess.gui.widgets.pyqtgraph.curve import Curve
from nicos_ess.gui.widgets.pyqtgraph.image_layer import (
    LEVEL_PERCENTILES,
    ImageLayer,
    _even,
    auto_levels,
)
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import (
    MENU_ORDER,
    HoverBox,
    PlotMenu,
    Title,
    check_action,
    fill_menu,
    number_field,
)
from nicos_ess.gui.widgets.pyqtgraph.theme import CompactAxisItem
from test.nicos_ess.gui.helpers import menu_action, mouse_drag

EDGES = np.arange(11.0)


@pytest.fixture
def plot(qtbot):
    widget = pg.GraphicsLayoutWidget()
    qtbot.addWidget(widget)
    plot = pg.PlotItem(axisItems={"left": CompactAxisItem("left")})
    widget.addItem(plot)
    # The widget owns the plot, so the widget must stay alive.
    yield plot


def test_a_histogram_of_more_bins_than_pixels_draws(plot, qtbot):
    """The pyqtgraph downsampling fails on steps with n values and n + 1 edges."""
    widget = plot.getViewWidget()
    widget.resize(120, 80)
    with qtbot.waitExposed(widget):
        widget.show()
    curve = Curve(plot, "b")
    for bins, steps, hold in [(512, 1, 0), (5000, 1, 0), (5000, 0, 0), (900, 0, 1)]:
        curve.set_data(np.arange(bins + steps), np.random.rand(bins), hold=hold)
        # grab() paints the curve now, and pytest-qt fails on an exception.
        widget.grab()
        assert curve.line.opts["autoDownsample"] == (bins > 4096)


FIRST = np.arange(1.0, 101.0).reshape(10, 10)
FIRST_LEVELS = tuple(np.percentile(FIRST, LEVEL_PERCENTILES))


def test_levels_always_once_or_manual(plot):
    layer = ImageLayer(plot)
    layer.set_image(FIRST, EDGES, EDGES)
    assert layer.levels == pytest.approx(FIRST_LEVELS)

    layer.set_mode("manual")
    layer.set_image(FIRST + 1000, EDGES, EDGES)
    assert layer.levels == pytest.approx(FIRST_LEVELS)

    # The "once" mode makes the next image set the levels, here on a log scale.
    layer.set_mode("once")
    layer.set_log(True)
    layer.set_image(FIRST, EDGES, EDGES)
    assert layer.levels[1] == pytest.approx(FIRST_LEVELS[1], rel=1e-3)
    layer.set_image(FIRST * 10, EDGES, EDGES)
    assert layer.levels[1] == pytest.approx(FIRST_LEVELS[1], rel=1e-3)


def test_auto_levels_of_a_nearly_empty_image_reach_its_few_counts():
    sparse = np.zeros((20, 20))
    # Nearly all values are equal, as early in a count.
    sparse[3, 4] = 50.0
    assert auto_levels(sparse) == (0.0, 50.0)


def test_restored_manual_levels_stay_the_same_on_a_log_scale(plot):
    layer = ImageLayer(plot)
    layer.restore(dict(mode="manual", levels=[0, 2]))
    other = ImageLayer(pg.PlotItem())
    other.restore(layer.state())
    other.set_log(True)
    other.set_image(FIRST, EDGES, EDGES)
    assert other.levels == (0, 2)
    # A level of 0 is drawn at the lowest value.
    assert other.drawn_levels() == pytest.approx((0.0, np.log10(2)))


@pytest.mark.parametrize(
    "damaged", [{"levels": 2}, {"levels": [1]}, {"mode": "x", "levels": [0, 1]}]
)
def test_a_damaged_settings_file_makes_the_levels_follow_the_images(plot, damaged):
    layer = ImageLayer(plot)
    layer.restore(dict(mode="manual", levels=[0, 2]))
    layer.restore(damaged)
    layer.set_image(FIRST, EDGES, EDGES)
    assert layer.mode == "always"
    assert layer.levels == pytest.approx(FIRST_LEVELS)


def test_a_smaller_range_keeps_following(plot):
    """Moving the handles into a smaller range must not count as a drag."""
    layer = ImageLayer(plot)
    layer.set_image(np.array([[0.0, 1e5]]), [0, 1, 2], [0, 1])
    layer.set_log(True)
    layer.set_image(np.array([[1.0, 1e5]]), [0, 1, 2], [0, 1])
    assert layer.follow


def test_float32_and_epoch_time_edges_are_drawn_as_even():
    assert _even(np.arange(513, dtype=np.float32) * np.float32(0.1) + 1000)
    assert _even(1.7633e9 + np.arange(100) * 0.1)
    assert not _even(np.geomspace(1, 100, 10))


def test_nothing_is_drawn_at_or_below_low_exactly(plot):
    """Hiding the lowest step of the colour table would hide the 3 counts too."""
    layer = ImageLayer(plot)
    layer.set_image(np.array([[0.0, 3.0], [500.0, 1000.0]]), [0, 1, 2], [0, 1, 2])
    layer.set_levels(0.0, 1000.0)
    layer.set_transparent_low(True)

    assert np.isnan(layer.image.image[0, 0])
    np.testing.assert_array_equal(layer.image.image.ravel()[1:], [3, 500, 1000])
    layer.set_levels(3.0, 1000.0)
    assert np.isnan(layer.image.image[0, 1])


def test_the_first_image_draws_without_importing_matplotlib(plot, monkeypatch):
    def from_matplotlib(name):
        raise AssertionError(f"{name} came from matplotlib")

    monkeypatch.setattr(pg.colormap, "getFromMatplotlib", from_matplotlib)
    layer = ImageLayer(plot)
    layer.set_image(np.ones((2, 2)), np.arange(3.0), np.arange(3.0))
    layer.set_reversed(True)

    table = pg.colormap.get("viridis", skipCache=True).getLookupTable(nPts=8)
    np.testing.assert_array_equal(layer.cmap.getLookupTable(nPts=8), table[::-1])


def test_a_diverging_colormap_centres_values_of_both_signs_on_zero(plot):
    layer = ImageLayer(plot)
    difference = np.linspace(-20.0, 100.0, 121).reshape(11, 11)
    layer.set_image(difference, np.arange(12.0), np.arange(12.0))
    layer.set_colormap("seismic")
    low, high = layer.levels
    # The white middle of the colormap is at zero.
    assert low == pytest.approx(-high)
    assert high == pytest.approx(np.percentile(difference, LEVEL_PERCENTILES[1]))


# The offscreen platform logs this for popups.
@pytest.mark.qt_log_ignore("This plugin does not support")
def test_a_right_click_opens_our_menu_only(plot, qtbot):
    log = lambda m: check_action(m, "Log", False, lambda _on: None)  # noqa: E731
    fill = lambda entries: entries.update({"Log scale": log})  # noqa: E731
    menus = PlotMenu(plot, fill, plot.vb.autoRange)
    widget = plot.getViewWidget()
    widget.resize(400, 300)
    with qtbot.waitExposed(widget):
        widget.show()
    for item in (plot.vb, plot.getAxis("bottom")):
        at = widget.mapFromScene(item.sceneBoundingRect().center())
        qtbot.mouseMove(widget.viewport(), at)
        qtbot.mouseClick(widget.viewport(), Qt.MouseButton.RightButton, pos=at)
        qtbot.waitUntil(menus.menu.isVisible)
        texts = [a.text() for a in menus.menu.actions() if not a.isSeparator()]
        assert texts == ["Log", "Reset zoom", "Save plot…"]
        assert not plot.vb.menu.isVisible() and not plot.ctrlMenu.isVisible()
        menus.menu.close()


def test_every_plot_menu_has_one_order_whatever_the_owner_adds_first():
    keys = [key for group in MENU_ORDER for key in group]
    menu = QMenu()
    fill_menu(menu, {k: lambda m, k=k: m.addAction(k) for k in reversed(keys)})
    assert [a.text() for a in menu.actions() if not a.isSeparator()] == keys
    assert sum(a.isSeparator() for a in menu.actions()) == len(MENU_ORDER) - 1


def test_submenus_do_not_pile_up_with_each_opening(plot):
    colours = lambda m: m.addMenu("Colours").addAction("x")  # noqa: E731
    fill = lambda entries: entries.update(Colours=colours)  # noqa: E731
    menus = PlotMenu(plot, fill, plot.vb.autoRange)
    for _ in range(5):
        menus.menu.aboutToShow.emit()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert len(menus.menu.findChildren(QMenu)) == 1


def test_save_plot_writes_a_file(plot, tmp_path, monkeypatch):
    monkeypatch.setattr(export, "_saved", "plot")
    target, defaults = tmp_path / "plot.png", []

    def ask(_parent, _caption, default, *_args):
        defaults.append(default)
        return str(target), "PNG image (*.png)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(ask))
    Curve(plot, "b").set_data([0, 1, 2], [1, 3, 2])
    menus = PlotMenu(plot, lambda menu: None, plot.vb.autoRange)
    menu_action(menus, "Save plot…").trigger()
    menu_action(menus, "Save plot…").trigger()
    assert target.stat().st_size > 0
    stamp = r"plot_\d{4}-\d\d-\d\d_\d{6}"
    assert re.fullmatch(stamp, defaults[0])
    # The second dialog starts in the folder of the last saved plot.
    assert re.fullmatch(re.escape(str(tmp_path)) + "/" + stamp, defaults[1])


class TestColourBar:
    @pytest.fixture
    def layer(self, plot, qtbot):
        widget = plot.getViewWidget()
        widget.resize(400, 300)
        with qtbot.waitExposed(widget):
            widget.show()
        layer = ImageLayer(plot)
        layer.set_image(np.arange(100.0).reshape(10, 10), EDGES, EDGES)
        layer.set_levels(20.0, 60.0)
        # The tests map values to pixels, so the 300 px high widget must have
        # laid out the colour bar to its full height first.
        qtbot.waitUntil(lambda: layer.colorbar.vb.sceneBoundingRect().height() > 200)
        return layer

    @staticmethod
    def on_bar(layer, value):
        """Return the widget position of *value* on the colour bar."""
        bar, (low, high) = layer.colorbar.vb.sceneBoundingRect(), layer.colorbar.span
        y = bar.bottom() - (value - low) / (high - low) * bar.height()
        return layer.plot.getViewWidget().mapFromScene(pg.Point(bar.center().x(), y))

    @pytest.mark.parametrize(
        "start, end, levels", [(60, 68, (20, 68)), (40, 45, (25, 65))]
    )
    def test_dragging_a_handle_or_the_band(self, qtbot, layer, start, end, levels):
        viewport = layer.plot.getViewWidget().viewport()
        mouse_drag(qtbot, viewport, self.on_bar(layer, start), self.on_bar(layer, end))
        assert layer.levels == pytest.approx(levels, abs=2)
        kept, span = layer.levels, layer.colorbar.span
        layer.set_image(np.ones((10, 10)), EDGES, EDGES)
        assert layer.levels == kept
        assert layer.colorbar.span == span

    def test_the_scale_stays_while_the_levels_follow_noisy_images(self, layer):
        layer.set_mode("always")
        span = layer.colorbar.span
        for scale in (1.05, 0.95, 1.1):
            layer.set_image(np.arange(100.0).reshape(10, 10) * scale, EDGES, EDGES)
            assert layer.colorbar.span == span
        layer.set_image(np.arange(100.0).reshape(10, 10) * 3, EDGES, EDGES)
        # A much larger image gets a new scale that covers all of it.
        assert layer.colorbar.span[1] > 3 * span[1] / 2
        assert layer.colorbar.span[0] == 0
        layer.set_image(np.arange(100.0).reshape(10, 10) - 10, EDGES, EDGES)
        assert layer.colorbar.span[0] < -10

    def test_clicks_are_the_plots(self, qtbot, layer, monkeypatch):
        clicks = []
        monkeypatch.setattr(
            layer.plot.vb, "mouseClickEvent", lambda ev: clicks.append(ev.double())
        )
        viewport, at = layer.plot.getViewWidget().viewport(), self.on_bar(layer, 65)
        # A drag without movement is a hover and a click.
        mouse_drag(qtbot, viewport, at, at, settle_ms=0)
        qtbot.mouseDClick(viewport, Qt.MouseButton.LeftButton, pos=at)
        qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=at)
        qtbot.mouseClick(viewport, Qt.MouseButton.RightButton, pos=at)
        assert clicks == [True, False]
        assert layer.levels == (20.0, 60.0)
        assert layer.mode == "manual"

    @staticmethod
    def menu_of(layer):
        menu = QMenu()
        layer.add_menu_entries(menu)
        return menu

    def test_the_menu_sets_the_mode(self, layer):
        menu = self.menu_of(layer)
        modes = [a for a in menu.actions() if a.actionGroup()]
        assert [a.isChecked() for a in modes] == [False, False, True]
        modes[1].trigger()
        assert layer.mode == "once"

    def test_the_menu_sets_typed_levels_and_ignores_an_empty_field(self, layer):
        menu = self.menu_of(layer)
        low, high = menu.actions()[0].defaultWidget().fields
        low.setText("10")
        high.setText("1000")
        high.editingFinished.emit()
        assert layer.levels == (10, 1000)
        low.setText("")
        high.editingFinished.emit()
        assert layer.levels == (10, 1000)

    def test_the_menu_sets_the_colormap_and_reverses_it(self, layer):
        menu = self.menu_of(layer)
        colormaps = next(a.menu() for a in menu.actions() if a.menu())
        assert [a.text() for a in colormaps.actions() if a.isChecked()] == ["viridis"]
        next(a for a in colormaps.actions() if a.text() == "seismic").trigger()
        next(a for a in menu.actions() if a.text() == "Reversed").trigger()
        assert tuple(layer.cmap.getColors(mode="byte")[0][:3]) == (128, 0, 0)
        other = ImageLayer(pg.PlotItem())
        other.restore(layer.state())
        assert (other.colormap_name, other.reversed) == ("seismic", True)


def test_numbers_are_typed_with_a_point_on_a_swedish_desktop(qtbot):
    previous = QLocale()
    QLocale.setDefault(QLocale(QLocale.Language.Swedish, QLocale.Country.Sweden))
    try:
        field = number_field(207.5)
        qtbot.addWidget(field)
        field.end(False)
        # The field shows "207." now.
        qtbot.keyClick(field, Qt.Key.Key_Backspace)
        qtbot.keyClicks(field, "25")
    finally:
        QLocale.setDefault(previous)
    assert field.text() == "207.25"
    assert number_field(35808.0500871).cursorPosition() == 0


def test_the_value_axis_keeps_its_room_when_the_labels_get_shorter(plot, qtbot):
    widget = plot.getViewWidget()
    widget.resize(400, 300)
    widget.show()
    axis = plot.getAxis("left")
    widths = []
    # The tick labels change from "1.000M" to "0.2" and back.
    for top in (1e6, 1.0, 1e6):
        plot.setYRange(0, top, padding=0)
        # grab() makes the axis fit its labels.
        widget.grab()
        QApplication.processEvents()
        widths.append(axis.width())
    assert widths[0] > 30 and widths == [widths[0]] * 3


def test_title_parts_stay_put_while_the_numbers_before_them_change(plot):
    title = Title()
    title.setGeometry(0, 0, 2000, title.line_height)

    def shape_x(total):
        title.set_parts(
            "detector", [(f"Σ {total} counts", None, False), ("64×64", None, False)]
        )
        line = title.item.document().firstBlock().layout().lineAt(0)
        return line.cursorToX(title.item.document().toPlainText().index("64×"))[0]

    first = shape_x("1.01M")
    shifts = [shape_x(t) - first for t in ("9950", "10.1k", "999k")]
    assert shifts == pytest.approx([0, 0, 0], abs=0.5)
    assert shape_x("3") < first


def test_a_narrow_title_shortens_the_name_and_leaves_out_whole_parts(plot):
    title = Title()
    title.set_parts(
        "detector_image",
        [("Σ 377.5M counts", None, False)]
        + [("colours fixed", None, True), ("12 s old", None, True)],
    )
    # The name keeps at least 12 letters.
    room = title.bold.horizontalAdvance("detect…image")
    room += title.plain.horizontalAdvance(" · colours fixed · 12 s old")
    title.setGeometry(0, 0, room + 10, title.line_height)
    assert title.text.endswith("12 s old</span>")
    assert "detect…image" in title.text
    assert "377.5M" not in title.text


def test_a_narrow_title_cuts_a_long_part_between_words(plot):
    title = Title()
    note = "background not applied: taken at another binning"
    parts = [(note, None, True), ("Σ 1.2M", None, False), ("120 bins", None, False)]
    title.set_parts("detector", parts + [("− background", None, True)], ["hint"])
    title.setGeometry(0, 0, 2000, title.line_height)
    assert note in title.text and "120 bins" in title.text
    title.setGeometry(0, 0, 450, title.line_height)
    assert "detector" in title.text and "1.2M" not in title.text
    # The text is cut between words, starting with the first part.
    assert "taken at another …" in title.text
    assert "− background" not in title.text
    assert title.toolTip().split("\n")[-2:] == ["− background", "hint"]


def test_a_narrow_title_cuts_no_number(plot):
    title = Title()
    title.set_parts(
        "monitor_1", [("ADC counts", None, True), ("FWHM " + "9" * 80, None, True)]
    )
    room = title.bold.horizontalAdvance("monitor_1 · ADC counts")
    # There is room for the word FWHM but not for its value.
    room += title.plain.horizontalAdvance(" · FWHM …")
    title.setGeometry(0, 0, room + 20, title.line_height)
    assert "FWHM" not in title.item.document().toPlainText()


def test_a_point_between_gaps_is_marked_where_lines_draw_nothing(plot):
    curve = Curve(plot, "b")
    curve.set_data([0, 1, 2, 3, 4], [1, np.nan, 2, np.nan, 3])

    assert list(curve.lone.data["x"]) == [0, 2, 4] and curve.lone.isVisible()
    curve.set_data([0, 1, 2], [1, 2, 3])
    assert not curve.lone.isVisible()


def test_the_hover_box_stays_inside_and_keeps_the_nearest_rows(plot):
    parent = pg.GraphicsWidget()
    # The parent has room for only a few rows.
    parent.resize(400, 120)
    box = HoverBox(parent)
    rows = [(pg.mkColor("r"), f"curve {i}", f"{i} mm", abs(i - 7)) for i in range(20)]
    box.show_rows("time 12:00:05", rows, pg.Point(390, 110), parent.boundingRect())

    text = box.label.toPlainText()
    assert "time 12:00:05" in text and "curve 7" in text and "more" in text
    # Only the rows nearest to the pointer fit, so curves 0 and 19 are left out.
    assert "curve 0" not in text and "curve 19" not in text
    assert re.search(r"font-weight:\s*[67]00[^>]*>curve 7<", box.label.toHtml())
    rect = box.mapRectToParent(box.boundingRect())
    # The box moves to the left of and above the pointer.
    assert parent.boundingRect().contains(rect)
    assert rect.right() < 390 and rect.bottom() < 110
    box.show_rows("", [], pg.Point(0, 0), parent.boundingRect())
    assert not box.isVisible()

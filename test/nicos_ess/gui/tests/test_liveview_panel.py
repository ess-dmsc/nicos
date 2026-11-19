"""Tests for the live view panel fed by the fake daemon.

The tests for FrameView itself are in widgets/test_frame_plot.py.
"""

from __future__ import annotations

import gc
import json
import time
from dataclasses import replace

import numpy as np
import pyqtgraph as pg
import pytest

from nicos.clients.gui.utils import SettingGroup
from nicos.guisupport.qt import (
    QApplication,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QEvent,
    QMainWindow,
    QMenu,
    QMimeData,
    QPainter,
    QPixmap,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTabBar,
    QTabWidget,
    QWidget,
    sip,
)
from nicos_ess.gui import live_hub
from nicos_ess.gui.panels import liveview
from nicos_ess.gui.panels.live_cards import MIME, paint_picture, plot_mime
from nicos_ess.gui.panels.live_grid import LiveGrid
from nicos_ess.gui.panels.liveview import LiveViewPanel, saved_spans
from nicos_ess.utilities import live_frame
from nicos_ess.utilities.grid_layout import find, insert
from nicos_ess.utilities.live_frame import Coord, Frame
from test.nicos_ess.gui.doubles.fake_transport import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    menu_action,
    mouse_drag,
    mouse_held,
    mouse_move,
    single_panel_guiconfig_string,
)
from test.nicos_ess.gui.widgets.frames import cube, deliver, histogram, live_event

PANEL = "nicos_ess.gui.panels.liveview.LiveViewPanel"


def clear_saved_views():
    for group in (live_hub.SETTINGS, LiveViewPanel.panelName):
        with SettingGroup(group) as settings:
            settings.remove("")


@pytest.fixture(autouse=True)
def no_saved_live_views():
    """Closing a window saves the view settings, so each test starts clean."""
    clear_saved_views()
    yield
    clear_saved_views()


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    window.show()  # Plots are only drawn while the panel is on screen.
    qtbot.waitUntil(panel.isVisible)
    return panel


def test_every_output_gets_a_plot_with_its_new_data(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    qtbot.waitUntil(lambda: panel.shown() == ["detector_image", "monitor_1"])

    deliver(qtbot, fake_daemon, panel, histogram(data=np.full(3, 2.0)))

    view = panel.views["monitor_1"]
    qtbot.waitUntil(lambda: list(view.curve.line.yData) == [2.0, 2.0, 2.0])
    assert view.history is panel.hub.series["monitor_1"]


def test_many_outputs_at_once_get_their_plots_over_several_turns(
    panel, fake_daemon, qtbot, monkeypatch
):
    monkeypatch.setattr(liveview, "DRAW_BUDGET", 0.0)
    made = []
    panel.hub.arrived.connect(lambda _names: made.append(len(panel.views)))
    frames = [histogram(name=f"monitor_{i}") for i in range(3)]
    deliver(qtbot, fake_daemon, panel, *frames, device="collector")

    assert made[0] == 1
    qtbot.waitUntil(lambda: len(panel.views) == 3)


def test_outputs_of_unloaded_devices_are_forgotten(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), device="collector")
    deliver(qtbot, fake_daemon, panel, cube(), device="camera")
    qtbot.waitUntil(lambda: "monitor_1" in panel.views)
    panel.views["monitor_1"].set_log(True)
    # A loaded device with the name of an output does not keep the output.
    fake_daemon.add_device(DeviceSpec("monitor_1", valuetype=int))
    fake_daemon.add_device(DeviceSpec("camera", valuetype=int))

    fake_daemon.push_setup()

    qtbot.waitUntil(lambda: panel.shown() == ["detector_image"])
    assert panel.hub.names() == ["detector_image"]
    # The output gets its plot settings back when it comes again.
    deliver(qtbot, fake_daemon, panel, histogram(), device="collector")
    qtbot.waitUntil(lambda: "monitor_1" in panel.views)
    assert panel.views["monitor_1"].log


def test_only_the_plot_settings_of_the_latest_outputs_are_saved(panel):
    hub = panel.hub
    for i in range(live_hub.SAVED_PLOTS + 1):
        hub.states_of(f"output_{i}")["1"] = {"log": True}
    hub.states_of("output_0")

    hub.save()

    with SettingGroup(live_hub.SETTINGS) as settings:
        saved = json.loads(settings.value("hub"))["views"]
    assert len(saved) == live_hub.SAVED_PLOTS
    assert "output_0" in saved
    assert "output_1" not in saved


@pytest.mark.parametrize(
    "change, total",
    [(dict(unit="K"), 6.0), (dict(counts=False), 2.0)],
    ids=["unit", "counts"],
)
def test_the_totals_start_again_when_an_output_changes_what_it_measures(
    panel, fake_daemon, qtbot, change, total
):
    deliver(qtbot, fake_daemon, panel, histogram())
    series = panel.hub.series["monitor_1"]
    assert set(series.arrays()[1]) == {14.0}

    deliver(qtbot, fake_daemon, panel, histogram(data=np.full(3, 2.0), **change))

    assert panel.hub.series["monitor_1"] is series
    assert set(series.arrays()[1]) == {total}


def test_the_totals_start_again_when_an_output_comes_from_another_device(panel):
    # esslivedata stamps its frames with data times ahead of the clock here.
    ahead = histogram(meta=dict(time=time.time() + 60))
    panel.hub.on_livedata(*live_event([ahead], "livedata_collector"))
    series = panel.hub.series["monitor_1"]
    panel.hub.on_livedata(*live_event([histogram(data=np.ones(3))], "jbi_detector"))

    assert panel.hub.series["monitor_1"] is series
    assert list(series.arrays()[1]) == [3.0]


@pytest.mark.parametrize(
    "spoil",
    [
        lambda event: event["datadescs"][1]["frame"]["meta"].update(time="soon"),
        lambda event: event["datadescs"][1]["frame"].update(dims=["x"]),
        lambda event: event["datadescs"][1]["frame"].pop("coords"),
        lambda event: event.pop("det"),
    ],
    ids=["time", "dims", "coords", "det"],
)
def test_an_unreadable_event_is_left_out_as_a_whole(panel, spoil):
    params, blobs = live_event([histogram(), cube()], "detector")
    spoil(params)

    panel.hub.on_livedata(params, blobs)

    assert panel.hub.names() == []
    assert panel.hub.series == {}
    panel.hub.on_livedata(*live_event([histogram(), cube()], "detector"))
    assert panel.hub.names() == ["detector_image", "monitor_1"]


def test_a_view_closed_after_the_hub_is_gone_raises_nothing(panel, qtbot):
    hub = live_hub.LiveHub(panel.client, panel.log)
    view = QWidget()
    view.index = 2
    hub.register(view)

    sip.delete(hub)
    sip.delete(view)
    qtbot.wait(10)


def test_the_plot_that_waited_longest_is_drawn_first(
    panel, fake_daemon, qtbot, monkeypatch
):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    # A slow machine must not run out of time before the second plot.
    monkeypatch.setattr(liveview, "DRAW_BUDGET", 60)
    order, draw = [], panel._draw
    monkeypatch.setattr(panel, "_draw", lambda name: (order.append(name), draw(name)))
    panel.drawn.clear()
    panel.drawn["detector_image"] = time.monotonic()
    panel.dirty.update(panel.views)

    panel.draw_dirty()

    assert order == ["monitor_1", "detector_image"]
    assert not panel.dirty


def test_a_hidden_plot_comes_back_with_show_all(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())

    panel.views["monitor_1"].hide_requested.emit()
    assert panel.shown() == ["detector_image"]
    panel.show_all()
    assert panel.shown() == ["detector_image", "monitor_1"]


def test_a_plot_shown_alone_goes_back_into_the_grid_from_its_menu(
    panel, fake_daemon, qtbot
):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    monitor = panel.views["monitor_1"]

    monitor.solo_requested.emit()
    assert panel.shown() == ["monitor_1"]
    assert "only this plot" in monitor.title_item.toolTip()
    menu_action(monitor.plot_menu, "Only this plot (double-click)").trigger()
    assert panel.shown() == ["detector_image", "monitor_1"]
    assert "only this plot" not in monitor.title_item.toolTip()


def test_hiding_a_plot_shown_alone_shows_the_others(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    monitor = panel.views["monitor_1"]

    monitor.solo_requested.emit()
    monitor.hide_requested.emit()

    assert panel.shown() == ["detector_image"]
    assert not any(c.isWindow() for c in panel.canvases.values())


def test_a_plot_made_while_drawing_failed_can_be_hidden_again(
    panel, fake_daemon, qtbot, monkeypatch
):
    first = [histogram(), histogram(name="monitor_2")]
    deliver(qtbot, fake_daemon, panel, *first, device="collector")
    monitor = panel.views["monitor_1"]
    monitor.solo_requested.emit()

    def broken(*_args):
        raise ValueError("a frame that this plot cannot draw")

    # The new plot shows the plot alone among the others again, and that
    # draws the monitor.
    monkeypatch.setattr(monitor, "show_frame", broken)
    with qtbot.capture_exceptions() as errors:
        deliver(qtbot, fake_daemon, panel, histogram(), cube(), device="collector")
    assert errors
    monkeypatch.undo()
    panel.views["detector_image"].hide_requested.emit()

    assert panel.shown() == ["monitor_1", "monitor_2"]


def test_an_output_far_behind_the_others_is_marked(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    frame, received = panel.hub.outputs["monitor_1"]
    panel.hub.outputs["monitor_1"] = (frame, received - 30)
    panel.hub.resumed = received - 30  # The count has run for 30 s.

    panel.update_ages()

    assert panel.views["monitor_1"].lagging
    assert not panel.views["detector_image"].lagging
    panel.hub.resumed = received  # No output is late in a count that just started.
    panel.update_ages()
    assert not panel.views["monitor_1"].lagging


def test_a_time_series_keeps_its_own_samples(panel, fake_daemon, qtbot):
    times = (np.array([0, 1, 2]) + time.time() - 10) * 10**9
    coords = {"time": Coord(("time",), times, "datetime64[ns]")}
    samples = Frame(np.array([1.0, 2.0, 3.0]), ("time",), name="temp", coords=coords)

    deliver(qtbot, fake_daemon, panel, samples)
    qtbot.waitUntil(lambda: panel.views["temp"].curve is not None)
    qtbot.wait(300)  # Let the plot redraw a few times.

    assert panel.hub.series["temp"].arrays()[1].tolist() == [1, 2, 3]


def test_every_plot_keeps_room_through_rearranging(panel, fake_daemon, qtbot):
    frames = [histogram(name=f"monitor_{i}") for i in range(3)]
    frames += [replace(cube(), name=f"image_{i}") for i in range(4)]
    deliver(qtbot, fake_daemon, panel, *frames)
    for step in (
        lambda: panel.window().resize(1600, 600),
        lambda: panel.set_hidden("monitor_0", True),
        lambda: panel.set_hidden("monitor_0", False),
        lambda: panel.window().resize(700, 1000),
        lambda: panel.window().resize(1000, 800),
    ):
        step()
        qtbot.wait(150)

    qtbot.waitUntil(lambda: len(panel.shown()) == 7)
    for view in panel.views.values():
        assert view.plot.geometry().width() > 50
        assert view.plot.geometry().height() > 30
    # A plot that moved to another grid still draws new data.
    deliver(qtbot, fake_daemon, panel, histogram(name="monitor_0", data=np.ones(3)))
    view = panel.views["monitor_0"]
    qtbot.waitUntil(lambda: list(view.curve.line.yData) == [1.0, 1.0, 1.0])


class Settings(dict):
    setValue = dict.__setitem__

    def value(self, key, default=None):
        return self.get(key, default)


def test_settings_survive_a_restart(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    panel.views["detector_image"].set_choice("wavelength")
    panel.views["detector_image"].set_full_profiles(True)
    panel.set_hidden("monitor_1", True)
    settings = Settings()
    panel.saveSettings(settings)
    panel.loadSettings(settings)
    with SettingGroup(live_hub.SETTINGS) as shared:
        hub = json.loads(shared.value("hub"))

    assert hub["placement"]["monitor_1"] == []
    assert hub["views"]["detector_image"]["1"]["view"] == "wavelength"
    assert hub["views"]["detector_image"]["1"]["profiles"] is True


THREE_VIEWS = single_panel_guiconfig_string(PANEL).replace(
    f"main_window = panel({PANEL!r})",
    "main_window = tabbed(\n"
    + "".join(f"    ('Live {i}', panel({PANEL!r}, index={i})),\n" for i in (1, 2, 3))
    + ")",
)


@pytest.fixture
def views(gui_window_factory, fake_daemon, qtbot):
    window = gui_window_factory(guiconfig_string=THREE_VIEWS)
    found = sorted(window.findChildren(LiveViewPanel), key=lambda p: p.index)
    window.show()
    qtbot.waitUntil(found[0].isVisible)
    return found


def test_several_views_share_one_hub(views):
    one, two, three = views
    assert one.hub is two.hub is three.hub
    assert two.panelName == "Live view 2"
    assert "No live data yet" in two.grid.empty_text
    assert not two.tool_bar.isEnabled()
    menu = QMenu()
    two._layout_entries(menu)
    assert menu.isEmpty()


def test_new_outputs_go_to_the_first_view(views, fake_daemon, qtbot):
    one, two, _three = views

    deliver(qtbot, fake_daemon, one, histogram(), cube())

    assert sorted(one.views) == ["detector_image", "monitor_1"]
    assert one.tool_bar.isEnabled() and two.views == {}
    assert "Nothing placed in Live 2" in two.grid.empty_text


def test_an_output_placed_in_a_missing_view_goes_to_the_first(views):
    hub = views[0].hub
    hub.placement["x"] = [7]  # This GUI has no view 7.
    assert hub.where("x") == [1]


def test_a_right_click_on_a_plot_leaves_the_menu_to_the_plot(
    panel, fake_daemon, qtbot, monkeypatch
):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    shown = []
    monkeypatch.setattr(QMenu, "exec", lambda menu, *args: shown.append(menu))
    canvas = panel.canvases["monitor_1"]
    qtbot.waitUntil(lambda: canvas.isVisible())
    panel._empty_menu(canvas.mapTo(panel.grid, canvas.rect().center()))
    assert shown == []


@pytest.mark.parametrize("across", [0.6, 0.95])
def test_a_right_click_anywhere_on_the_title_opens_the_plot_menu(
    two_plots, qtbot, across
):
    view, canvas = two_plots.views["monitor_1"], two_plots.canvases["monitor_1"]
    opened = []
    view.plot_menu.open = opened.append
    rect = view.title_item.sceneBoundingRect()
    point = QPointF(rect.left() + across * rect.width(), rect.center().y())
    at = canvas.mapFromScene(point)
    qtbot.mouseClick(canvas.viewport(), Qt.MouseButton.RightButton, pos=at)
    qtbot.wait(50)
    assert len(opened) == 1


def test_plot_and_panel_menus_move_and_show_plots(views, fake_daemon, qtbot):
    one, two, three = views
    deliver(qtbot, fake_daemon, one, histogram(), cube())
    view = one.views["detector_image"]
    qtbot.waitUntil(lambda: view.view is not None)

    move = menu_action(view.plot_menu, "Move to").menu()
    assert [a.text() for a in move.actions()] == ["Live 2", "Live 3"]
    menu_action(view.plot_menu, "Live 3").trigger()
    assert sorted(one.views) == ["monitor_1"] and "detector_image" in three.views

    one.set_hidden("monitor_1", True)  # Every view offers it again.
    assert one.views == {} and two.views == {}
    menu = QMenu()
    two._layout_entries(menu)
    next(a for a in menu.actions() if a.text() == "monitor_1").trigger()
    assert "monitor_1" in two.views


def test_a_plot_in_several_views_is_decoded_once(
    views, fake_daemon, qtbot, monkeypatch
):
    one, two, three = views
    deliver(qtbot, fake_daemon, one, histogram())
    one.hub.show_in("monitor_1", 3, True)
    assert "monitor_1" in three.views and "monitor_1" not in two.views
    decoded, events, decode = [], [], live_frame.decode

    def counting_decode(*args):
        decoded.append(1)
        return decode(*args)

    monkeypatch.setattr(live_frame, "decode", counting_decode)
    one.client.livedata.connect(lambda *a: events.append(1))

    deliver(qtbot, fake_daemon, one, histogram(data=np.full(3, 7.0)))
    curve = one.views["monitor_1"].curve
    qtbot.waitUntil(lambda: list(curve.line.yData) == [7.0] * 3)

    assert events and len(decoded) == len(events)


def test_each_view_keeps_its_own_plot_settings(views, fake_daemon, qtbot):
    one, _two, three = views
    deliver(qtbot, fake_daemon, one, histogram())
    one.hub.show_in("monitor_1", 3, True)

    one.views["monitor_1"].set_log(True)
    one.saveSettings(Settings())
    three.saveSettings(Settings())
    states = one.hub.view_states["monitor_1"]
    assert states["1"]["log"] and not states["3"]["log"]


def test_a_tool_is_armed_on_every_plot_and_esc_goes_back(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    view = panel.views["detector_image"]
    qtbot.waitUntil(lambda: view.image is not None)
    measure = menu_action(view.plot_menu, "Measure").menu()
    next(a for a in measure.actions() if a.text() == "Box").trigger()

    assert all(v.armed == "box" for v in panel.views.values())
    checked = [k for k, a in panel.tool_actions.items() if a.isChecked()]
    assert checked == ["box"]
    canvas = panel.canvases["detector_image"]
    QApplication.setActiveWindow(panel.window())
    canvas.setFocus()
    qtbot.keyClick(canvas, Qt.Key.Key_Escape)  # Esc only works with focus.
    assert all(v.armed is None for v in panel.views.values())
    assert panel.tool_actions["pan"].isChecked()


def test_an_armed_tool_neither_measures_nor_pans_a_curve(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram())
    canvas, view = panel.canvases["monitor_1"], panel.views["monitor_1"]
    qtbot.waitUntil(lambda: view.curve is not None)
    panel.set_tool("box")
    centre = canvas.mapFromScene(view.plot.vb.sceneBoundingRect().center())

    mouse_drag(qtbot, canvas.viewport(), centre, centre + QPoint(80, 40))

    assert not view.zoomed() and view.measure.tools == {}
    # The same drag with the pan tool moves the curve, so the drag reaches the plot.
    panel.set_tool("pan")
    mouse_drag(qtbot, canvas.viewport(), centre, centre + QPoint(80, 40))
    assert view.zoomed()


def test_clear_removes_every_measurement_and_its_profile(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, cube())
    view = panel.views["detector_image"]
    view.arm("crosshair")
    assert view.measure.measure_at(1.0, 1.0) and view.profiles.profiles

    panel.clear_measures()

    assert view.measure.tools == {} and view.profiles.profiles == {}


def test_a_drag_starts_where_the_pointer_pressed_and_moves_nothing_else(
    panel, fake_daemon, qtbot
):
    """The first line adds profile strips, which move the image under the pointer.

    A drag that starts on a measurement draws a new one and leaves the old one
    where it is.
    """
    image = Frame(np.random.rand(64, 64), ("y", "x"), name="camera")
    deliver(qtbot, fake_daemon, panel, image)
    panel.resize(1200, 700)
    qtbot.wait(200)
    view, canvas = panel.views["camera"], panel.canvases["camera"]
    vb = view.plot.vb

    def drag(tool, start, end):
        panel.set_tool(tool)
        qtbot.wait(100)
        at = canvas.mapFromScene(vb.mapViewToScene(pg.Point(*start)))
        pressed = vb.mapSceneToView(canvas.mapToScene(at))
        if isinstance(end, tuple):
            end = canvas.mapFromScene(vb.mapViewToScene(pg.Point(*end)))
        mouse_drag(qtbot, canvas.viewport(), at, end)
        if tool == "line":  # A box snaps to whole bins.
            first, _end = view.measure.tools[tool].points()
            assert first == pytest.approx((pressed.x(), pressed.y()), abs=1e-6)

    drag("line", (10, 50), (50, 20))
    drag("box", (10, 10), (30, 30))
    box = view.measure.tools["box"].points()
    drag("line", (20, 20), QPoint(600, 150))  # This starts inside the box.
    assert view.measure.tools["box"].points() == pytest.approx(box)


def cells_of(panel):
    return {cell.name: cell.rect() for cell in panel.grid.cells}


def title_point(panel, name):
    """Return a point on the title of *name* right of its name, in the viewport."""
    rect = panel.views[name].title_item.sceneBoundingRect()
    point = QPointF(rect.left() + 0.8 * rect.width(), rect.center().y())
    return panel.canvases[name].mapFromScene(point)


def settled(qtbot, panel):
    qtbot.waitUntil(lambda: not panel.grid.layer.isVisible(), timeout=2000)


@pytest.fixture
def two_plots(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    panel.window().resize(1200, 600)
    qtbot.waitUntil(lambda: panel.grid.width() > 1000)
    qtbot.wait(100)
    return panel


def test_a_plot_dragged_onto_one_of_the_same_size_swaps_with_it(two_plots, qtbot):
    panel = two_plots
    start = title_point(panel, "monitor_1")
    away = start - QPoint(panel.grid.width() // 2, 0)
    mouse_drag(qtbot, panel.canvases["monitor_1"].viewport(), start, away)
    settled(qtbot, panel)

    assert cells_of(panel) == {
        "monitor_1": (0, 0, 6, 1),
        "detector_image": (6, 0, 6, 1),
    }
    assert panel.spans == [("monitor_1", 6, 1), ("detector_image", 6, 1)]
    cell = find(panel.grid.cells, "detector_image")
    assert panel.grid.cards["detector_image"].geometry() == panel.grid.frame(cell)


def test_while_dragging_the_rows_keep_their_height(two_plots, fake_daemon, qtbot):
    panel, grid = two_plots, two_plots.grid
    deliver(qtbot, fake_daemon, panel, histogram(name="extra"))
    viewport = panel.canvases["detector_image"].viewport()
    heights = {n: c.height() for n, c in grid.cards.items()}
    end = viewport.mapFromGlobal(grid.mapToGlobal(QPoint(600, grid.height() - 10)))
    start = title_point(panel, "detector_image")
    with mouse_held(qtbot, viewport, start, end):
        qtbot.wait(300)
        assert grid.session.key == ("row",)
        assert all(grid.shown[n].height() == heights[n] for n in ("extra", "monitor_1"))
    settled(qtbot, panel)
    assert cells_of(panel)["detector_image"] == (0, 1, 12, 1)
    assert cells_of(panel)["monitor_1"] == (6, 0, 6, 1)


def test_a_short_move_or_a_click_on_the_title_drags_nothing(two_plots, qtbot):
    panel = two_plots
    viewport = panel.canvases["monitor_1"].viewport()
    opened = []
    panel.views["monitor_1"].plot_menu.open = opened.append
    start = title_point(panel, "monitor_1")
    distance = QApplication.startDragDistance() - 2

    mouse_drag(qtbot, viewport, start, start + QPoint(distance, 0))
    title = panel.views["monitor_1"].title_item
    name = panel.canvases["monitor_1"].mapFromScene(
        title.mapToScene(QPointF(title.name_end - 2, title.boundingRect().center().y()))
    )
    mouse_drag(qtbot, viewport, name, name, settle_ms=50)

    assert len(opened) == 1
    assert panel.spans == [] and panel.grid.session is None


def test_a_plot_dragged_away_and_back_stays_and_the_next_drag_works(two_plots, qtbot):
    panel = two_plots
    viewport = panel.canvases["monitor_1"].viewport()
    start = title_point(panel, "monitor_1")
    away = start - QPoint(panel.grid.width() // 2, 0)
    mouse_drag(qtbot, viewport, start, away, start)
    settled(qtbot, panel)
    assert cells_of(panel)["monitor_1"] == (6, 0, 6, 1)
    assert panel.spans == []

    sip.delete(panel.grid.lift)  # as when the window of the last drag was closed
    mouse_drag(qtbot, viewport, start, away)
    settled(qtbot, panel)
    assert cells_of(panel)["monitor_1"] == (0, 0, 6, 1)


def test_esc_puts_a_dragged_plot_back(two_plots, qtbot):
    panel = two_plots
    viewport = panel.canvases["monitor_1"].viewport()
    start = title_point(panel, "monitor_1")
    with mouse_held(qtbot, viewport, start, start - QPoint(500, 0)):
        assert panel.grid.session is not None and panel.grid.layer.isVisible()
        qtbot.keyClick(viewport, Qt.Key.Key_Escape)
        qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=start)
    settled(qtbot, panel)

    assert panel.grid.session is None
    assert panel.spans == []
    assert cells_of(panel)["monitor_1"] == (6, 0, 6, 1)


def test_the_age_update_does_not_fail_on_an_output_forgotten_during_a_drag(
    two_plots, qtbot
):
    panel = two_plots
    viewport = panel.canvases["monitor_1"].viewport()
    start = title_point(panel, "monitor_1")
    with mouse_held(qtbot, viewport, start, start - QPoint(300, 0)):
        assert panel.grid.session is not None
        # A setup change unloads the device of the other plot during the drag.
        panel.hub.drop("detector_image")
        panel.update_ages()  # The panel calls this every second.
    settled(qtbot, panel)

    assert sorted(panel.views) == ["monitor_1"]


def test_a_plot_kept_through_a_drag_follows_the_totals_of_the_next_count(
    two_plots, fake_daemon, qtbot
):
    panel = two_plots
    viewport = panel.canvases["detector_image"].viewport()
    start = title_point(panel, "detector_image")
    end = start - QPoint(300, 0)
    with mouse_held(qtbot, viewport, start, end):
        # The setup is loaded again while the button is held, and a new count
        # starts.
        fake_daemon.add_device(DeviceSpec("detector_image", valuetype=int))
        fake_daemon.push_setup()
        qtbot.waitUntil(lambda: "monitor_1" not in panel.hub.outputs)
        deliver(qtbot, fake_daemon, panel, histogram())
    settled(qtbot, panel)

    assert panel.views["monitor_1"].history is panel.hub.series["monitor_1"]


def test_the_edges_of_a_plot_resize_it_and_its_neighbour_gives_room(two_plots, qtbot):
    grid = two_plots.grid
    grid.show_grips("detector_image")
    grip = grid.grips["e"]
    assert grip.isVisible() and grip.cursor().shape() == Qt.CursorShape.SizeHorCursor
    start = grip.rect().center()

    mouse_drag(qtbot, grip, start, start + QPoint(grid.width() // 6, 0))
    settled(qtbot, two_plots)

    assert cells_of(two_plots) == {
        "detector_image": (0, 0, 8, 1),
        "monitor_1": (8, 0, 4, 1),
    }
    assert grid.cards["detector_image"].width() > grid.width() // 2


def test_a_plot_that_arrives_while_the_layer_fades_gets_its_place(
    two_plots, fake_daemon, qtbot, monkeypatch
):
    panel, grid = two_plots, two_plots.grid
    fade_out, arrived = grid._fade_out, []

    def arrive_then_fade():
        # The real cards are laid out under the layer when a new output comes.
        if not arrived:
            arrived.append(not grid.layer.isHidden())
            panel.hub.on_livedata(*live_event([histogram(name="extra")], "extra"))
        fade_out()

    monkeypatch.setattr(grid, "_fade_out", arrive_then_fade)
    grid.show_grips("monitor_1")
    grip = grid.grips["s"]
    start = grip.rect().center()
    mouse_drag(qtbot, grip, start, start + QPoint(0, 150))
    qtbot.waitUntil(lambda: arrived == [True], timeout=2000)
    settled(qtbot, panel)

    frames = grid.frames()
    assert "extra" in frames and grid.cards["extra"].isVisible()
    for name, card in grid.cards.items():
        assert card.geometry() == frames[name].toRect()


def test_a_resize_ends_when_the_button_is_released_anywhere(two_plots, qtbot):
    grid, elsewhere = two_plots.grid, two_plots.tool_bar
    grid.show_grips("monitor_1")
    grip = grid.grips["se"]
    start = grip.rect().center()
    with mouse_held(qtbot, grip, start, start + QPoint(0, 200)):
        # The pointer left the grip, which must keep the grab until the release.
        grip.leaveEvent(QEvent(QEvent.Type.Leave))
        qtbot.wait(50)
        assert grid.session is not None and grip.isVisible()
        # The release goes to another window, or Qt loses it and the next move
        # comes without the button.
        qtbot.mouseRelease(elsewhere, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        assert grid.session is None
    settled(qtbot, two_plots)
    assert cells_of(two_plots)["monitor_1"] == (6, 0, 6, 2)

    grid.show_grips("monitor_1")
    with mouse_held(qtbot, grip, start, start - QPoint(0, 100)):
        mouse_move(qtbot, elsewhere, QPoint(5, 5), Qt.MouseButton.NoButton)
        assert grid.session is None


def test_the_arrangement_survives_a_restart(gui_window_factory, fake_daemon, qtbot):
    saved = [["monitor_1", 4, 2], ["detector_image", 8, 1]]
    with SettingGroup(LiveViewPanel.panelName) as settings:
        settings.setValue("liveview", json.dumps(dict(grid=saved)))
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    window.show()
    deliver(qtbot, fake_daemon, panel, histogram(), cube())

    assert cells_of(panel) == {
        "monitor_1": (0, 0, 4, 2),
        "detector_image": (4, 0, 8, 2),
    }
    settings = Settings()
    panel.saveSettings(settings)
    assert json.loads(settings["liveview"]) == dict(grid=saved)


def test_damaged_saved_spans_are_left_out():
    grid = [5, ["a", 6, 1], ["a", 4, 2], ["b", "6", 1], ["c", None, 1]]
    grid += [["d", 6.5, 1], ["e", True, 1], [None, 6, 1], ["f", 40, 10**6]]
    assert saved_spans(dict(grid=grid)) == [("a", 6, 1), ("f", 40, 10**6)]
    assert saved_spans([]) == []


DAMAGED_HUB = [
    [],
    {"placement": [["monitor_1", 1]]},
    {"placement": {"monitor_1": 1, "detector_image": [1, "2", None]}},
    {"placement": None, "views": [1, 2]},
    {"views": {"monitor_1": [1, 2], "detector_image": "log"}},
]


@pytest.mark.parametrize("saved", DAMAGED_HUB)
def test_damaged_hub_settings_are_left_out(
    saved, gui_window_factory, fake_daemon, qtbot
):
    with SettingGroup(live_hub.SETTINGS) as settings:
        settings.setValue("hub", json.dumps(saved))
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    window.show()
    deliver(qtbot, fake_daemon, panel, histogram(), cube())

    assert sorted(panel.views) == ["detector_image", "monitor_1"]


PRESET = {"monitor_*": (0, 0, 4, 2), "detector_image": (4, 0, 8, 1)}


def test_the_guiconfig_layout_holds_until_the_user_arranges(
    gui_window_factory, fake_daemon, qtbot
):
    config = single_panel_guiconfig_string(PANEL, layout=PRESET)
    window = gui_window_factory(guiconfig_string=config)
    panel = get_panel_by_class(window, PANEL)
    window.show()
    frames = [histogram(), cube(), histogram(name="extra")]
    deliver(qtbot, fake_daemon, panel, *frames)

    preset = cells_of(panel)
    assert preset["monitor_1"] == (0, 0, 4, 2) and preset["detector_image"][2] == 8
    assert preset["extra"] == (0, 2, 12, 1)  # The preset leaves it out.
    panel.keep_arrangement(insert(panel.grid.cells, "extra", "monitor_1", False))
    assert cells_of(panel)["extra"] == (0, 0, 4, 2)
    menu_action(panel.views["extra"].plot_menu, "Reset layout").trigger()
    assert cells_of(panel) == preset
    assert panel.spans == []


def test_options_written_slightly_wrong_still_work(
    gui_window_factory, fake_daemon, qtbot
):
    layout = {"monitor_*": (0, 0, 4), "detector_image": (4, 0, 8, 1)}
    config = single_panel_guiconfig_string(PANEL, outputs="monitor_*", layout=layout)
    window = gui_window_factory(guiconfig_string=config)
    panel = get_panel_by_class(window, PANEL)
    window.show()
    deliver(qtbot, fake_daemon, panel, histogram(), cube())

    assert panel.outputs == ["monitor_*"]
    assert sorted(cells_of(panel)) == ["detector_image", "monitor_1"]


def test_a_plot_shown_alone_fills_the_grid_and_comes_back(two_plots, qtbot):
    panel = two_plots
    grid = panel.grid
    before = cells_of(panel)
    panel.views["monitor_1"].solo_requested.emit()

    assert grid.solo == "monitor_1"
    assert not grid.cards["detector_image"].isVisible()
    alone = grid.cards["monitor_1"].geometry()
    assert alone.width() > grid.width() - 30 and alone.height() > grid.height() - 30
    grid.show_grips("monitor_1")
    assert not any(grip.isVisible() for grip in grid.grips.values())

    panel.views["monitor_1"].solo_requested.emit()
    assert grid.solo is None and cells_of(panel) == before
    assert grid.cards["detector_image"].isVisible()


def test_a_drag_from_a_plot_shown_alone_shows_all_and_moves_it(two_plots, qtbot):
    panel, grid = two_plots, two_plots.grid
    before = cells_of(panel)
    panel.views["monitor_1"].solo_requested.emit()
    viewport = panel.canvases["monitor_1"].viewport()
    rect = panel.views["monitor_1"].title_item.sceneBoundingRect()
    point = QPointF(rect.left() + 0.3 * rect.width(), rect.center().y())
    start = panel.canvases["monitor_1"].mapFromScene(point)
    with mouse_held(qtbot, viewport, start, start + QPoint(0, 20)):
        assert grid.solo is None and not panel.views["monitor_1"].solo
        assert grid.session is not None and grid.session.name == "monitor_1"
        other = grid.cards["detector_image"].geometry().center()
        at = viewport.mapFromGlobal(grid.mapToGlobal(other))
        mouse_move(qtbot, viewport, at)
        qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=at)
    settled(qtbot, panel)

    assert cells_of(panel) == {
        "monitor_1": before["detector_image"],
        "detector_image": before["monitor_1"],
    }


def qt_drag(target, mime, at, ctrl=False, drop=True):
    """Send a Qt drag of *mime* over *target* to *at* and return its last event."""
    data = QMimeData()
    data.setData(MIME, mime)
    actions = Qt.DropAction.MoveAction | Qt.DropAction.CopyAction
    keys = Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier(0)
    args = (actions, data, Qt.MouseButton.LeftButton, keys)
    events = [QDragEnterEvent(at, *args), QDragMoveEvent(at, *args)]
    if drop:
        events.append(QDropEvent(QPointF(at), *args))
    for event in events:
        QApplication.sendEvent(target, event)
    return event


def leave(target):
    """End a drag that did not drop.

    Qt keeps the target of a drag until the drag leaves it, and a drag in a
    later test would reach the target after its test deleted it.
    """
    QApplication.sendEvent(target, QDragLeaveEvent())


@pytest.fixture
def third_view_open(views, fake_daemon, qtbot):
    one, _two, three = views
    deliver(qtbot, fake_daemon, one, histogram(), cube(), histogram(name="monitor_2"))
    tab_widget(three).setCurrentIndex(2)
    qtbot.waitUntil(lambda: three.grid.width() > 500)
    return views


def test_a_plot_dropped_on_another_view_leaves_only_the_view_it_came_from(
    third_view_open,
):
    one, _two, three = third_view_open
    one.hub.show_in("monitor_1", 2, True)

    landing = qt_drag(three.grid, plot_mime(one.grid, "monitor_1"), QPoint(450, 300))

    assert landing.dropAction() == Qt.DropAction.MoveAction
    assert one.hub.where("monitor_1") == [2, 3]
    assert "monitor_1" not in one.views and "monitor_1" in three.views


def test_a_plot_dropped_with_ctrl_is_copied_before_the_plot_under_it(third_view_open):
    one, _two, three = third_view_open
    one.hub.move("monitor_1", 3)

    mime = plot_mime(one.grid, "monitor_2")
    landing = qt_drag(three.grid, mime, QPoint(10, 10), ctrl=True)

    assert landing.dropAction() == Qt.DropAction.CopyAction
    assert one.hub.where("monitor_2") == [1, 3]
    assert cells_of(three) == {"monitor_2": (0, 0, 6, 1), "monitor_1": (6, 0, 6, 1)}
    assert three.spans == [("monitor_2", 6, 1), ("monitor_1", 6, 1)]


def test_a_plot_dropped_with_ctrl_on_its_own_grid_only_moves_there(third_view_open):
    one, _two, three = third_view_open
    one.hub.move("monitor_1", 3)
    one.hub.move("monitor_2", 3)
    one.hub.show_in("monitor_2", 2, True)
    assert cells_of(three)["monitor_2"] == (0, 1, 12, 1)

    mime = plot_mime(three.grid, "monitor_2")
    qt_drag(three.grid, mime, QPoint(10, 10), ctrl=True)

    assert one.hub.where("monitor_2") == [2, 3]
    assert cells_of(three) == {"monitor_2": (0, 0, 12, 1), "monitor_1": (0, 1, 12, 1)}


def test_move_to_takes_a_plot_only_out_of_the_view_of_its_menu(third_view_open):
    one, _two, three = third_view_open
    one.hub.move("monitor_1", 3)
    one.hub.show_in("monitor_1", 2, True)

    move_to = menu_action(three.views["monitor_1"].plot_menu, "Move to").menu()
    assert [a.text() for a in move_to.actions()] == ["Live 1", "Live 2"]
    move_to.actions()[0].trigger()

    assert one.hub.where("monitor_1") == [1, 2]


def test_drops_from_other_programs_are_refused(views):
    foreign = json.dumps([-1, 0, 1, "x"]).encode()
    event = qt_drag(views[1].grid, foreign, QPoint(5, 5), drop=False)
    assert not event.isAccepted()
    leave(views[1].grid)


def tab_widget(panel):
    tabs = panel.parentWidget()
    while not isinstance(tabs, QTabWidget):
        tabs = tabs.parentWidget()
    return tabs


def test_a_dragged_plot_resting_on_a_tab_opens_it(views, qtbot):
    tabs = tab_widget(views[0])
    bar = tabs.tabBar()
    mime = plot_mime(views[0].grid, "monitor_1")
    qt_drag(bar, mime, bar.tabRect(2).center(), drop=False)

    qtbot.waitUntil(lambda: tabs.currentIndex() == 2, timeout=2000)
    leave(bar)


class OwnTabs(QWidget):
    """A container with a tab bar of its own, like a docking window has."""

    def __init__(self):
        super().__init__()
        self.bar = QTabBar(self)
        for title in ("Live 1", "Live 2", "Live 3"):
            self.bar.addTab(title)

    def plot_switch_bars(self):
        return [self.bar]


def test_a_container_without_a_tab_widget_can_open_its_tabs_for_a_plot(qtbot):
    page = OwnTabs()
    qtbot.addWidget(page)
    grid = LiveGrid(1)
    grid.setParent(page)
    page.show()
    qtbot.waitExposed(page)
    mime = plot_mime(grid, "monitor_1")
    qt_drag(page.bar, mime, page.bar.tabRect(2).center(), drop=False)

    qtbot.waitUntil(lambda: page.bar.currentIndex() == 2, timeout=2000)
    leave(page.bar)


def test_an_empty_picture_of_a_card_that_has_no_size_yet_paints_nothing(qtbot):
    target = QPixmap(50, 50)
    painter = QPainter(target)
    paint_picture(painter, QPixmap(), QRectF(0, 0, 40, 40))

    assert painter.end()


def test_a_slide_running_when_its_window_is_collected_raises_nothing(qtbot):
    window = QWidget()
    window.cycle = window  # the main window is only freed by the cyclic GC
    grid = LiveGrid(1)
    grid.setParent(window)
    grid.shown["monitor_1"] = QRect(0, 0, 10, 10)
    grid._glide("monitor_1", QRect(100, 100, 10, 10))
    window.deleteLater()
    del window, grid
    gc.collect()
    # processEvents runs the animation but leaves the deferred delete waiting.
    end = time.monotonic() + 0.1
    while time.monotonic() < end:
        QApplication.processEvents()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("end", ["drop", "cancel"])
def test_a_drag_that_ends_in_a_hidden_tab_takes_its_layer_down(
    end, views, fake_daemon, qtbot
):
    one = views[0]
    deliver(qtbot, fake_daemon, one, histogram(), cube())
    tabs = tab_widget(one)
    viewport = one.canvases["monitor_1"].viewport()
    start = title_point(one, "monitor_1")
    with mouse_held(qtbot, viewport, start, start - QPoint(200, 0)):
        tabs.setCurrentIndex(1)  # the drag rests on the tab of Live 2
        getattr(one.grid, end)()
        qtbot.wait(600)
        tabs.setCurrentIndex(0)

    qtbot.waitUntil(one.grid.layer.isHidden, timeout=2000)
    deliver(qtbot, fake_daemon, one, histogram(data=np.full(3, 17.0)))
    qtbot.waitUntil(lambda: list(one.views["monitor_1"].curve.line.yData) == [17.0] * 3)


def test_plots_of_a_closed_window_show_in_the_first_view_at_once(
    views, fake_daemon, qtbot
):
    one = views[0]
    deliver(qtbot, fake_daemon, one, histogram(), cube())
    aux = QMainWindow()
    aux.mainwindow, aux.log = one.mainwindow, one.log
    four = LiveViewPanel(aux, one.client, {"index": 4})
    aux.setCentralWidget(four)
    aux.show()
    one.hub.move("monitor_1", 4, 1)
    assert "monitor_1" in four.views and "monitor_1" not in one.views

    aux.close()
    aux.deleteLater()  # NICOS deletes an auxiliary window with its panels
    qtbot.waitUntil(lambda: one.hub.indices() == [1, 2, 3])

    assert one.hub.where("monitor_1") == [1]
    qtbot.waitUntil(lambda: "monitor_1" in one.views, timeout=1000)


def test_a_new_roi_plot_shows_in_the_view_of_its_detector(views, fake_daemon, qtbot):
    one, two, _three = views
    deliver(qtbot, fake_daemon, one, histogram(), cube())
    one.hub.move("detector_image", 2, 1)  # the user put the detector in Live 2
    deliver(qtbot, fake_daemon, one, histogram(name="detector_image.roi0"))

    assert one.hub.where("detector_image.roi0") == [2]
    qtbot.waitUntil(lambda: "detector_image.roi0" in two.views, timeout=1000)
    assert "detector_image.roi0" not in one.views


OUTPUTS = single_panel_guiconfig_string(PANEL).replace(
    f"main_window = panel({PANEL!r})",
    "main_window = tabbed(\n"
    f"    ('Live 1', panel({PANEL!r}, index=1)),\n"
    f"    ('Live 2', panel({PANEL!r}, index=2, outputs=['monitor_*'])),\n"
    ")",
)


def test_the_outputs_option_chooses_the_view_until_the_user_moves(
    gui_window_factory, fake_daemon, qtbot
):
    window = gui_window_factory(guiconfig_string=OUTPUTS)
    one, two = sorted(window.findChildren(LiveViewPanel), key=lambda p: p.index)
    window.show()
    deliver(qtbot, fake_daemon, one, histogram(), cube())

    assert one.hub.where("monitor_1") == [2] and one.hub.where("detector_image") == [1]
    one.hub.move("monitor_1", 1)
    assert one.hub.where("monitor_1") == [1]

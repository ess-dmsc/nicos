"""Tests for the live view panel fed by the fake daemon.

The tests for FrameView itself are in widgets/test_frame_plot.py.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace

import numpy as np
import pyqtgraph as pg
import pytest

from nicos.clients.gui.utils import SettingGroup
from nicos.core import LIVE
from nicos.guisupport.qt import QApplication, QMenu, QPoint, Qt
from nicos.utils import byteBuffer
from nicos_ess.gui import live_hub
from nicos_ess.gui.panels import liveview
from nicos_ess.gui.panels.liveview import MIN_CELL, LiveViewPanel, grid_columns
from nicos_ess.utilities import live_frame
from nicos_ess.utilities.live_frame import Coord, Frame, encode
from test.nicos_ess.gui.doubles.fake_transport import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    menu_action,
    mouse_drag,
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


def set_shape(qtbot, panel, width, height, columns):
    panel.window().resize(width, height)
    qtbot.waitUntil(lambda: panel._cols == columns)


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    window = gui_window_factory(guiconfig_string=single_panel_guiconfig_string(PANEL))
    panel = get_panel_by_class(window, PANEL)
    panel.split_states.clear()
    window.show()  # Plots are only drawn while the panel is on screen.
    qtbot.waitUntil(panel.isVisible)
    return panel


@pytest.mark.parametrize(
    "count, width, height, columns",
    [(1, 800, 600, 1), (4, 800, 600, 2), (6, 600, 1600, 1), (12, 1600, 900, 4)],
)
def test_the_grid_follows_the_panel(count, width, height, columns):
    assert grid_columns(count, width, height) == columns


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
    def send(device, frame):
        datadescs, data, labels = encode([frame])
        params = dict(uid=0, time=0, det=device, tag=LIVE, datadescs=datadescs)
        panel.hub.on_livedata(params, [bytes(byteBuffer(b)) for b in [*data, *labels]])

    # esslivedata stamps its frames with data times ahead of the clock here.
    send("livedata_collector", histogram(meta=dict(time=time.time() + 60)))
    series = panel.hub.series["monitor_1"]
    send("jbi_detector", histogram(data=np.ones(3)))

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


def test_plots_go_next_to_their_own_and_where_the_user_places_them(
    panel, fake_daemon, qtbot
):
    names = ["ngem", "ngem.roi4", "multiblade", "ngem.roi0", "he3"]
    deliver(qtbot, fake_daemon, panel, *(histogram(name=n) for n in names))
    assert panel.shown() == ["he3", "multiblade", "ngem", "ngem.roi0", "ngem.roi4"]

    menu = QMenu()
    panel._layout_entries(menu, panel.views["ngem.roi4"])
    place = next(a.menu() for a in menu.actions() if a.text() == "Place")
    next(a for a in place.actions() if a.text() == "After he3").trigger()
    assert panel.shown() == ["he3", "ngem.roi4", "multiblade", "ngem", "ngem.roi0"]
    panel.place("ngem", None)
    assert panel.shown()[:2] == ["ngem", "he3"]

    settings = Settings()
    panel.saveSettings(settings)
    assert json.loads(settings["liveview"])["order"] == panel.shown()


def test_a_time_series_keeps_its_own_samples(panel, fake_daemon, qtbot):
    times = (np.array([0, 1, 2]) + time.time() - 10) * 10**9
    coords = {"time": Coord(("time",), times, "datetime64[ns]")}
    samples = Frame(np.array([1.0, 2.0, 3.0]), ("time",), name="temp", coords=coords)

    deliver(qtbot, fake_daemon, panel, samples)
    qtbot.waitUntil(lambda: panel.views["temp"].curve is not None)
    qtbot.wait(300)  # Let the plot redraw a few times.

    assert panel.hub.series["temp"].arrays()[1].tolist() == [1, 2, 3]


def test_dragged_sizes_come_back_until_made_equal(panel, fake_daemon, qtbot):
    deliver(qtbot, fake_daemon, panel, histogram(), cube())
    set_shape(qtbot, panel, 1600, 500, 2)
    assert not panel.grid.widget(0).opaqueResize()  # Sizes change on the drop.
    panel.grid.widget(0).setSizes([700, 250])
    first, second = (panel.canvases[n] for n in panel.shown())
    qtbot.waitUntil(lambda: first.width() > 2 * second.width())
    dragged = panel.grid.widget(0).sizes()

    def rearrange():
        grid, alone = panel.grid, panel.canvases["monitor_1"]
        panel.views["monitor_1"].solo_requested.emit()
        qtbot.waitUntil(lambda: alone.width() > panel.grid.width() - 10)
        assert panel.grid is grid
        panel.views["monitor_1"].solo_requested.emit()
        qtbot.waitUntil(lambda: all(panel.grid.widget(0).sizes()))
        return panel.grid.widget(0).sizes()

    first, second = rearrange()
    assert first / second == pytest.approx(dragged[0] / dragged[1], rel=0.05)
    menu = QMenu()
    panel._layout_entries(menu)
    next(a for a in menu.actions() if a.text() == "Equal plot sizes").trigger()
    first, second = rearrange()
    assert first == pytest.approx(second, abs=2)
    settings = Settings()
    panel.saveSettings(settings)  # Only the arrangement on screen is saved.
    assert list(json.loads(settings["liveview"])["splits"]) == [panel._key]
    panel.grid.widget(0).setSizes([2000, 1])
    qtbot.waitUntil(lambda: min(panel.grid.widget(0).sizes()) >= MIN_CELL[0])


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

    assert panel._saved["splits"][panel._key]["cols"] == [panel.grid.widget(0).sizes()]
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
    for view in found:
        view.split_states.clear()
    window.show()
    qtbot.waitUntil(found[0].isVisible)
    return found


def test_several_views_share_one_hub(views):
    one, two, three = views
    assert one.hub is two.hub is three.hub
    assert two.panelName == "Live view 2"
    assert "No live data yet" in two.grid.text()
    assert not two.tool_bar.isEnabled()
    menu = QMenu()
    two._layout_entries(menu)
    assert menu.isEmpty()


def test_new_outputs_go_to_the_first_view(views, fake_daemon, qtbot):
    one, two, _three = views

    deliver(qtbot, fake_daemon, one, histogram(), cube())

    assert sorted(one.views) == ["detector_image", "monitor_1"]
    assert one.tool_bar.isEnabled() and two.views == {}
    assert "Nothing placed in Live 2" in two.grid.text()


def test_an_output_placed_in_a_missing_view_goes_to_the_first(views):
    hub = views[0].hub
    hub.placement["x"] = [7]  # This GUI has no view 7.
    assert hub.where("x") == [1]


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

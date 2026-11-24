"""Tests for the ESS history viewer panel on pyqtgraph."""

import json
import time

import numpy as np
import pytest

from nicos.guisupport.qt import (
    QApplication,
    QDialog,
    QEvent,
    QMenu,
    QPointF,
    QSettings,
    sip,
)
from nicos_ess.gui.history_series import HistorySeries
from nicos_ess.gui.panels import history_pyqt
from nicos_ess.gui.panels.history import NewViewDialog
from nicos_ess.gui.panels.history_pyqt import HistoryPanel
from nicos_ess.gui.widgets.pyqtgraph import export
from test.nicos_ess.gui.helpers import (
    answer_dialogs,
    drawn_pixels,
    get_panel_by_class,
    menu_action,
    single_panel_guiconfig_string,
)


def _info(devices, **overrides):
    """Return what the new-view dialog gives for the last hour of *devices*."""
    info = dict(devices=devices, name="", interval="", slidingWindow=True)
    info.update(simpleTime=True, simpleTimeSpec="1h")
    info.update(customY=False, customYFrom="", customYTo="")
    info.update(frombox=False, tobox=False, fromdate=0, todate=0)
    return info | overrides


def _panel(gui_window_factory):
    window = gui_window_factory(
        guiconfig_string=single_panel_guiconfig_string(HistoryPanel)
    )
    return get_panel_by_class(window, HistoryPanel)


@pytest.fixture
def now():
    return time.time()


@pytest.fixture
def history(gui_window_factory, fake_daemon, now):
    times = [now - 3540 + 10 * index for index in range(348)]
    fake_daemon.set_history(
        "ts1/value", [(t, float(i % 40)) for i, t in enumerate(times)]
    )
    fake_daemon.set_history(
        "ts2/value", [(t, [float(i), -i]) for i, t in enumerate(times)]
    )
    fake_daemon.set_cache("ts1/value", 1.0)
    fake_daemon.set_cache("ts1/unit", "mm")
    return _panel(gui_window_factory)


@pytest.fixture
def motor_history(gui_window_factory, fake_daemon, now):
    fake_daemon.set_history("mot/value", [(now - 1200, 1.0), (now - 600, 3.0)])
    fake_daemon.set_cache("mot/value", 3.0)
    return _panel(gui_window_factory)


@pytest.fixture
def two_units(history, fake_daemon):
    fake_daemon.set_cache("ts2/unit", "K")
    return history._createViewFromDialog(_info("ts1, ts2, ts1*2")).plot


def frame(plot, name):
    """Return the frame that is drawn for the signal *name*."""
    view = plot.frames
    return view.frame if view.curve_name == name else view.overlay_frames[name]


def on_screen(plot, x, y):
    """Return the pixel of *plot* where the point (x, y) of the left axis is."""
    scene = plot.view_box.mapViewToScene(QPointF(x, y))
    viewport = plot.canvas.viewport()
    return viewport.mapTo(plot, plot.canvas.mapFromScene(scene))


def test_view_plots_history_expressions_and_live_updates(
    history, fake_daemon, qtbot, now
):
    history._createViewFromDialog(_info("ts1, ts1*2, ts2"))
    plot = history.currentPlot

    assert plot.frames.curve_name == "ts1"
    assert list(plot.frames.overlay_frames) == ["ts1*2", "ts2[0]", "ts2[1]"]
    doubled = frame(plot, "ts1*2").data
    np.testing.assert_allclose(doubled, 2 * frame(plot, "ts1").data)
    np.testing.assert_allclose(frame(plot, "ts2[1]").data, -frame(plot, "ts2[0]").data)
    lines = {"ts1": plot.frames.curve.line}
    lines |= {name: curve.line for name, curve in plot.frames.overlay_curves.items()}
    heights = {}
    for name, line in lines.items():
        _xs, ys = drawn_pixels(plot, line)
        assert len(ys) > 100, f"{name} is not drawn"
        heights[name] = ys.mean()
    # The pixel rows count from the top, so a curve of larger values has
    # smaller rows.
    assert heights["ts1*2"] < heights["ts1"] - 10
    assert heights["ts2[1]"] > heights["ts2[0]"] + 10

    fake_daemon.push_cache("ts1/value", 17.0, timestamp=now + 30)
    qtbot.waitUntil(lambda: frame(plot, "ts1*2").data[-1] == 34.0, timeout=2500)


def test_columns_named_by_the_format_keep_their_names(history, fake_daemon, qtbot, now):
    """The same column can hold different ROIs over time, but a name cannot."""
    fake_daemon.set_history(
        "ngem/value",
        [(now - 600, [100, 10]), (now - 400, [200, 20, 30]), (now - 200, [300, 40])],
    )
    formats = ["%d, roi0 = %d", "%d, roi0 = %d, roi3 = %d", "%d, roi3 = %d"]
    times = [now - 700, now - 400, now - 200]
    fake_daemon.set_history("ngem/fmtstr", zip(times, formats, strict=True))
    history._createViewFromDialog(_info("ngem"))
    plot = history.currentPlot

    assert list(plot.frames.overlay_frames) == ["ngem.roi0", "ngem.roi3"]
    assert list(frame(plot, "ngem.roi0").data[:2]) == [10, 20]
    assert list(frame(plot, "ngem.roi3").data[:2]) == [30, 40]

    fake_daemon.push_cache("ngem/fmtstr", "%d, roi3 = %d, roi5 = %d", timestamp=now + 5)
    fake_daemon.push_cache("ngem/value", [400, 50, 60], timestamp=now + 5)
    qtbot.waitUntil(lambda: "ngem.roi5" in plot.frames.overlay_frames, timeout=2500)
    assert frame(plot, "ngem.roi3").data[-1] == 50
    assert frame(plot, "ngem.roi5").data[-1] == 60


def test_a_second_unit_goes_to_the_right_axis_and_axes_show_units(two_units):
    plot = two_units
    places = [plot.place(name) for name in ("ts1", "ts2[0]", "ts2[1]", "ts1*2")]
    assert places == ["left", "right", "right", "left"]
    left, right = (plot.frames.plot.getAxis(side) for side in ("left", "right"))
    assert (left.labelText, right.labelText) == ("mm", "K")


def test_a_curve_moved_to_an_axis_of_another_unit_is_hidden_and_counted(two_units):
    plot = two_units
    plot.set_place("ts2[0]", "left")

    assert plot.place("ts2[0]") == "hidden"
    title = plot.frames.title_item
    assert "1 hidden" in title.text
    assert "ts2[0] in another unit" in title.toolTip().split("\n")


def test_the_first_curve_on_the_left_sets_the_unit_of_the_left_axis(two_units):
    plot = two_units
    left, right = (plot.frames.plot.getAxis(side) for side in ("left", "right"))
    plot.set_place("ts1", "right")

    assert (left.labelText, right.labelText) == ("K", "mm")
    assert plot.place("ts1*2") == "right"


def test_moving_a_curve_to_the_right_hides_the_curves_there_in_another_unit(
    two_units,
):
    plot = two_units
    plot.set_place("ts1", "right")
    plot.set_place("ts2[0]", "right")

    assert (plot.place("ts1"), plot.place("ts2[1]")) == ("hidden", "left")


def test_a_plot_with_every_curve_hidden_shows_the_empty_note(two_units):
    plot = two_units
    for name in ("ts1", "ts2[0]", "ts2[1]", "ts1*2"):
        plot.set_place(name, "hidden")

    assert plot.frames.empty_note.isVisible()
    assert plot.frames.frame.data.size == 0


def zoom_in(plot):
    (x0, _x1), _ = plot.view_box.viewRange()
    plot.view_box.setXRange(x0, x0 + 100, padding=0)


def test_reset_zoom_shows_the_whole_time_range_again(history):
    history._createViewFromDialog(_info("ts1", simpleTimeSpec="10m"))
    plot = history.currentPlot
    QApplication.processEvents()
    (x0, x1), _ = plot.view_box.viewRange()
    assert x1 - x0 == pytest.approx(600, rel=0.05)

    zoom_in(plot)
    assert plot.frames.zoomed()
    history.actionUnzoom.trigger()
    QApplication.processEvents()
    (x0, x1), _ = plot.view_box.viewRange()
    assert not plot.frames.zoomed() and x1 - x0 == pytest.approx(600, rel=0.05)


def test_a_reconnect_after_a_long_break_rebuilds_the_views(history, monkeypatch):
    history._createViewFromDialog(_info("ts1", simpleTimeSpec="10m"))
    old = history.currentPlot
    QApplication.processEvents()
    zoom_in(old)

    history.on_client_disconnected()
    monkeypatch.setattr(history_pyqt, "currenttime", lambda: time.time() + 10)
    history.on_client_connected()

    plot = history.currentPlot
    assert plot is not old and sip.isdeleted(old)
    assert [view.name for view in history.views] == ["ts1 (10m)"]
    assert not plot.frames.zoomed()
    zoom_in(plot)
    history.actionUnzoom.trigger()
    assert not plot.frames.zoomed()


def test_a_reconnect_keeps_the_rows_the_current_view_and_the_live_values(
    history, fake_daemon, qtbot, monkeypatch, now
):
    history._createViewFromDialog(_info("ts1"))
    history._createViewFromDialog(_info("ts2"))
    history.openView(history.views[0])

    history.on_client_disconnected()
    monkeypatch.setattr(history_pyqt, "currenttime", lambda: time.time() + 10)
    history.on_client_connected()

    rows = [history.viewList.item(row).text() for row in range(2)]
    assert history.viewList.count() == 2 and rows == ["ts1 (1h)", "ts2 (1h)"]
    assert history.currentPlot.view.name == "ts1 (1h)"
    views = {view.name: view for view in history.views}
    fake_daemon.push_cache("ts1/value", 17.0, timestamp=now + 30)
    fake_daemon.push_cache("ts2/value", [5.0, -5.0], timestamp=now + 30)
    qtbot.waitUntil(
        lambda: (
            views["ts1 (1h)"].series["ts1"].y[-1] == 17.0
            and views["ts2 (1h)"].series["ts2[0]"].y[-1] == 5.0
        ),
        timeout=2500,
    )


def test_a_custom_y_range_sets_the_y_axis(history):
    history._createViewFromDialog(
        _info("ts1", customY=True, customYFrom="-5", customYTo="50")
    )
    QApplication.processEvents()
    assert history.currentPlot.view_box.viewRange()[1] == pytest.approx((-5, 50))


def test_a_view_from_the_devices_panel_is_named_after_its_devices(history):
    history.newView("ts1")
    assert history.viewStack[-1].name == "ts1 (1h)"


def test_the_views_survive_a_settings_round_trip(history):
    history._createViewFromDialog(
        _info("ts1", name="kept", customY=True, customYFrom="-5", customYTo="50")
    )
    history._createViewFromDialog(_info("ts1, ts2"))

    settings = QSettings()
    settings.beginGroup("history-roundtrip-test")
    try:
        history.saveSettings(settings)
        history.loadSettings(settings)
    finally:
        settings.remove("")
        settings.endGroup()
    saved = {view.name: json.loads(json.dumps(view.dlginfo)) for view in history.views}
    assert dict(history.last_views) == saved
    assert saved["kept (1h)"]["customYFrom"] == "-5"


def test_the_tool_bar_follows_the_current_view(history):
    first = history._createViewFromDialog(_info("ts1", name="first"))
    second = history._createViewFromDialog(_info("ts2", name="second"))
    assert history.currentPlot is second.plot
    history.openView(first)
    assert history.currentPlot is first.plot

    history.actionCloseView.trigger()
    assert history.currentPlot is (plot := second.plot)
    history.actionDeleteView.trigger()
    # Deleting the shown view opens the next view in the list.
    assert history.currentPlot is first.plot
    history.actionDeleteView.trigger()
    assert history.views == [] and not history.actionSavePlot.isEnabled()
    # The plot is deleted right away. If Python freed the plot items first, Qt
    # could still call them.
    assert history.currentPlot is None and sip.isdeleted(plot)


def test_the_plot_is_saved_as_an_image(history, tmp_path, monkeypatch):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    ask = lambda *args: (str(tmp_path / "plot.png"), args[-1])  # noqa: E731
    monkeypatch.setattr(export.QFileDialog, "getSaveFileName", ask)
    history.currentPlot.savePlot()
    assert (tmp_path / "plot.png").stat().st_size > 0


def test_all_curves_are_exported_into_one_table(history, tmp_path, monkeypatch):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    listed = []

    def fill(dialog):
        combo = dialog.curveCombo
        listed.extend(combo.itemText(index) for index in range(combo.count()))
        combo.setCurrentText("all (in one file, multiple data columns)")
        dialog.selectFile(str(tmp_path / "data"))

    answer_dialogs(monkeypatch, fill=fill)
    history.actionSaveData.trigger()

    assert listed == [
        "all (in separate files)",
        "all (in one file, multiple data columns)",
        "ts1 (mm)",
        "ts1*2 (mm)",
    ]
    table = np.loadtxt(tmp_path / "data.dat")
    np.testing.assert_allclose(table[:, 2], 2 * table[:, 1])


def test_only_the_shown_view_is_redrawn(history, fake_daemon, qtbot, monkeypatch, now):
    hidden = history._createViewFromDialog(_info("ts1", name="hidden"))
    shown = history._createViewFromDialog(_info("ts1", name="shown"))
    redrawn = []
    monkeypatch.setattr(hidden.plot, "refresh", lambda: redrawn.append(hidden))

    fake_daemon.push_cache("ts1/value", 17.0, timestamp=now + 30)
    qtbot.waitUntil(lambda: frame(shown.plot, "ts1").data[-1] == 17.0, timeout=2500)
    assert hidden.series["ts1"].y[-1] == 17.0 and redrawn == []
    monkeypatch.undo()
    history.openView(hidden)
    assert frame(hidden.plot, "ts1").data[-1] == 17.0


def test_axes_and_hidden_curves_belong_to_the_view(history, monkeypatch):
    view = history._createViewFromDialog(_info("ts1, ts1*2"))
    history.currentPlot.set_place("ts1", "right")
    history.currentPlot.set_place("ts1*2", "hidden")
    expected = {"ts1": "right", "ts1*2": "hidden"}
    assert view.dlginfo["axes"] == expected
    answer_dialogs(monkeypatch)

    history.actionEditView.trigger()

    edited = history.viewStack[-1]
    assert edited is not view and edited.plot.places == expected
    assert edited.plot.place("ts1*2") == "hidden"


def test_a_preset_saved_while_editing_keeps_its_axes(history, monkeypatch):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    history.currentPlot.set_place("ts1", "right")

    def fill(dialog):
        dialog.namebox.setText("axes preset")
        dialog.savePreset.setChecked(True)

    answer_dialogs(monkeypatch, fill=fill)
    history.actionEditView.trigger()
    try:
        history.currentPlot.set_place("ts1", "left")
        assert history.presetdict["axes preset"]["axes"] == {"ts1": "right"}
    finally:
        history.presetdict.pop("axes preset", None)


def test_the_tool_bar_leaves_the_zoom_actions_to_the_plot_menu(history):
    assert history.actionScaleX not in history.bar.actions()
    history._createViewFromDialog(_info("ts1, ts1*2"))
    assert history.getMenus() == []


def test_the_plot_menu_offers_curves_and_log_scale(history):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    frames = history.currentPlot.frames
    curves = menu_action(frames.plot_menu, "Curves").menu()

    assert "Hide this plot" not in [a.text() for a in frames.plot_menu.menu.actions()]
    assert [a.text() for a in curves.actions()[:3]] == ["Legend", "Points", "Lines"]
    assert frames.plot.buttonsHidden
    menu_action(frames.plot_menu, "Log scale").trigger()
    assert frames.log


def test_a_curve_moves_to_the_right_axis_through_the_plot_menu(history):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    plot = history.currentPlot
    curves = menu_action(plot.frames.plot_menu, "Curves").menu()
    [curve_menu] = [
        a.menu() for a in curves.actions() if a.menu() and a.text() == "ts1*2 (mm)"
    ]
    [right] = [a for a in curve_menu.actions() if a.text() == "Right axis"]

    assert right.actionGroup().isExclusive()
    right.trigger()
    assert plot.place("ts1*2") == "right"


def test_refilling_the_plot_menu_drops_the_old_curve_menus(history):
    history._createViewFromDialog(_info("ts1, ts1*2"))
    plot_menu = history.currentPlot.frames.plot_menu
    plot_menu.refill()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    before = len(plot_menu.menu.findChildren(QMenu))

    plot_menu.refill()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert len(plot_menu.menu.findChildren(QMenu)) == before


def test_the_readout_shows_values_and_follows_new_data(history, fake_daemon, qtbot):
    # The window must be large enough for the plot to show its legend.
    history.window().resize(1200, 900)
    history._createViewFromDialog(_info("ts1, ts1*2", interval="0.001"))
    plot = history.currentPlot
    legend, box = plot.frames.legend, plot.view_box
    # After the layout the legend is below the plot, so it covers no curve.
    qtbot.waitUntil(
        lambda: (
            legend.isVisible()
            and legend.sceneBoundingRect().top() >= box.sceneBoundingRect().bottom()
        )
    )
    series = next(iter(plot.view.series.values()))
    # Just before the next point the previous value is still held.
    x, y = series.x[50] * 0.1 + series.x[51] * 0.9, series.y[50]
    text = f"ts1 {y:.0f} mm · ts1*2 {2 * y:.0f} mm"
    qtbot.waitUntil(
        lambda: (
            plot.frames.hover_at(box.mapViewToScene(QPointF(x, y)))
            and plot.frames.hover.endswith(text)
        )
    )

    end = plot.frames.curve.line.xData[-1]
    plot.frames.hover_at(plot.view_box.mapViewToScene(QPointF(end - 1, y)))
    fake_daemon.push_cache("ts1/value", 42.0, timestamp=end - 2)
    qtbot.waitUntil(lambda: "ts1 42 mm ·" in plot.frames.hover, timeout=3000)


def test_an_old_value_is_held_up_to_now_and_a_new_one_steps(
    motor_history, fake_daemon, qtbot, now
):
    # In a one minute window the held line grows by more than a pixel per second.
    motor_history._createViewFromDialog(
        _info("mot", interval="0.001", simpleTimeSpec="1m")
    )
    plot = motor_history.currentPlot
    item = plot.frames.curve.line
    first_end = item.xData[-1]
    assert first_end >= now and item.yData[-1] == 3.0
    qtbot.waitUntil(lambda: item.xData[-1] >= first_end + 1, timeout=3000)
    series = next(iter(plot.view.series.values()))
    assert series.x[-1] < first_end

    fake_daemon.push_cache("mot/value", 9.0, timestamp=time.time())
    qtbot.waitUntil(lambda: series.y[-1] == 9.0, timeout=3000)
    plot.refresh()
    assert item.opts["stepMode"] == "right"
    assert list(plot.frames.frame.data[:2]) == [3.0, 9.0]


def test_an_archived_view_spans_exactly_its_time_range(motor_history, monkeypatch, now):
    start, end = int(now - 900), int(now - 300)
    motor_history._createViewFromDialog(
        _info("mot", simpleTime=False, frombox=True, fromdate=start)
        | dict(tobox=True, todate=end)
    )
    plot = motor_history.currentPlot

    # The line must not grow up to the current time on a later redraw.
    monkeypatch.setattr(history_pyqt, "currenttime", lambda: now + 60)
    plot.refresh()
    item = plot.frames.curve.line
    assert (item.xData[0], item.xData[-1]) == pytest.approx((start, end), abs=1)
    assert list(item.yData[:2]) == [1.0, 3.0]  # The 1 dates from before the start.


def test_a_value_older_than_the_view_is_held_across_it(gui_window_factory, fake_daemon):
    now = time.time()
    fake_daemon.set_history("mot/value", [(now - 5 * 3600, 4.0)])
    fake_daemon.set_cache("mot/value", 4.0)
    panel = _panel(gui_window_factory)
    view = panel._createViewFromDialog(_info("mot", slidingWindow=False))
    plot = panel.currentPlot
    QApplication.processEvents()

    item = plot.frames.curve.line
    assert item.xData[0] == pytest.approx(view.fromtime, abs=1)
    assert item.xData[-1] == pytest.approx(time.time(), abs=2)
    assert list(item.yData) == [4.0, 4.0]
    xs, ys = drawn_pixels(plot, item)
    start, end = on_screen(plot, view.fromtime, 4.0), on_screen(plot, time.time(), 4.0)
    assert xs.min() <= start.x() + 2 and xs.max() >= end.x() - 2
    assert np.abs(ys - start.y()).max() <= 3


def test_a_key_without_history_starts_now_at_its_cache_value_and_is_noted(
    gui_window_factory, fake_daemon, record_modal_message_boxes
):
    """The curve starts now instead of at the start of the view.

    There is no message box for each key without history.
    """
    fake_daemon.set_cache("mot/value", 7.0)
    before = time.time()
    view = _panel(gui_window_factory)._createViewFromDialog(_info("mot, nothing"))

    series = view.series["mot"]
    assert series.x[0] >= before and list(series.y) == [7.0]
    assert view.series["nothing"].n == 0
    assert record_modal_message_boxes == []
    assert "no history of mot, nothing" in view.plot.frames.title_item.text


def test_a_column_listed_twice_gets_one_curve(history):
    view = history._createViewFromDialog(_info("ts2[0], ts2"))
    curves = menu_action(history.currentPlot.frames.plot_menu, "Curves").menu()

    assert [a.text() for a in curves.actions() if a.menu()] == ["ts2[0]", "ts2[1]"]
    assert [series.descr for series in view.series.values()] == ["ts2[0]", "ts2[1]"]


def test_a_parameter_named_like_a_column_gets_its_own_curve(
    history, fake_daemon, qtbot, now
):
    fake_daemon.set_history("ngem/value", [(now - 600, [100, 10])])
    fake_daemon.set_history("ngem/fmtstr", [(now - 700, "%d, roi0 = %d")])
    fake_daemon.set_history("ngem/roi0", [(now - 600, 5.0)])
    history._createViewFromDialog(_info("ngem, ngem.roi0"))
    plot = history.currentPlot
    assert list(plot.frames.overlay_frames) == ["ngem.roi0", "ngem.roi0 (ngem/roi0)"]

    fake_daemon.push_cache("ngem/roi0", 7.0, timestamp=now + 5)
    qtbot.waitUntil(
        lambda: frame(plot, "ngem.roi0 (ngem/roi0)").data[-1] == 7.0, timeout=2500
    )
    assert frame(plot, "ngem.roi0").data[-1] == 10


def test_a_long_time_span_is_fetched_in_one_request_per_key(history, fake_daemon):
    fake_daemon.command_log.clear()
    history._createViewFromDialog(_info("ts2", simpleTimeSpec="1000d"))

    requests = [
        args for command, args in fake_daemon.command_log if command == "gethistory"
    ]
    assert [args[0] for args in requests] == ["ts2/value", "ts2/fmtstr"]
    (_, start, end, interval), (*_, format_interval) = requests
    # A series keeps at most maxsize points, but the columns need every format.
    assert (float(end) - float(start)) / interval <= HistorySeries.maxsize
    assert format_interval == 0


@pytest.mark.parametrize(
    "low, high, accepted",
    [
        ("0", "inf", False),
        ("nan", "nan", False),
        ("x", "1", False),
        ("-1e308", "1e308", True),
    ],
)
def test_the_view_dialog_takes_only_finite_y_limits(
    history,
    record_modal_message_boxes,
    allow_warning_message_boxes,
    low,
    high,
    accepted,
):
    dialog = NewViewDialog(history, client=history.client)
    dialog.devices.setText("ts1")
    dialog.customY.setChecked(True)
    dialog.customYFrom.setText(low)
    dialog.customYTo.setText(high)

    dialog.accept()

    assert (dialog.result() == QDialog.DialogCode.Accepted) == accepted
    assert [call.kind for call in record_modal_message_boxes] == ["warning"] * (
        not accepted
    )


def test_a_preset_with_y_limits_that_are_not_finite_autoscales(history):
    info = _info(
        "ts1", name="no limits", customY=True, customYFrom="0", customYTo="inf"
    )
    history._add_preset("no limits", info)
    try:
        [launch] = [a for a in history.presetmenu.actions() if a.text() == "no limits"]
        launch.trigger()
    finally:
        history.presetdict.pop("no limits", None)

    assert [view.name for view in history.views] == ["no limits (1h)"]
    assert history.currentPlot.view_box.autoRangeEnabled()[1]
    history.actionDeleteView.trigger()
    assert history.views == [] and history.viewList.count() == 0


def test_a_failed_edit_keeps_the_view(history, monkeypatch):
    view = history._createViewFromDialog(_info("ts1"))
    answer_dialogs(monkeypatch, fill=lambda dialog: dialog.devices.setText(" "))

    history.actionEditView.trigger()

    assert history.views == [view] and history.currentPlot is view.plot


def test_the_view_dialog_refuses_devices_it_cannot_parse(
    history, record_modal_message_boxes, allow_warning_message_boxes
):
    dialog = NewViewDialog(history, client=history.client)
    dialog.devices.setText("ts1+")

    dialog.accept()

    assert dialog.result() == QDialog.DialogCode.Rejected
    assert [call.kind for call in record_modal_message_boxes] == ["warning"]


def test_an_unmapped_reading_ends_the_previous_history_step():
    series = HistorySeries("valve", None, 0, mapping={"open": 0})
    for index in range(series.maxstrings):
        series.add(index, f"other state {index}")
    series.add(50, "open")
    series.add(60, "unseen fault")

    frame = history_pyqt.series_frame(series, start=50, end=70, meta={})
    times = frame.coords["time"].values
    # The plot may show a gap or a distinct state after the fault.
    np.testing.assert_array_equal(frame.data[times == 50], [0])
    assert not np.any((times > 60) & (frame.data == 0))

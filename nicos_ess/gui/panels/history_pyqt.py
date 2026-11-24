"""This history viewer draws its plots with pyqtgraph.

The panel reuses the view list, dialogs, presets and settings of the GR
history panel. The plots are frame views of the series.
"""

from functools import partial
from time import time as currenttime

import numpy as np

from nicos.clients.gui.utils import enumerateWithProgress
from nicos.clients.gui.widgets.plotting import ViewPlot
from nicos.guisupport.qt import (
    QDialog,
    QLabel,
    QListWidgetItem,
    QObject,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
    sip,
)
from nicos.utils import parseKeyExpression
from nicos_ess.gui.history_series import ColumnNames, HistorySeries
from nicos_ess.gui.panels import history
from nicos_ess.gui.panels.history import (
    NewViewDialog,
    custom_y_limits,
    get_time_and_interval,
)
from nicos_ess.gui.widgets.pyqtgraph.export import (
    print_plot,
    save_plot_dialog,
    save_plot_quietly,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import radio_entries
from nicos_ess.utilities.live_frame import curve_frame

PLACES = {"left": "Left axis", "right": "Right axis", "hidden": "Hidden"}


class View(QObject):
    """A View holds the series of one history view and its plot while the plot
    is open.
    """

    def __init__(self, panel, info, name, keys, exprs, descs, times, interval):
        QObject.__init__(self)
        self.name, self.dlginfo, self.client = name, info, panel.client
        self.fromtime, self.totime, self.window, self.yrange = times
        self.interval = interval
        self.meta = panel._getMetainfo(keys)
        self.uniq_keys = set()
        self.series = {}  # This maps the name of a curve to its HistorySeries.
        self._key_series = {}  # This maps a key to a dict from name to series.
        # This maps a multi-value key to (ColumnNames, description).
        self._columns = {}
        self._format_keys = {}  # This maps a format string key to ColumnNames.
        self.listitem = self.plot = None
        self.missing = []  # These keys have no history.
        # The extra 60 seconds also catch values that arrive during the query.
        hist_totime = self.totime or currenttime() + 60
        queried = {}
        items = list(zip(keys, exprs, descs, strict=True))
        if self.fromtime is not None:
            text = "Querying history..."
            items = (
                i for _, i in enumerateWithProgress(items, text, force_display=True)
            )
            # The store thins the points to what a series keeps.
            step = max(interval, (hist_totime - self.fromtime) / HistorySeries.maxsize)
        for key, expr, desc in items:
            self.uniq_keys.add(key)
            history = []
            if self.fromtime is not None:
                if key not in queried:
                    queried[key] = self._query_history(key, hist_totime, step)
                history = queried[key]
            self._load_series(key, expr, desc, history, hist_totime)

    def _history(self, key, totime, interval):
        """Return the history of *key* with at most one point per *interval*."""
        args = (key, str(self.fromtime), str(totime), interval)
        return self.client.ask("gethistory", *args, default=[])

    def _query_history(self, key, totime, interval):
        """Return the history of *key* and note the key as missing if it has
        no history.

        A view that runs up to now shows the current value of such a key.
        """
        history = self._history(key, totime, interval)
        if not history:
            self.missing.append(key.removesuffix("/value"))
            if self.totime is None:
                history = self._current_value(key)
        return history

    def _load_series(self, key, expr, desc, history, totime):
        """Load *history* into the series of *key*.

        A key with several values gets one series per column unless *expr*
        picks from the values.
        """
        first = history[0][1] if history else None
        if expr or not isinstance(first, (list, tuple)):
            self._new_series(key, desc, expr).load(history)
        else:
            self._load_columns(key, desc, history, totime)

    def _load_columns(self, key, desc, history, totime):
        # Take the column names from the format string when possible.
        columns = self._column_names(key, totime, history)
        if columns is None:
            for i in range(len(history[0][1])):
                self._new_series(key, f"{desc}[{i}]", f"x[{i}]").load(history)
            return
        self._columns[key] = (columns, desc)
        history = [(t, columns.named(t, v) or {}) for t, v in history]
        for column in dict.fromkeys(c for _t, value in history for c in value):
            self._column_series(key, column).load(history)

    def _new_series(self, key, name, expr):
        """Return the series of *key* called *name*. A view like "multi[0], multi"
        asks for the same series twice. A name that another key already uses
        gets the key appended."""
        key_series = self._key_series.setdefault(key, {})
        if name in key_series:
            return key_series[name]
        if name in self.series:
            return self._new_series(key, f"{name} ({key})", expr)
        unit, mapping = self.meta[0].get(key), self.meta[1].get(key)
        series = HistorySeries(name, expr, self.interval, self.window, unit, mapping)
        self.series[name] = key_series[name] = series
        return series

    def _column_series(self, key, column):
        desc = self._columns[key][1]
        name = f"{desc}.{column}" if column else desc
        return self._new_series(key, name, f"x[{column!r}]")

    def _column_names(self, key, totime, history):
        """Return the `ColumnNames` of a multi-value key from the history of
        its format string.

        Return None if the format string does not name the columns.
        """
        if not key.endswith("/value"):
            return None
        fmtkey = key.removesuffix("value") + "fmtstr"
        # Every format is needed, because each names the columns from its time on.
        formats = self._history(fmtkey, totime, 0)
        item = None if formats else self.client.getCacheKey(fmtkey)
        if item is not None and item[1] is not None:
            formats = [(self.fromtime, item[1])]
        columns = ColumnNames(formats or ())
        if not any(columns.named(t, v) for t, v in history):
            return None
        self._format_keys[fmtkey] = columns
        self.uniq_keys.add(fmtkey)
        return columns

    def _current_value(self, key):
        # The history store returns the reading that was valid at the start of
        # a query. This is only needed for values older than the retention
        # period or when the store does not have the value. The cache does not
        # tell when the value was set, so the value counts as valid from now.
        item = self.client.getCacheKey(key)
        return [] if item is None or item[1] is None else [(currenttime(), item[1])]

    def newValue(self, vtime, key, op, value):
        if op != "=":
            return
        if key in self._format_keys:
            self._format_keys[key].add(vtime, value)
            return
        if key in self._columns:
            value = self._columns[key][0].named(vtime, value)
            if not value:
                return
            for column in value:
                self._column_series(key, column)
        # The panel redraws the current plot once per second.
        for series in self._key_series[key].values():
            series.add(vtime, value)

    def close_plot(self):
        # Delete the plot right away because Qt could still call the plot items
        # if Python freed them first. The panel takes the plot out of the
        # layout beforehand and never closes a view from inside the plot.
        if self.plot:
            sip.delete(self.plot)
            self.plot = None

    def cleanup(self):
        self.close_plot()


def series_frame(series, start, end, meta):
    """Return the frame of *series* from *start* to *end*.

    A *start* of None means all data. The frame starts with the value that is
    valid at *start*, and the last value is held until *end*.
    """
    keep = np.isfinite(series.x) & np.isfinite(series.y)
    x, y = series.x[keep], series.y[keep]
    if start is not None:
        first = max(int(np.searchsorted(x, start, side="right")) - 1, 0)
        x, y = np.maximum(x[first:], start), y[first:]
    if x.size and end > x[-1]:
        x, y = np.append(x, end), np.append(y, y[-1])
    t = "datetime64[s]"
    return curve_frame("time", series.unit, x, y, t, name=series.label, meta=meta)


def _dialog_times(info):
    """Return the start, end and sliding window of the view in the dialog
    *info*.

    Raise ValueError if the time in the simple time mode cannot be parsed.
    """
    if not info["simpleTime"]:
        fromtime = info["fromdate"] if info["frombox"] else None
        totime = info["todate"] if info["tobox"] else None
        return fromtime, totime, None
    itime, _ = get_time_and_interval(info["simpleTimeSpec"])
    window = itime if info["slidingWindow"] else None
    return currenttime() - itime, None, window


class HistoryPlot(QWidget):
    """A HistoryPlot shows the time plot of a view.

    Each signal is on the "left" or "right" axis or is "hidden". By default a
    second unit goes to the right axis.
    """

    def __init__(self, view, extra_menu=None):
        super().__init__()
        self.view, view.plot = view, self
        # This maps signal to place. The info of a view can share its axes with
        # a preset or an older view, so the plot takes its own copy.
        self.places = view.dlginfo["axes"] = dict(view.dlginfo.get("axes", {}))
        self.frames = FrameView(view.name, extra_menu, totals=False)
        self.canvas = FrameCanvas(self.frames)
        self.view_box = self.frames.plot.vb
        QVBoxLayout(self).setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.canvas)
        if view.yrange:
            self.view_box.enableAutoRange(y=False)
            self.view_box.setYRange(*view.yrange, padding=0)

    def refresh(self):
        """Draw the series up to now for a live view, or up to the end of the
        view."""
        view = self.view
        end = view.totime or currenttime()
        start = end - view.window if view.window else view.fromtime
        meta = {"hold": True}
        if view.missing:
            meta["facts"] = [f"no history of {', '.join(view.missing)}"]
        frames = [
            series_frame(s, start, end, meta | {"axis": self.places.get(s.descr)})
            for s in view.series.values()
            if s.n and self.places.get(s.descr) != "hidden"
        ]
        frames.sort(key=lambda frame: frame.meta["axis"] == "right")
        self.frames.show_frames(frames or [curve_frame("time", "", [], [])])

    def place(self, signal):
        """Return whether *signal* is on the "left" or "right" axis or is
        "hidden"."""
        # Ask the frames because they know where the signal is actually drawn.
        return self.frames.sides.get(self.view.series[signal].label, "hidden")

    def set_place(self, signal, place):
        """Move *signal* to *place*.

        Moving a signal to the right axis hides the signals there that have
        another unit.
        """
        units = {s.descr: s.unit for s in self.view.series.values()}
        for other, was in list(self.places.items()):
            if place == was == "right" and units.get(other) != units[signal]:
                self.places[other] = "hidden"
        self.places[signal] = place
        self.refresh()

    def unzoom(self):
        self.frames.follow_data()

    def savePlot(self):
        return save_plot_dialog(self.canvas, self)

    def printPlot(self):
        return print_plot(self.canvas, self)

    def saveQuietly(self):
        return save_plot_quietly(self.canvas)

    # Reuse the data export of the GR plot for the series of this plot.
    saveData = ViewPlot.saveData

    @property
    def plotcurves(self):
        return [series for series in self.view.series.values() if series.n]

    def _getCurveLegend(self, series):
        return series.title

    def _getCurveData(self, series):
        return series.x, series.y


class HistoryPanel(history.HistoryPanel):
    """The panel shows time series plots of any cache values."""

    panelName = "History"

    def __init__(self, parent, client, options):
        history.HistoryPanel.__init__(self, parent, client, options)
        # The 20 px of the base class are below the minimum width.
        self.splitter.setSizes([200, 800])
        self.splitter.restoreState(self.splitterstate)
        self.empty = QLabel(
            "There is no history view yet. New View in the tool bar adds one."
        )
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plotLayout.addWidget(self.empty)
        self._refresh_presets()
        self._holdTimer = QTimer(self, interval=1000)
        self._holdTimer.timeout.connect(self._holdCurrentView)
        self._holdTimer.start()

    def setPanelToolbar(self):
        bar = super().setPanelToolbar()
        in_menu = (self.actionScaleX, self.actionScaleY, self.actionUnzoom)
        # These actions are in the plot menu instead.
        for action in (*in_menu, self.actionSavePlot):
            bar.removeAction(action)
        self.presetmenu.setTitle("Presets")
        return bar

    def _plot_entries(self, entries, _view):
        entries["Curves"] = self._fill_curves_menu
        entries["Presets"] = lambda m: m.addMenu(self.presetmenu)
        entries["Attach to electronic log"] = lambda m: m.addAction(
            self.actionAttachElog
        )

    def setCustomStyle(self, font, back):
        self.user_font, self.user_color = font, back

    def _autoscale(self, x=None, y=None):
        """Do nothing because a plot follows the data until it is zoomed and
        again after "Reset zoom"."""

    def _fill_curves_menu(self, menu):
        plot = self.currentPlot
        signals = [s for s in plot.view.series.values() if s.n] if plot else []
        if not signals:
            menu.addAction("(no curves)").setEnabled(False)
        # Hidden curves are marked so that they match the count in the title.
        for series in signals:
            d = series.descr
            sub = menu.addMenu(series.title + " (hidden)" * (plot.place(d) == "hidden"))
            radio_entries(sub, PLACES, plot.place(d), partial(plot.set_place, d))

    def _createViewFromDialog(self, info, row=None):
        if not info["devices"].strip():
            return None
        keys, exprs, descs = parseKeyExpression(info["devices"], multiple=True)
        name = info["name"] or info["devices"]
        if info["simpleTime"]:
            name += f" ({info['simpleTimeSpec']})"
        try:
            fromtime, totime, window = _dialog_times(info)
        except ValueError:
            return None
        try:
            interval = float(info.get("interval", ""))
        except ValueError:
            interval = 5.0
        times = (fromtime, totime, window, custom_y_limits(info))
        view = View(self, info, name, keys, exprs, descs, times, interval)
        self.views.append(view)
        view.listitem = QListWidgetItem(view.name)
        row = self.viewList.count() if row is None else row
        self.viewList.insertItem(row, view.listitem)
        self.openView(view)
        if view.totime is None:
            for key in view.uniq_keys:
                self.keyviews.setdefault(key, []).append(view)
        return view

    def _holdCurrentView(self):
        """Extend the curves of a live view to now because cache values stay
        valid until they change."""
        plot = self.currentPlot
        if plot is not None and plot.view.totime is None:
            plot.refresh()

    def openView(self, view):
        if not view.plot:
            HistoryPlot(view, self._plot_entries)
        self.viewList.setCurrentItem(view.listitem)
        self.setCurrentView(view)

    def setCurrentView(self, view):
        if self.currentPlot:
            self.plotLayout.removeWidget(self.currentPlot)
            self.currentPlot.hide()
        self.currentPlot = plot = view and view.plot
        self.empty.setVisible(view is None)
        self.enablePlotActions(view is not None)
        if view is None:
            return
        if view in self.viewStack:
            self.viewStack.remove(view)
        self.viewStack.append(view)
        self.viewList.setCurrentItem(view.listitem)
        self.plotLayout.addWidget(plot)
        plot.show()
        # The timer redraws only the shown plot, so a plot that was hidden is
        # out of date.
        plot.refresh()

    def on__actionEditView_triggered(self):
        view = self.viewStack[-1]
        dialog = NewViewDialog(self, view.dlginfo, client=self.client)
        dialog.setWindowTitle("Edit history view")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        # Merging keeps the axes of the old view.
        info = dict(view.dlginfo, **dialog.infoDict())
        if dialog.savePreset.isChecked():
            self._add_preset(info["name"], info)
        self._replace_view(view, info)

    def _replace_view(self, view, info):
        """Build a view from *info* in the row of *view*, and remove *view* only
        if the new view was built."""
        if self._createViewFromDialog(info, self.viewList.row(view.listitem)):
            self.viewStack.remove(view)
            self.clearView(view)

    def clearView(self, view):
        # Take the plot out of the layout before it is deleted. Removing it
        # later hands it back to Python, and the garbage collector could then
        # free it at any time, even inside Qt event handling.
        if view.plot is self.currentPlot:
            self.setCurrentView(None)
        return super().clearView(view)

    def on__actionCloseView_triggered(self):
        view = self.viewStack.pop()
        self.setCurrentView(self.viewStack[-1] if self.viewStack else None)
        view.close_plot()

    def on_client_connected(self):
        # After a longer disconnect, reload the views to avoid "flatlines".
        if currenttime() - self._disconnected_since < 5:
            return
        for view in list(self.viewStack):
            self._replace_view(view, view.dlginfo)

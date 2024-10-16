import json
import pickle
import time
from collections import OrderedDict
import random

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import DlgUtils, loadUi
from nicos.guisupport.qt import (
    QVBoxLayout,
    pyqtSignal,
    QObject,
    QToolBar,
    QAction,
    QIcon,
    QListWidget,
    QSplitter,
    Qt,
    QDateTime,
    QDialog,
    QCompleter,
    QListWidgetItem,
    QStyledItemDelegate,
    pyqtSlot,
    QInputDialog,
    QTimer,
    QByteArray,
    QMainWindow,
    QBrush,
    QColor,
)
from nicos.guisupport.trees import BaseDeviceParamTree
from nicos.utils import number_types, parseKeyExpression, parseDuration
from nicos_ess.gui.utils import get_icon
from nicos_ess.gui.widgets.pyqtgraph.history_plot import HistoryWidget
from nicos_ess.gui.widgets.pyqtgraph.utils.utils import COLORS, clear_layout, PlotTypes


class NoEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return None


def float_with_default(s, d):
    try:
        return float(s)
    except ValueError:
        return d


class NewViewDialog(DlgUtils, QDialog):
    def __init__(self, parent, info=None, client=None):
        QDialog.__init__(self, parent)
        DlgUtils.__init__(self, "History viewer")
        loadUi(self, "panels/history_new.ui")
        self.client = client

        self.fromdate.setDateTime(QDateTime.currentDateTime())
        self.todate.setDateTime(QDateTime.currentDateTime())

        self.interval.hide()
        self.label_4.hide()
        self.customY.hide()
        self.customYFrom.hide()
        self.customYTo.hide()
        self.label_5.hide()

        # Connect signals
        self.customY.toggled.connect(self.toggleCustomY)
        self.toggleCustomY(False)

        self.simpleTime.toggled.connect(self.toggleTimeOptions)
        self.extTime.toggled.connect(self.toggleTimeOptions)
        self.frombox.toggled.connect(self.toggleTimeOptions)
        self.tobox.toggled.connect(self.toggleTimeOptions)
        self.toggleTimeOptions()

        self.helpButton.clicked.connect(self.showDeviceHelp)
        self.simpleHelpButton.clicked.connect(self.showSimpleHelp)

        self.devicesFrame.hide()
        self.deviceTree = None
        self.deviceTreeSel = OrderedDict()
        if not client:
            self.devicesExpandBtn.hide()
        else:
            devices = client.getDeviceList()
            devcompleter = QCompleter(devices, self)
            devcompleter.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
            self.devices.setCompleter(devcompleter)

        if info is not None:
            self.devices.setText(info["devices"])
            self.namebox.setText(info["name"])
            self.simpleTime.setChecked(info["simpleTime"])
            self.simpleTimeSpec.setText(info["simpleTimeSpec"])
            self.slidingWindow.setChecked(info["slidingWindow"])
            self.extTime.setChecked(not info["simpleTime"])
            self.frombox.setChecked(info["frombox"])
            self.tobox.setChecked(info["tobox"])
            self.fromdate.setDateTime(QDateTime.fromSecsSinceEpoch(info["fromdate"]))
            self.todate.setDateTime(QDateTime.fromSecsSinceEpoch(info["todate"]))
            self.customY.setChecked(info["customY"])
            self.customYFrom.setText(info["customYFrom"])
            self.customYTo.setText(info["customYTo"])

    def toggleCustomY(self, on):
        self.customYFrom.setEnabled(on)
        self.customYTo.setEnabled(on)
        if on:
            self.customYFrom.setFocus()

    def toggleTimeOptions(self):
        """Enable or disable UI elements based on the time selection."""
        on = self.simpleTime.isChecked()
        self.simpleTimeSpec.setEnabled(on)
        self.slidingWindow.setEnabled(on)
        self.frombox.setEnabled(not on)
        self.fromdate.setEnabled(not on and self.frombox.isChecked())
        self.tobox.setEnabled(not on)
        self.todate.setEnabled(not on and self.tobox.isChecked())

    def on_devicesAllBox_toggled(self, on):
        self.deviceTree.only_explicit = not on
        self.deviceTree._reinit()
        self._syncDeviceTree()

    @pyqtSlot()
    def on_devicesExpandBtn_clicked(self):
        self.devicesExpandBtn.hide()
        self._createDeviceTree()

    blacklist = {"maxage", "pollinterval", "visibility", "classes", "value"}

    def _createDeviceTree(self):
        def param_predicate(name, value, info):
            return (
                name not in self.blacklist
                and (not info or info.get("userparam", True))
                and isinstance(value, (number_types, list, tuple))
            )

        def item_callback(item, parent=None):
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            if parent and item.text(0) == "status":
                item.setText(1, "0")
            item.setCheckState(0, Qt.CheckState.Unchecked)
            return True

        self.deviceTree = tree = BaseDeviceParamTree(self)
        tree.device_clause = '"." not in dn'
        tree.param_predicate = param_predicate
        tree.item_callback = item_callback
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Device/Param", "Index", "Scale", "Offset"])
        tree.setClient(self.client)

        tree.setColumnWidth(1, tree.columnWidth(1) // 2)
        tree.setColumnWidth(2, tree.columnWidth(2) // 2)
        tree.setColumnWidth(3, tree.columnWidth(3) // 2)
        tree.resizeColumnToContents(0)
        tree.setColumnWidth(0, round(tree.columnWidth(0) * 1.5))
        # disallow editing for name column
        tree.setItemDelegateForColumn(0, NoEditDelegate())
        tree.itemChanged.connect(self.on_deviceTree_itemChanged)
        self._syncDeviceTree()

        self.devicesFrame.layout().addWidget(tree)
        self.devicesFrame.show()
        self.resize(self.sizeHint())

    def _syncDeviceTree(self):
        # restore selection from entries in textbox
        if not self.devices.text():
            return

        tree = self.deviceTree
        tree.itemChanged.disconnect(self.on_deviceTree_itemChanged)
        keys = parseKeyExpression(self.devices.text(), multiple=True)[0]
        for key in keys:
            dev, _, param = key.partition("/")
            for i in range(tree.topLevelItemCount()):
                if tree.topLevelItem(i).text(0).lower() == dev:
                    devitem = tree.topLevelItem(i)
                    break
            else:
                continue
            if param == "value":
                item = devitem
                newkey = devitem.text(0)
            else:
                if not devitem.childCount():
                    tree.on_itemExpanded(devitem)
                for i in range(devitem.childCount()):
                    if devitem.child(i).text(0).lower() == param:
                        item = devitem.child(i)
                        item.parent().setExpanded(True)
                        break
                else:
                    continue
                newkey = devitem.text(0) + "." + item.text(0)
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setText(1, "")
            item.setText(2, "")
            item.setText(3, "")
            self.deviceTreeSel[newkey] = ""
        tree.itemChanged.connect(self.on_deviceTree_itemChanged)

    def on_deviceTree_itemChanged(self, item, col):
        key = item.text(0)
        if item.parent():  # a device parameter
            key = item.parent().text(0) + "." + key
        if item.checkState(0) == Qt.CheckState.Checked:
            index = item.text(1)
            if not item.text(2):
                item.setText(2, "1")
            if not item.text(3):
                item.setText(3, "0")
            suffix = "".join("[%s]" % i for i in index.split(",")) if index else ""
            scale = float_with_default(item.text(2), 1)
            offset = float_with_default(item.text(3), 0)
            if scale != 1:
                suffix += "*" + item.text(2)
            if offset != 0:
                suffix += ("+" if offset > 0 else "-") + item.text(3).strip("+-")
            self.deviceTreeSel[key] = suffix
        else:
            self.deviceTreeSel.pop(key, None)
        self.devices.setText(
            ", ".join((k + v) for (k, v) in self.deviceTreeSel.items())
        )

    def showSimpleHelp(self):
        self.showInfo(
            "Please enter a time interval with units like this:\n\n"
            "30m   (30 minutes)\n"
            "12h   (12 hours)\n"
            "1d 6h (30 hours)\n"
            "3d    (3 days)\n"
        )

    def showDeviceHelp(self):
        self.showInfo(
            "Enter a comma-separated list of device names or "
            'parameters (as "device.parameter").  Example:\n\n'
            "T, T.setpoint\n\nshows the value of device T, and the "
            "value of the T.setpoint parameter.\n\n"
            "More complex expressions using these are supported:\n"
            "- use [i] to select subitems by index, e.g. motor.status[0]\n"
            "- use *x or /x to scale the values by a constant, e.g. "
            "T*100, T.heaterpower\n"
            "- use +x or -x to add an offset to the values, e.g. "
            "T+5 or combined (T+5)*100\n"
            "- you can also use functions like sqrt()"
        )

    def accept(self):
        devices_expr = self.devices.text()
        devices, expressions, descriptions = parseKeyExpression(
            devices_expr, multiple=True
        )
        if len(devices) == 0:
            self.showError("You must select at least one device/signal.")
            return

        if self.simpleTime.isChecked():
            try:
                parseDuration(self.simpleTimeSpec.text())
            except ValueError:
                self.showSimpleHelp()
                return

        if self.customY.isChecked():
            try:
                float(self.customYFrom.text())
            except ValueError:
                self.showError("You have to input valid y axis limits.")
                return
            try:
                float(self.customYTo.text())
            except ValueError:
                self.showError("You have to input valid y-axis limits.")
                return
        return QDialog.accept(self)

    def infoDict(self):
        return dict(
            devices=self.devices.text(),
            name=self.namebox.text(),
            simpleTime=self.simpleTime.isChecked(),
            simpleTimeSpec=self.simpleTimeSpec.text(),
            slidingWindow=self.slidingWindow.isChecked(),
            frombox=self.frombox.isChecked(),
            tobox=self.tobox.isChecked(),
            fromdate=self.fromdate.dateTime().toSecsSinceEpoch(),
            todate=self.todate.dateTime().toSecsSinceEpoch(),
            customY=self.customY.isChecked(),
            customYFrom=self.customYFrom.text(),
            customYTo=self.customYTo.text(),
        )


class LineData(QObject):
    dataChanged = pyqtSignal(str)
    throttledDataChanged = pyqtSignal(str)

    def __init__(
        self,
        name,
        raw_data=None,
        color_index=None,
        expires=False,
        throttle_rate_ms=1000,
        synthetic_rate_ms=1000,
        units=None,
    ):
        super().__init__()
        if raw_data is None:
            raw_data = []
        self.raw_data = raw_data
        self._name = name
        self._timestamps = None
        self._values = None
        self._expires = expires
        self._throttle_rate_ms = throttle_rate_ms
        self._synthetic_rate_ms = synthetic_rate_ms
        self._units = units if units else ""
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._on_timer_timeout)
        self._update_timer.start(throttle_rate_ms)
        self._color = (
            random.choice(COLORS) if color_index is None else COLORS[color_index]
        )

        self.dataChanged.connect(self._on_data_changed)

        self._last_throttled_timestamp = 0

        if raw_data:
            self._timestamps, self._values = self._process_raw_data(raw_data)
            self.dataChanged.emit(self._name)
            self.throttledDataChanged.emit(self._name)

    def _process_raw_data(self, raw_data):
        timestamps = np.array([x[0] for x in raw_data])
        values = np.array([x[1] for x in raw_data])
        return timestamps, values

    def set_units(self, units):
        self._units = units

    def get_units(self):
        return self._units

    def remove_duplicates(self, timestamps, values):
        timestamps, indices = np.unique(timestamps, return_index=True)
        values = np.array(values)[indices]
        return timestamps, values

    def set_raw_data(self, raw_data):
        self._timestamps, self._values = self._process_raw_data(raw_data)
        self.dataChanged.emit(self._name)

    def add_point(self, timestamp_ms, value):
        self._timestamps = np.append(self._timestamps, timestamp_ms)
        self._values = np.append(self._values, value)
        self.dataChanged.emit(self._name)

    def add_array(self, raw_data):
        timestamps, values = self._process_raw_data(raw_data)
        self._timestamps = np.append(self._timestamps, timestamps)
        self._values = np.append(self._values, values)
        self.dataChanged.emit(self._name)

    def set_arrays(self, timestamps, values):
        self._timestamps = timestamps
        self._values = values
        self.dataChanged.emit(self._name)

    def _on_timer_timeout(self):
        if time.time() - self._last_throttled_timestamp > self._throttle_rate_ms / 1000:
            self.throttledDataChanged.emit(self._name)
            self._last_throttled_timestamp = time.time()

    def _on_data_changed(self):
        timestamps, values = self.remove_duplicates(self._timestamps, self._values)
        self._timestamps = timestamps
        self._values = values

    def get_data(self):
        return self._timestamps, self._values

    def get_color(self):
        return self._color

    def get_name(self):
        return self._name

    def does_expire(self):
        return self._expires

    def trim_data(self, start_time):
        if self._timestamps is None or len(self._timestamps) == 0:
            return
        idx = np.searchsorted(self._timestamps, start_time)
        self._timestamps = self._timestamps[idx:]
        self._values = self._values[idx:]

    def update_synthetic_data(self):
        if self._timestamps is None or len(self._timestamps) == 0:
            return
        last_ts = self._timestamps[-1]
        if time.time() - last_ts > self._synthetic_rate_ms / 1000:
            self.add_point(time.time(), self._values[-1])


class HistoryPanel(Panel):
    panelName = "History"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self.history_view = HistoryWidget()
        self.views = []

        self._lines = {}
        self._plots = {}

        self._window_length = 100

        self.data = self.mainwindow.data

        self.data.datasetAdded.connect(self.on_scan_info)
        self.data.pointsAdded.connect(self.on_scan_data)
        self.data.fitAdded.connect(self.on_scan_fit)
        self.client.scan_start_event.connect(self.on_scan_start)
        self.client.scan_end_event.connect(self.on_scan_end)

        self.initialize_view_widget()
        self.initialize_ui()
        self.create_toolbar()
        self.build_ui()
        self.setup_connections(client)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self.on_poll)
        self._poll_timer.start(100)

    def on_scan_start(self, info):
        """
        The info is a dictionary with the following keys:
        "devices": str, "fromdate": int
        The info does not contain any other information.
        We then need to build a view from this info. and spawn a new history view.
        """
        default_view_info = {
            "name": f"Scan {info['fromdate']} {info['devices']}",
            "devices": info["devices"],
            "fromdate": info["fromdate"],
            "todate": time.time() + 60 * 60 * 24,  # some time in the future
            "simpleTime": False,
            "simpleTimeSpec": "1h",
            "slidingWindow": False,
            "frombox": True,
            "tobox": False,
            "customY": False,
            "customYFrom": "",
            "customYTo": "",
        }
        self.create_view_from_info(default_view_info)
        self.views_list.setCurrentRow(self.views_list.count() - 1)
        print("on_scan_start", info)

    def on_scan_end(self, info):
        """
        This one gets the view from the list of views and edits it, by adding a todate.
        The info contains the following keys:
        "devices": str, "fromdate": int, "todate": int
        """
        name = f"Scan {info['fromdate']} {info['devices']}"
        for view in self.views:
            view_info = view.data(Qt.ItemDataRole.UserRole)
            if view_info.get("name") == name:
                view_info["todate"] = info["todate"]
                view_info["tobox"] = True
                self.update_view(view, view_info)

        print("on_scan_end", info)

    def on_scan_info(self, blob):
        print("on_scan_info", blob)

    def on_scan_data(self, dataset):
        print("on_scan_data", dataset)

    def on_scan_fit(self, dataset, fit):
        print("on_scan_fit", dataset, fit)

    def initialize_ui(self):
        self.main_layout = QVBoxLayout()
        self.views_layout = QVBoxLayout()
        self.controls_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

    def initialize_view_widget(self):
        self.views_list = QListWidget()
        for name, view in self.last_views:
            name = view.get("name") or view.get("devices")
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, view)
            item.setForeground(QBrush(QColor("#aaaaaa")))
            self.views_list.addItem(item)

    def create_toolbar(self):
        self.toolbar = QToolBar("History Toolbar")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.layout().addWidget(self.toolbar)

        actions_info = [
            ("Add View", "add_circle_outline-24px.svg", self.on_add_view),
            ("Edit View", "edit-24px.svg", self.on_edit_view),
            ("Delete View", "delete-24px.svg", self.on_delete_view),
            ("Autoscale View", None, self.on_autoscale_view),
            ("Correlate Signals", None, self.on_correlate_signals),
            ("Histogram Signal", None, self.on_histogram_signal),
        ]

        for text, icon_name, callback in actions_info:
            icon = get_icon(icon_name) if icon_name else QIcon()
            action = QAction(icon, text, self)
            action.triggered.connect(callback)
            setattr(self, f"{text.lower().replace(' ', '_')}_action", action)
            self.toolbar.addAction(action)

    def build_ui(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.views_list)
        self.main_splitter.addWidget(self.history_view)

        self.main_splitter.setSizes([20, 80])
        self.main_splitter.restoreState(self.splitterstate)

        self.main_layout.addWidget(self.main_splitter)

    def setup_connections(self, client):
        client.connected.connect(self.on_client_connected)
        client.cache.connect(self.on_client_cache)
        self.views_list.currentItemChanged.connect(self.on_view_item_changed)
        self.views_list.itemClicked.connect(self.on_view_item_clicked)
        self.views_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.history_view.derivedWidgetRemoved.connect(self.on_derived_widget_removed)

    def on_add_view(self):
        self._open_view_dialog(NewViewDialog)

    def on_edit_view(self):
        current_item = self.views_list.currentItem()
        if current_item:
            view_info = current_item.data(Qt.ItemDataRole.UserRole)
            self._open_view_dialog(NewViewDialog, view_info, current_item)

    def on_item_double_clicked(self, item):
        if item:
            view_info = item.data(Qt.ItemDataRole.UserRole)
            self._open_view_dialog(NewViewDialog, view_info, item)

    def _open_view_dialog(self, dialog_class, info=None, item=None):
        dialog = dialog_class(self, info=info, client=self.client)
        if dialog.exec() == QDialog.Accepted:
            view_info = dialog.infoDict()
            if item:
                self.update_view(item, view_info)
            else:
                self.create_view_from_info(view_info)
                self.views_list.setCurrentRow(self.views_list.count() - 1)

    def on_delete_view(self):
        current_item = self.views_list.currentItem()
        if current_item:
            row = self.views_list.row(current_item)
            self.views_list.takeItem(row)
            self.views.remove(current_item)
            self.history_view.clear()

        if self.views_list.count() > 0:
            self.on_view_item_changed(self.views_list.currentItem(), None)
        else:
            self.history_view.clear()
            self.history_view.remove_all_derived_widgets()
            clear_layout(self.history_view.derived_plots_layout)
            self.history_view.reset_widget()

    def on_autoscale_view(self):
        self.history_view.set_autoscale()

    def on_correlate_signals(self):
        if len(self._lines) < 2:
            self.showError("You must have at least two signals to correlate.")
            return

        selected_signals = self._select_signals(2, "Select Signals to Correlate")
        if selected_signals:
            self.history_view.create_xy_plot(selected_signals)
            self._update_view_info(PlotTypes.XY.value, selected_signals)
        else:
            self.showError("You must select exactly two signals.")

    def on_histogram_signal(self):
        selected_signals = self._select_signals(1, "Select Signal for Histogram")
        if selected_signals:
            self.history_view.create_histogram_plot(selected_signals)
            self._update_view_info(PlotTypes.HISTOGRAM.value, selected_signals)

    def on_poll(self):
        for line in self._lines.values():
            line.update_synthetic_data()

    def loadSettings(self, settings):
        self.splitterstate = settings.value("splitter", "", QByteArray)
        self.presetdict = {}
        # read new format if present
        settings.beginGroup("presets_new")
        for key in settings.childKeys():
            self.presetdict[key] = json.loads(settings.value(key))
        settings.endGroup()
        # convert old format
        try:
            presetval = settings.value("presets")
            if presetval:
                for name, value in presetval.items():
                    if not isinstance(value, bytes):
                        value = value.encode("latin1")
                    self.presetdict[name] = pickle.loads(value)
        except Exception:
            pass
        settings.remove("presets")
        self.last_views = []
        settings.beginGroup("views_new")
        for key in settings.childKeys():
            try:
                info = json.loads(settings.value(key))
                self.last_views.append((key, info))
            except Exception:
                pass
        settings.endGroup()

    def saveSettings(self, settings):
        settings.setValue("splitter", self.main_splitter.saveState())
        settings.beginGroup("presets_new")
        for key, info in self.presetdict.items():
            settings.setValue(key, json.dumps(info))
        settings.endGroup()
        settings.beginGroup("views_new")
        settings.remove("")  # empty the existing entries before add new
        for view_item in self.views:
            view_info = view_item.data(Qt.ItemDataRole.UserRole)
            view_name = view_info.get("name") or view_info.get("devices")
            settings.setValue(view_name, json.dumps(view_info))
        settings.endGroup()

    def _select_signals(self, count, title):
        signal_names = list(self._lines.keys())
        selected_signals = []
        for i in range(count):
            signal, ok = QInputDialog.getItem(
                self,
                title,
                f"Select signal {i + 1}:",
                signal_names,
                0,
                False,
            )
            if not ok or signal in selected_signals:
                return None
            selected_signals.append(signal)
            signal_names.remove(signal)
        return selected_signals

    def _update_view_info(self, plot_type, data):
        current_item = self.views_list.currentItem()
        if current_item:
            view_info = current_item.data(Qt.ItemDataRole.UserRole)
            view_info[plot_type] = data
            current_item.setData(Qt.ItemDataRole.UserRole, view_info)

    def create_view_from_info(self, info):
        name = info.get("name") or info.get("devices")
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, info)
        self.views_list.addItem(item)
        self.views.append(item)
        self.load_view(info)

    def update_view(self, item, info):
        name = info.get("name") or info.get("devices")
        item.setText(name)
        item.setData(Qt.ItemDataRole.UserRole, info)
        self.load_view(info)

    def load_view(self, info):
        self.history_view.clear()
        self.history_view.remove_all_derived_widgets()
        clear_layout(self.history_view.derived_plots_layout)
        self.history_view.reset_widget()
        self._lines.clear()
        self._plots.clear()
        devices_expr = info["devices"]

        xy_plots = info.get(PlotTypes.XY.value, None)
        histogram = info.get(PlotTypes.HISTOGRAM.value, None)

        if xy_plots:
            self.history_view.create_xy_plot(xy_plots)
        if histogram:
            self.history_view.create_histogram_plot(histogram)

        simple_query = info["simpleTime"]
        extended_query_open = not info["tobox"] and not simple_query

        live_updating = simple_query or extended_query_open

        self._window_length = parseDuration(info["simpleTimeSpec"])
        devices, expressions, descriptions = parseKeyExpression(
            devices_expr, multiple=True
        )
        for i, (device, expr, desc) in enumerate(
            zip(devices, expressions, descriptions)
        ):
            fr = time.time() - self._window_length if simple_query else info["fromdate"]
            to = time.time() + 60 if live_updating else info["todate"]
            interval = None
            data = self._get_history(device, fr, to, interval)

            if not data:
                rescaled_to = to - 60 if live_updating else to
                #  No history data available, synthesise some fake data based
                #  on the last known value
                result = self._get_cached_value(device)
                last_value = [res for res in result if res[0] == device][0][1]
                num_fake_points = max((rescaled_to - fr) // 60, 100)
                data = [
                    (ts, last_value)
                    for ts in np.linspace(fr, rescaled_to, num_fake_points)
                ]

            try:
                units = self._get_cached_value(f"{desc}/unit")[0][1]
            except IndexError:
                units = None

            line = self._lines.get(device, None)
            if line is None:
                line = LineData(
                    device,
                    data,
                    color_index=i,
                    expires=simple_query,
                    throttle_rate_ms=1000,
                    units=units,
                )
                self._lines[device] = line
                if live_updating:
                    line.throttledDataChanged.connect(self.on_line_data_changed)
            else:
                line.set_raw_data(data)

        self.history_view.set_plots(self._lines)

    def on_view_item_changed(self, current, previous):
        if current:
            view_info = current.data(Qt.ItemDataRole.UserRole)
            if current in self.views:
                self.load_view(view_info)

    def on_view_item_clicked(self, item):
        info = item.data(Qt.ItemDataRole.UserRole)
        if info is not None and item not in self.views:
            row = self.views_list.row(item)

            do_restore = self.askQuestion("Restore this view from last time?")
            self.views_list.takeItem(row)

            new_item = QListWidgetItem(item.text())
            new_item.setData(Qt.ItemDataRole.UserRole, info)
            if do_restore:
                self.views_list.insertItem(row, new_item)
                self.views.append(new_item)
                self.views_list.setCurrentItem(new_item)

        self.on_view_item_changed(item, None)

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def get_start_time(self):
        return time.time() - self._window_length

    def on_line_data_changed(self, key):
        self._remove_expired_data()
        self.history_view.update_plot(key, self._lines)

    def _remove_expired_data(self):
        start_time = self.get_start_time()
        for key, line in self._lines.items():
            if line.does_expire():
                line.trim_data(start_time)

    def on_client_cache(self, data):
        timestamp, key, _, value = data
        if key in self._lines:
            self._lines[key].add_point(timestamp, eval(value))

    def _get_history(self, key, fr, to, interval):
        return self.client.ask(
            "gethistory", key, str(fr), str(to), interval, default=[]
        )

    def _get_cached_value(self, key):
        result = self.client.ask("getcachekeys", key, default=[])
        return result

    def on_client_connected(self):
        pass

    def on_derived_widget_removed(self, widget_name):
        current_item = self.views_list.currentItem()
        if current_item:
            info = current_item.data(Qt.ItemDataRole.UserRole)
            info.pop(widget_name, None)
            current_item.setData(Qt.ItemDataRole.UserRole, info)

    def closeEvent(self, event):
        self.saveSettings(self.settings)
        return QMainWindow.closeEvent(self, event)

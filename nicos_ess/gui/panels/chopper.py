"""NICOS livewidget with pyqtgraph."""

import time

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QSplitter,
    Qt,
    QVBoxLayout,
)
from nicos_ess.gui.widgets.chopper_widget import (
    ChopperWidget,
)
from nicos_ess.gui.widgets.pyqtgraph.histogram_data_viewer import (
    HistogramDataViewer,
    TrendViewer,
)

BIN_WIDTH = 100


def nanoseconds_to_degrees(timedelta, frequency):
    return timedelta * frequency * 360 / 1e9


class MiniDB:
    """
    A simple key value store with a max size.
    Later this should be replaced with the nicos cache / redis timeseries.
    """

    def __init__(self):
        self.DB = {}
        self._max_size = 10000

    def add(self, key, value):
        if key not in self.DB:
            self.DB[key] = []
        self.DB[key].append(value)
        if len(self.DB[key]) > self._max_size:
            self.DB[key].pop(0)


class ChopperPanel(Panel):
    panelName = "Live data view"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self._slit_direction = options.get("slit_direction", "CW")  # CW or CCW
        self._guide_pos = options.get("guide_pos", "UP")  # UP, DOWN

        self.chopper_widget = ChopperWidget(
            parent=self, slit_direction=self._slit_direction, guide_pos=self._guide_pos
        )
        self.histogram_widget = HistogramDataViewer(parent=self)
        self.trend_widget = TrendViewer(parent=self)

        self._db = MiniDB()

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def build_ui(self):
        self.view_splitter = QSplitter(Qt.Orientation.Vertical)
        self.plot_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.plot_splitter.addWidget(self.histogram_widget)
        self.plot_splitter.addWidget(self.trend_widget)

        self.view_splitter.addWidget(self.chopper_widget)
        self.view_splitter.addWidget(self.plot_splitter)

        self.layout().addWidget(self.view_splitter)

    def setup_connections(self, client):
        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.setup.connect(self.on_client_setup)
        client.disconnected.connect(self.on_client_disconnect)

        self.chopper_widget.onChopperSelected.connect(
            self._update_selected_chopper_name
        )

    def _update_selected_chopper_name(self, name):
        self._selected_chopper = name
        self._update_delay_errors(f"{name}_delay_errors")

    def handle_delay_errors(self, data):
        timestamp, key, value = data
        dev_name = key.split("/")[0]
        dev_name = dev_name.replace("_delay_errors", "")

        x, y, mean, stddev, fwhm, left_bin_edge, right_bin_edge = self._calc_stats(
            value
        )

        params = [
            ("timestamps", timestamp),
            ("x", x),
            ("y", y),
            ("mean", mean),
            ("stddev", stddev),
            ("fwhm", fwhm),
            ("left_bin_edges", left_bin_edge),
            ("right_bin_edges", right_bin_edge),
        ]
        for param_key, param in params:
            self._db.add(f"{dev_name}/{param_key}", param)

        self._update_selected_chopper()

    def _update_selected_chopper(self):
        selected = self.chopper_widget.get_selected_chopper()
        if selected:
            dev_name = selected
            x = self._db.DB[f"{dev_name}/x"][-1]
            y = self._db.DB[f"{dev_name}/y"][-1]
            timestamps = self._db.DB[f"{dev_name}/timestamps"]
            mean = self._db.DB[f"{dev_name}/mean"]
            stddev = self._db.DB[f"{dev_name}/stddev"]
            fwhm = self._db.DB[f"{dev_name}/fwhm"]
            left_bin_edge = self._db.DB[f"{dev_name}/left_bin_edges"][-1]
            right_bin_edge = self._db.DB[f"{dev_name}/right_bin_edges"][-1]

            self.histogram_widget.receive_data(
                x, y, mean[-1], stddev[-1], fwhm[-1], left_bin_edge, right_bin_edge
            )
            self.trend_widget.receive_data(timestamps, mean, stddev, fwhm)

    def _calc_stats(self, data_array):
        num_bins = int((max(data_array) - min(data_array)) / BIN_WIDTH)
        num_bins = min(max(num_bins, 1), 100)
        bins = np.linspace(min(data_array), max(data_array), num_bins)
        hist, bin_edges = np.histogram(data_array, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        x = bin_centers
        y = hist
        mean = np.mean(data_array)
        stddev = np.std(data_array, ddof=1)
        fwhm, left_idx, right_idx = self._calc_fwhm(bin_edges, hist)
        left_bin_edge = bin_edges[left_idx]
        right_bin_edge = bin_edges[right_idx]
        return x, y, mean, stddev, fwhm, left_bin_edge, right_bin_edge

    def _calc_fwhm(self, bin_edges, hist):
        half_max = max(hist) / 2
        max_idx = np.argmax(hist)

        left_indices = np.where(hist[:max_idx] < half_max)[0]
        if len(left_indices) > 0:
            left_idx = left_indices[-1]
        else:
            left_idx = 0

        right_indices = np.where(hist[max_idx:] < half_max)[0]
        if len(right_indices) > 0:
            right_idx = right_indices[0] + max_idx
        else:
            right_idx = len(hist) - 1

        fwhm = bin_edges[right_idx] - bin_edges[left_idx]
        return fwhm, left_idx, right_idx

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def _get_loaded_choppers(self):
        return [chopper["chopper"] for chopper in self.chopper_widget.chopper_data]

    def on_client_cache(self, data):
        timestamp, key, _, value = data

        device_name, parameter_name = key.split("/")

        if parameter_name != "value":
            return

        chopper_name = self._extract_chopper_name(device_name)

        loaded_choppers = self._get_loaded_choppers()
        if chopper_name not in loaded_choppers:
            return

        if device_name.endswith("_delay"):
            self._handle_delay_update(chopper_name, value)
        elif device_name.endswith("_speed"):
            self._handle_speed_update(chopper_name, value)
        elif device_name.endswith("_park_angle"):
            self._handle_park_angle_update(chopper_name, value)
        elif device_name.endswith("_delay_errors"):
            self._update_delay_errors(device_name)

    def _extract_chopper_name(self, device_name):
        suffixes = ["_delay", "_speed", "_delay_errors", "_park_angle"]
        for suffix in suffixes:
            if device_name.endswith(suffix):
                return device_name[: -len(suffix)]
        return device_name

    def _handle_delay_update(self, chopper_name, delay_value):
        delay = float(delay_value)
        frequency = self.eval_command(f"{chopper_name}_speed.read()", default=None)
        if frequency is not None and frequency != 0:
            frequency = float(frequency)
            self._update_chopper_angle(chopper_name, delay, frequency)

    def _handle_speed_update(self, chopper_name, speed_value):
        frequency = float(speed_value)
        self.chopper_widget.set_chopper_speed(chopper_name, frequency)
        if frequency != 0:
            delay = self.eval_command(f"{chopper_name}_delay.read()", default=None)
            if delay is not None:
                delay = float(delay)
                self._update_chopper_angle(chopper_name, delay, frequency)

    def _handle_park_angle_update(self, chopper_name, park_angle_value):
        park_angle = float(park_angle_value)
        self.chopper_widget.set_chopper_park_angle(chopper_name, park_angle)
        frequency = self.eval_command(f"{chopper_name}_speed.read()", default=None)
        if frequency is not None:
            frequency = float(frequency)
            if frequency < 2:
                self.chopper_widget.set_chopper_angle(chopper_name, park_angle)

    def _update_chopper_angle(self, chopper_name, delay, frequency):
        angle = nanoseconds_to_degrees(delay, frequency)
        self.chopper_widget.set_chopper_angle(chopper_name, angle)

    def _update_delay_errors(self, device_name):
        array = self.eval_command(f"{device_name}.raw_errors", default=None)
        if array is None:
            if device_name.startswith(self._selected_chopper):
                self.histogram_widget.clear()
                self.trend_widget.clear()
            return
        self.handle_delay_errors((time.time(), f"{device_name}/raw_errors", array))

    def _poll_all_choppers(self):
        signal_suffixes = ["_delay", "_speed", "_park_angle"]
        for chopper_name in self._get_loaded_choppers():
            for suffix in signal_suffixes:
                _ = self.eval_command(f"{chopper_name}{suffix}.poll()", default=None)

    def on_client_connected(self):
        self._get_chopper_info()
        self._poll_all_choppers()

    def on_client_setup(self, setup):
        self._get_chopper_info()
        self._poll_all_choppers()

    def on_client_disconnect(self):
        self.chopper_widget.clear()
        self.histogram_widget.clear()
        self.trend_widget.clear()

    def _get_chopper_info(self):
        devices = self.client.eval("session.devices", {})

        chopper_info = []

        for dev_name in devices.keys():
            disc_info = {"chopper": dev_name}
            for param in [
                "slit_edges",
                "resolver_offset",
                "tdc_offset",
                "spin_direction",
            ]:
                value = self.client.eval(f"{dev_name}.{param}", None)
                if value is None:
                    continue

                disc_info[param] = value

            if "slit_edges" in disc_info:
                chopper_info.append(disc_info)

        self.chopper_widget.update_chopper_data(chopper_info)

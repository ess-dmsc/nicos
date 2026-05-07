"""NICOS livewidget with pyqtgraph."""

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QCheckBox,
    QHBoxLayout,
    QSplitter,
    Qt,
    QVBoxLayout,
)
from nicos_ess.devices.epics.chopper import (
    CHOPPER_GUI_CHOPPER,
    CHOPPER_GUI_DELAY_ERRORS_KEY,
    CHOPPER_GUI_INFO_METHOD,
    CHOPPER_GUI_PARK_ANGLE_KEY,
    CHOPPER_GUI_SPEED_KEY,
    CHOPPER_GUI_TOTAL_DELAY_KEY,
    is_chopper_moving,
)
from nicos_ess.gui.widgets.chopper_math import (
    build_rotation_model,
    has_canonical_inputs,
)
from nicos_ess.gui.widgets.chopper_widget import (
    ChopperLegendWidget,
    ChopperWidget,
)
from nicos_ess.gui.widgets.pyqtgraph.histogram_data_viewer import (
    HistogramDataViewer,
    TrendViewer,
)

BIN_WIDTH = 100

CHOPPER_KEY_ROLE_SPEED = "speed"
CHOPPER_KEY_ROLE_TOTAL_DELAY = "total_delay"
CHOPPER_KEY_ROLE_PARK_ANGLE = "park_angle"
CHOPPER_KEY_ROLE_DELAY_ERRORS = "delay_errors"

CHOPPER_GUI_KEY_FIELDS = (
    (CHOPPER_GUI_SPEED_KEY, CHOPPER_KEY_ROLE_SPEED),
    (CHOPPER_GUI_TOTAL_DELAY_KEY, CHOPPER_KEY_ROLE_TOTAL_DELAY),
    (CHOPPER_GUI_PARK_ANGLE_KEY, CHOPPER_KEY_ROLE_PARK_ANGLE),
    (CHOPPER_GUI_DELAY_ERRORS_KEY, CHOPPER_KEY_ROLE_DELAY_ERRORS),
)


def nanoseconds_to_degrees(timedelta, frequency):
    # Delay-to-phase conversion uses frequency magnitude; spin direction
    # bookkeeping is handled from chopper metadata and speed sign.
    return timedelta * abs(frequency) * 360 / 1e9


class MiniDB:
    """
    Bounded in-memory store for recent histogram and trend values.
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

        self._guide_pos = options.get("guide_pos", "UP")  # UP, DOWN

        self.chopper_widget = ChopperWidget(parent=self, guide_pos=self._guide_pos)
        self.histogram_widget = HistogramDataViewer(parent=self)
        self.trend_widget = TrendViewer(parent=self)

        self._db = MiniDB()
        self._registered_chopper_keys = set()
        self._chopper_cache_keys = {}
        self._chopper_key_roles = {}
        self._speeds = {}
        self._total_delays = {}
        self._park_angles = {}

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        layout = QVBoxLayout()
        controls = QHBoxLayout()
        self._detail_checkbox = QCheckBox("Detailed view")
        self._detail_checkbox.setToolTip(
            "Show motor-housing opacity and TDC reference marker."
        )
        self._detail_checkbox.toggled.connect(self.chopper_widget.set_detailed_view)
        controls.addWidget(self._detail_checkbox)
        controls.addSpacing(18)
        controls.addWidget(ChopperLegendWidget(parent=self))
        controls.addStretch(1)
        layout.addLayout(controls)
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
        client.connected.connect(self.on_client_connected)
        client.setup.connect(self.on_client_setup)
        client.disconnected.connect(self.on_client_disconnect)

        self.chopper_widget.onChopperSelected.connect(
            self._update_selected_chopper_name
        )

    def _update_selected_chopper_name(self, name):
        if name is None:
            self.histogram_widget.clear()
            self.trend_widget.clear()
            return
        if f"{name}/x" in self._db.DB:
            self._update_selected_chopper()
        else:
            self.histogram_widget.clear()
            self.trend_widget.clear()

    def _handle_delay_errors(self, timestamp, chopper_name, value):
        value = np.asarray(value)
        if value.size == 0:
            return

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
            self._db.add(f"{chopper_name}/{param_key}", param)

        self._update_selected_chopper()

    def _update_selected_chopper(self):
        selected = self.chopper_widget.get_selected_chopper()
        if not selected or f"{selected}/x" not in self._db.DB:
            return

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
        data_array = np.asarray(data_array, dtype=float)
        if data_array.size == 0:
            empty = np.asarray([], dtype=float)
            return empty, empty, np.nan, np.nan, 0.0, np.nan, np.nan

        data_min = float(np.min(data_array))
        data_max = float(np.max(data_array))
        data_range = data_max - data_min
        if data_range == 0.0:
            half_width = BIN_WIDTH / 2.0
            bins = np.asarray([data_min - half_width, data_max + half_width])
        else:
            num_bins = int(np.ceil(data_range / BIN_WIDTH))
            num_bins = min(max(num_bins, 1), 100)
            bins = np.linspace(data_min, data_max, num_bins + 1)
        hist, bin_edges = np.histogram(data_array, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        x = bin_centers
        y = hist
        mean = float(np.mean(data_array))
        stddev = float(np.std(data_array, ddof=0))
        fwhm, left_idx, right_idx = self._calc_fwhm(bin_edges, hist)
        left_bin_edge = bin_edges[left_idx]
        right_bin_edge = bin_edges[right_idx]
        return x, y, mean, stddev, fwhm, left_bin_edge, right_bin_edge

    def _calc_fwhm(self, bin_edges, hist):
        if len(hist) == 0:
            return 0.0, 0, 0

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

        right_edge_idx = min(right_idx + 1, len(bin_edges) - 1)
        fwhm = bin_edges[right_edge_idx] - bin_edges[left_idx]
        return fwhm, left_idx, right_edge_idx

    def _get_loaded_choppers(self):
        return [
            chopper[CHOPPER_GUI_CHOPPER] for chopper in self.chopper_widget.chopper_data
        ]

    def on_keyChange(self, key, value, timestamp, expired):
        if key == "session/mastersetup":
            super().on_keyChange(key, value, timestamp, expired)
            return

        role_info = self._chopper_key_roles.get(key.lower())
        if role_info is None:
            return

        chopper_name, role = role_info
        if role == CHOPPER_KEY_ROLE_DELAY_ERRORS:
            if value is None or expired:
                if self.chopper_widget.get_selected_chopper() == chopper_name:
                    self.histogram_widget.clear()
                    self.trend_widget.clear()
                return
            self._handle_delay_errors(timestamp, chopper_name, value)
            return

        if value is None or expired:
            self._clear_role_value(chopper_name, role)
            return

        if role == CHOPPER_KEY_ROLE_SPEED:
            self._handle_speed_update(chopper_name, value)
        elif role == CHOPPER_KEY_ROLE_TOTAL_DELAY:
            self._handle_total_delay_update(chopper_name, value)
        elif role == CHOPPER_KEY_ROLE_PARK_ANGLE:
            self._handle_park_angle_update(chopper_name, value)

    def _handle_total_delay_update(self, chopper_name, delay_value):
        delay = float(delay_value)
        self._total_delays[chopper_name] = delay
        self._update_chopper_angle(chopper_name)

    def _handle_speed_update(self, chopper_name, speed_value):
        frequency = float(speed_value)
        self._speeds[chopper_name] = frequency
        self.chopper_widget.set_chopper_speed(chopper_name, frequency)
        self._update_chopper_angle(chopper_name)

    def _handle_park_angle_update(self, chopper_name, park_angle_value):
        park_angle = float(park_angle_value)
        self._park_angles[chopper_name] = park_angle
        self.chopper_widget.set_chopper_park_angle(chopper_name, park_angle)
        self._update_chopper_angle(chopper_name)

    def _update_chopper_angle(self, chopper_name):
        frequency = self._speeds.get(chopper_name)
        if frequency is None:
            self.chopper_widget.clear_chopper_angle(chopper_name)
            return

        if is_chopper_moving(frequency):
            delay = self._total_delays.get(chopper_name)
            if delay is not None:
                angle = nanoseconds_to_degrees(delay, frequency)
                self.chopper_widget.set_chopper_angle(chopper_name, angle)
            else:
                self.chopper_widget.clear_chopper_angle(chopper_name)
            return

        park_angle = self._park_angles.get(chopper_name)
        if park_angle is not None:
            self.chopper_widget.set_chopper_angle(chopper_name, park_angle)
        else:
            self.chopper_widget.clear_chopper_angle(chopper_name)

    def _clear_role_value(self, chopper_name, role):
        if role == CHOPPER_KEY_ROLE_SPEED:
            self._speeds.pop(chopper_name, None)
            self.chopper_widget.set_chopper_speed(chopper_name, None)
            self.chopper_widget.clear_chopper_angle(chopper_name)
        elif role == CHOPPER_KEY_ROLE_TOTAL_DELAY:
            self._total_delays.pop(chopper_name, None)
            if is_chopper_moving(self._speeds.get(chopper_name)):
                self.chopper_widget.clear_chopper_angle(chopper_name)
        elif role == CHOPPER_KEY_ROLE_PARK_ANGLE:
            self._park_angles.pop(chopper_name, None)
            self.chopper_widget.set_chopper_park_angle(chopper_name, None)
            if not is_chopper_moving(self._speeds.get(chopper_name)):
                self.chopper_widget.clear_chopper_angle(chopper_name)

    def _register_chopper_keys(self):
        registered_new_keys = False
        for normalized_key, key in self._chopper_cache_keys.items():
            if normalized_key in self._registered_chopper_keys:
                continue
            registered_key = self.client.register(self, key)
            self._registered_chopper_keys.add(registered_key.lower())
            registered_new_keys = True
        return registered_new_keys

    def _load_choppers(self):
        self._get_chopper_info()
        if self._register_chopper_keys():
            self.client.on_connected_event()
        for chopper_name in self._get_loaded_choppers():
            if chopper_name in self._speeds:
                self.chopper_widget.set_chopper_speed(
                    chopper_name, self._speeds[chopper_name]
                )
            if chopper_name in self._park_angles:
                self.chopper_widget.set_chopper_park_angle(
                    chopper_name, self._park_angles[chopper_name]
                )
            self._update_chopper_angle(chopper_name)

    def on_client_connected(self):
        self._load_choppers()

    def on_client_setup(self, setup):
        self._load_choppers()

    def on_client_disconnect(self):
        self.chopper_widget.clear()
        self.histogram_widget.clear()
        self.trend_widget.clear()

    def _get_chopper_info(self):
        devices = self.client.eval("session.devices", {})

        chopper_info = []
        self._chopper_cache_keys = {}
        self._chopper_key_roles = {}

        for dev_name in devices.keys():
            has_contract = self.client.eval(
                "hasattr(session.devices[%r], %r)"
                % (dev_name, CHOPPER_GUI_INFO_METHOD),
                False,
            )
            if not has_contract:
                continue

            disc_info = self.client.eval(
                "session.devices[%r].%s()" % (dev_name, CHOPPER_GUI_INFO_METHOD),
                None,
            )
            if not isinstance(disc_info, dict):
                continue

            chopper_name = disc_info.get(CHOPPER_GUI_CHOPPER)
            if not chopper_name:
                continue

            if not has_canonical_inputs(disc_info):
                self.log.warning(
                    "Ignoring chopper %s with incomplete GUI metadata", chopper_name
                )
                continue
            try:
                build_rotation_model(disc_info)
            except ValueError as err:
                self.log.warning(
                    "Ignoring chopper %s with invalid GUI metadata: %s",
                    chopper_name,
                    err,
                )
                continue

            self._add_chopper_key_roles(chopper_name, disc_info)
            chopper_info.append(disc_info)

        self.chopper_widget.update_chopper_data(chopper_info)

    def _add_chopper_key_roles(self, chopper_name, disc_info):
        for field, role in CHOPPER_GUI_KEY_FIELDS:
            key = disc_info.get(field)
            if not key:
                continue
            normalized_key = key.lower()
            self._chopper_cache_keys[normalized_key] = key
            self._chopper_key_roles[normalized_key] = (chopper_name, role)

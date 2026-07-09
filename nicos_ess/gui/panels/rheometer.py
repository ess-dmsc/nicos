"""NICOS Rheometer setup panel.

The device name is supplied through the panel ``options`` dict
(``options={'rheometer': '<device name>'}``)
"""

import csv
import io

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QStandardItem,
    QStandardItemModel,
    Qt,
    QTableView,
    QTimer,
    QVBoxLayout,
)

_FUNCTION_GROUPS = ("duration", "stress", "rate", "strain", "frequency")

# Panel group name -> device key prefix ("frequency" group uses "freq" keys).
_GROUP_KEY_PREFIX = {
    "duration": "duration",
    "stress": "stress",
    "rate": "rate",
    "strain": "strain",
    "frequency": "freq",
}

# enable_* cache key -> function groups it gates.
_ENABLE_GROUPS = {
    "enable_stress": ("stress",),
    "enable_rate": ("rate",),
    "enable_strain": ("strain",),
    "enable_freq": ("frequency",),
}

# enum config cache key -> combo widget attribute.
_COMBO_CONFIG_KEYS = {
    "interv_mode": "mode_combo",
    "duration_func": "duration_combo",
    "stress_func": "stress_combo",
    "rate_func": "rate_combo",
    "strain_func": "strain_combo",
    "freq_func": "frequency_combo",
}

_READBACK_LABELS = [
    ("meas_state", "State"),
    ("meas_num", "Measurement #"),
    ("meas_interval", "Interval"),
    ("meas_pt_elapsed_time", "Point elapsed [s]"),
    ("meas_syst", "Measuring system"),
    ("device_temp", "Device temp"),
    ("temp_mon", "Temperature"),
    ("gap", "Gap"),
    ("torque", "Torque"),
    ("force", "Force"),
    ("rot_speed", "Rotational speed"),
    ("phase_ang", "Phase angle"),
    ("strain", "Strain"),
    ("freq", "Frequency"),
    ("shear_stress", "Shear stress"),
    ("shear_rate", "Shear rate"),
    ("shear_strain", "Shear strain"),
    ("viscosity", "Viscosity"),
    ("tot_modulus", "|G*|"),
    ("loss_modulus", "G''"),
    ("storage_modulus", "G'"),
]

_TABLE_HEADERS = [
    "Interval",
    "Mode",
    "Measure Mode",
    "Number of Points",
    "Duration",
    "Stress",
    "Rate",
    "Strain",
    "Frequency",
]


class RheometerPanel(Panel):
    panelName = "Rheometer Setup"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self._dev = options.get("rheometer")

        # lowercased "<dev>/<key>" -> updater(value, expired)
        self._key_updaters = {}
        # which measure-mode PV the shared combo writes; set from the enable flags
        self._measure_key = "visc_meas_mode"
        # set True while populating widgets to suppress write-backs
        self._loading = False
        self._action_widgets = []

        self.build_ui()
        self.setup_connections()
        self.register_keys()
        if self.client.isconnected:
            self.on_client_connected()

    def build_ui(self):
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.build_splitter())
        self.setLayout(main_layout)

    def build_splitter(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.build_edit_layout())
        splitter.addWidget(self.build_display_layout())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    def build_edit_layout(self):
        layout = QVBoxLayout()
        frame = QFrame()

        self.mode_combo = QComboBox()
        layout.addWidget(QLabel("Mode:"))
        layout.addWidget(self.mode_combo)

        self.measure_mode_combo = QComboBox()
        layout.addWidget(QLabel("Measure Mode:"))
        layout.addWidget(self.measure_mode_combo)

        num_points_layout = QHBoxLayout()
        self.num_points_le = QLineEdit()
        num_points_layout.addWidget(QLabel("Number of measurement points:"))
        num_points_layout.addWidget(self.num_points_le)
        layout.addLayout(num_points_layout)

        temp_layout = QHBoxLayout()
        self.temp_setpoint_le = QLineEdit()
        temp_layout.addWidget(QLabel("Temperature setpoint:"))
        temp_layout.addWidget(self.temp_setpoint_le)
        layout.addLayout(temp_layout)

        grid = QGridLayout()
        for i, (group, label_text) in enumerate(
            [
                ("duration", "Duration function [s]"),
                ("stress", "Stress function [Pa]"),
                ("rate", "Rate function [1/s]"),
                ("strain", "Strain function [%]"),
                ("frequency", "Frequency function [rad/s]"),
            ]
        ):
            self._build_function_group(grid, i * 2, group, label_text)
        layout.addLayout(grid)

        layout.addStretch()

        self.add_interval_button = QPushButton("Add interval")
        self.clear_intervals_button = QPushButton("Clear intervals")
        self.send_intervals_button = QPushButton("Load intervals")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.init_button = QPushButton("Initialise device")
        for button in (
            self.add_interval_button,
            self.clear_intervals_button,
            self.send_intervals_button,
            self.start_button,
            self.stop_button,
            self.init_button,
        ):
            layout.addWidget(button)
            self._action_widgets.append(button)

        frame.setLayout(layout)
        return frame

    def _build_function_group(self, grid, row, group, label_text):
        combo = QComboBox()
        initial_le = QLineEdit()
        final_le = QLineEdit()
        setattr(self, f"{group}_label", QLabel(label_text))
        setattr(self, f"{group}_combo", combo)
        setattr(self, f"{group}_initial_le", initial_le)
        setattr(self, f"{group}_final_le", final_le)

        grid.addWidget(getattr(self, f"{group}_label"), row, 0)
        grid.addWidget(combo, row + 1, 0)
        grid.addWidget(QLabel("Initial"), row, 1)
        grid.addWidget(initial_le, row + 1, 1)
        grid.addWidget(QLabel("Final"), row, 2)
        grid.addWidget(final_le, row + 1, 2)

    def build_display_layout(self):
        layout = QVBoxLayout()
        frame = QFrame()

        self.connection_label = QLabel("Disconnected")
        self.device_model_label = QLabel("-")
        self.manufacturer_label = QLabel("-")
        header = QHBoxLayout()
        header.addWidget(QLabel("Device:"))
        header.addWidget(self.manufacturer_label)
        header.addWidget(self.device_model_label)
        header.addStretch()
        header.addWidget(self.connection_label)
        layout.addLayout(header)

        error_layout = QHBoxLayout()
        self.error_label = QLabel("")
        self.clear_error_button = QPushButton("Clear error")
        self._action_widgets.append(self.clear_error_button)
        error_layout.addWidget(QLabel("Error:"))
        error_layout.addWidget(self.error_label, 1)
        error_layout.addWidget(self.clear_error_button)
        layout.addLayout(error_layout)

        self.tableView = QTableView()
        self.tableModel = QStandardItemModel()
        self.tableView.setModel(self.tableModel)
        self.tableView.setWordWrap(True)
        self.tableView.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tableModel.setHorizontalHeaderLabels(_TABLE_HEADERS)
        layout.addWidget(self.tableView)

        readback_grid = QGridLayout()
        self._readback_value_labels = {}
        for row, (key, label_text) in enumerate(_READBACK_LABELS):
            value_label = QLabel("----")
            self._readback_value_labels[key] = value_label
            readback_grid.addWidget(QLabel(f"{label_text}:"), row // 2, (row % 2) * 2)
            readback_grid.addWidget(value_label, row // 2, (row % 2) * 2 + 1)
        layout.addLayout(readback_grid)

        frame.setLayout(layout)
        return frame

    def setup_connections(self):
        self.client.connected.connect(self.on_client_connected)
        self.client.disconnected.connect(self.on_client_disconnect)

        self.mode_combo.currentTextChanged.connect(
            lambda value: self._write_config("interv_mode", value)
        )
        self.measure_mode_combo.currentTextChanged.connect(
            lambda value: self._write_config(self._measure_key, value)
        )
        self.num_points_le.editingFinished.connect(
            lambda: self._write_config("num_meas_pts", self.num_points_le.text())
        )
        self.temp_setpoint_le.returnPressed.connect(
            lambda: self._write_config("temp_setpoint", self.temp_setpoint_le.text())
        )

        for group in _FUNCTION_GROUPS:
            prefix = _GROUP_KEY_PREFIX[group]
            combo = getattr(self, f"{group}_combo")
            initial_le = getattr(self, f"{group}_initial_le")
            final_le = getattr(self, f"{group}_final_le")
            combo.currentTextChanged.connect(
                lambda value, p=prefix: self._write_config(f"{p}_func", value)
            )
            initial_le.editingFinished.connect(
                lambda p=prefix, le=initial_le: self._write_config(
                    f"{p}_init", le.text()
                )
            )
            final_le.editingFinished.connect(
                lambda p=prefix, le=final_le: self._write_config(
                    f"{p}_final", le.text()
                )
            )

        self.add_interval_button.clicked.connect(
            lambda: self._call_method("add_interval")
        )
        self.clear_intervals_button.clicked.connect(
            lambda: self._call_method("clear_intervals")
        )
        self.send_intervals_button.clicked.connect(
            lambda: self._call_method("send_intervals")
        )
        self.start_button.clicked.connect(lambda: self._call_method("start"))
        self.stop_button.clicked.connect(lambda: self._call_method("stop"))
        self.init_button.clicked.connect(lambda: self._call_method("init_device"))
        self.clear_error_button.clicked.connect(lambda: self._call_method("clear_err"))

    def register_keys(self):
        """Subscribe to exactly the rheometer keys the panel displays."""
        if not self._dev:
            return
        self._key_updaters = {}
        readback_keys = (
            [key for key, _ in _READBACK_LABELS]
            + list(_ENABLE_GROUPS)
            + list(_COMBO_CONFIG_KEYS)
            + ["enable_osc_mode", "enable_visc_mode", "interv_raw_table"]
            + ["device_connected", "manufacturer", "device_model", "err_msg"]
        )
        for cache_key in readback_keys:
            full_key = f"{self._dev}/{cache_key}".lower()
            self._key_updaters[full_key] = self._make_updater(cache_key)
            self.client.register(self, full_key)

    def _make_updater(self, cache_key):
        if cache_key == "interv_raw_table":
            return self._update_interval_table
        if cache_key in _COMBO_CONFIG_KEYS:
            combo = getattr(self, _COMBO_CONFIG_KEYS[cache_key])
            return lambda value, expired: self._update_combo(
                combo, cache_key, value, expired
            )
        if cache_key in _ENABLE_GROUPS:
            return lambda value, expired: self._update_group_enabled(cache_key, value)
        if cache_key in ("enable_osc_mode", "enable_visc_mode"):
            return lambda value, expired: self._update_measure_binding(cache_key, value)
        if cache_key == "device_connected":
            return self._update_connection
        if cache_key == "err_msg":
            return self._update_error
        if cache_key == "manufacturer":
            return lambda value, expired: self.manufacturer_label.setText(str(value))
        if cache_key == "device_model":
            return lambda value, expired: self.device_model_label.setText(str(value))
        return lambda value, expired: self._update_readback(cache_key, value, expired)

    def on_keyChange(self, key, value, time, expired):
        updater = self._key_updaters.get(key.lower())
        if updater is not None:
            updater(value, expired)

    def _update_readback(self, cache_key, value, expired):
        label = self._readback_value_labels.get(cache_key)
        if label is None:
            return
        label.setText("----" if expired or value is None else str(value))

    def _update_group_enabled(self, enable_key, value):
        enabled = bool(value)
        for group in _ENABLE_GROUPS[enable_key]:
            self._set_group_enabled(group, enabled)

    def _set_group_enabled(self, group, enabled):
        for suffix in ("combo", "initial_le", "final_le"):
            getattr(self, f"{group}_{suffix}").setEnabled(enabled)

    def _update_measure_binding(self, enable_key, value):
        if not value:
            return
        self._measure_key = (
            "osc_meas_mode" if enable_key == "enable_osc_mode" else "visc_meas_mode"
        )
        self._populate_combo(self.measure_mode_combo, self._measure_key)

    def _update_connection(self, value, expired):
        connected = bool(value) and not expired
        self.connection_label.setText("Connected" if connected else "Disconnected")

    def _update_error(self, value, expired):
        self.error_label.setText("" if expired or value is None else str(value))

    def _update_interval_table(self, value, expired):
        # #IntervRawTable is CSV with an "idx,..." header row; fields may be
        # quoted and contain commas (e.g. "LIN(0.1,5)"). Columns match
        # _TABLE_HEADERS.
        self.tableModel.clear()
        self.tableModel.setHorizontalHeaderLabels(_TABLE_HEADERS)
        if expired or not value:
            return
        for cells in csv.reader(io.StringIO(str(value))):
            if not any(cell.strip() for cell in cells):
                continue
            if cells[0].strip().lower() == "idx":  # IOC header row
                continue
            cells = (cells + [""] * len(_TABLE_HEADERS))[: len(_TABLE_HEADERS)]
            self.tableModel.appendRow([QStandardItem(cell.strip()) for cell in cells])
        QTimer.singleShot(0, self.tableView.resizeRowsToContents)
        QTimer.singleShot(0, self.tableView.resizeColumnsToContents)

    def _write_config(self, key, value):
        if self._loading or not self._dev:
            return
        self.client.tell("exec", f"{self._dev}.set_pv({key!r}, {value!r})")

    def _call_method(self, method):
        if not self._dev:
            return
        self.client.tell("exec", f"{self._dev}.{method}()")

    def on_client_connected(self):
        self.connection_label.setText("Connected")
        self._populate_combos()

    def on_client_disconnect(self):
        self.connection_label.setText("Disconnected")
        for label in self._readback_value_labels.values():
            label.setText("----")
        self.error_label.setText("")

    def _populate_combos(self):
        if not self._dev:
            return
        self._populate_combo(self.mode_combo, "interv_mode")
        self._populate_combo(self.measure_mode_combo, self._measure_key)
        for group in _FUNCTION_GROUPS:
            prefix = _GROUP_KEY_PREFIX[group]
            self._populate_combo(getattr(self, f"{group}_combo"), f"{prefix}_func")

    def _populate_combo(self, combo, config_key):
        choices = self.client.eval(f"{self._dev}.get_choices({config_key!r})", [])
        if not choices:
            # leave empty so a later cache event retries (channels may be cold)
            return
        self._loading = True
        try:
            combo.blockSignals(True)
            current = combo.currentText()
            combo.clear()
            combo.addItems([str(choice) for choice in choices])
            if current:
                index = combo.findText(current)
                if index >= 0:
                    combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)
            self._loading = False

    def _update_combo(self, combo, config_key, value, expired):
        if combo.count() == 0:
            self._populate_combo(combo, config_key)
        if not expired and value is not None:
            self._apply_combo_value(combo, value)

    def _apply_combo_value(self, combo, value):
        index = -1
        if isinstance(value, str) and not value.isdigit():
            index = combo.findText(value)
        else:
            try:
                index = int(value)
            except (TypeError, ValueError):
                index = -1
        if not 0 <= index < combo.count():
            return
        self._loading = True
        try:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)
            self._loading = False

    def setViewOnly(self, viewonly):
        for widget in self._action_widgets:
            widget.setEnabled(not viewonly)

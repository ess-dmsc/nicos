import time

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
)
from nicos.protocols.cache import cache_load
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView
from nicos_ess.gui.widgets.pyqtgraph.plot_parts import number_field
from nicos_ess.utilities.frame_views import Axis, axis
from nicos_ess.utilities.live_frame import curve_frame, float_array, frames

SPECTROMETERS = ["hr4", "qepro"]  # TODO: get the names from the server
GREEN = "rgba(0, 200, 0, 75%)"
BLUE = "rgba(0, 0, 255, 60%)"
RED = "rgba(255, 0, 0, 60%)"
# Each drawing mode uses these arrays, so their arrival redraws the plot.
REDRAWN_BY = {
    "normal": {"normal"},
    "lightbackground": {"lightbackground"},
    "darkbackground": {"darkbackground"},
    "subtraction": {"normal", "lightbackground"},
    "absorbance": {"normal", "lightbackground", "darkbackground"},
}


def spectrum_array(values):
    """Return *values* as a 1-D float array, or an empty array if they do not
    form one."""
    array = float_array(values)
    return array if array.ndim == 1 else np.array([])


def _background(color):
    return f"background-color: {color}"


def _minimum(widget):
    widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
    return widget


def _group(title):
    group = QGroupBox(title)
    group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    grid = QGridLayout(group)
    grid.setContentsMargins(5, 5, 5, 5)
    grid.setHorizontalSpacing(5)
    grid.setVerticalSpacing(10)
    return group, grid


class SpectrometerControl(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.selected_device = None
        layout = QVBoxLayout(self)

        settings, grid = _group("Settings")
        self.detector_combo = self._combo([])
        self.detector_combo.currentIndexChanged.connect(self.on_detector_changed)
        # Only a choice of the user is sent, never a readback from the cache.
        self.acq_mode_combo = self._combo(["single", "continuous"])
        self.acq_mode_combo.activated.connect(self.on_acq_mode)
        self.integration_time_lbl = QLabel()
        self.set_integration_time_units("ms")
        self.integration_time = self._field("integrationtime")
        self.boxcar_width = self._field("boxcarwidth")
        rows = (
            (QLabel("Spectrometer:"), self.detector_combo),
            (QLabel("Acquisition Mode:"), self.acq_mode_combo),
            (self.integration_time_lbl, self.integration_time),
            (QLabel("Boxcar Width:"), self.boxcar_width),
        )
        for row, (label, widget) in enumerate(rows):
            grid.addWidget(label, row, 0)
            grid.addWidget(widget, row, 1)
            if isinstance(widget, QLineEdit):
                grid.addWidget(widget.readback, row, 2)
        grid.setRowStretch(5, 1)
        grid.setColumnStretch(0, 1)
        layout.addWidget(settings)
        self.fields = [self.integration_time, self.boxcar_width]

        normalisation, grid = _group("Normalisation")
        self.checkboxes = []
        for row, (text, mode) in enumerate(
            (
                ("Display Light Background", "lightbackground"),
                ("Display Dark Background", "darkbackground"),
                ("Subtract Light Background", "subtraction"),
                ("Calculate Absorbance", "absorbance"),
            )
        ):
            box = QCheckBox(text)
            box.clicked.connect(lambda _c=False, b=box, m=mode: self._switch_plot(b, m))
            grid.addWidget(box, row, 0)
            self.checkboxes.append(box)
        self.valid_labels = {}
        for row, which in enumerate(("light", "dark"), start=4):
            label = QLabel(
                f"{which.capitalize()} background is invalid. Please acquire a new one."
            )
            label.setStyleSheet("color: red")
            label.hide()
            grid.addWidget(label, row, 0)
            self.valid_labels[f"{which}valid"] = label
        grid.setRowStretch(6, 1)
        layout.addWidget(normalisation)

        row = QHBoxLayout()
        self.start_acq_button = self._button(row, "Start Acquisition", GREEN)
        self.start_acq_button.clicked.connect(parent.start_acquisition)
        self.stop_acq_button = self._button(row, "Stop Acquisition")
        self.stop_acq_button.clicked.connect(lambda: parent.call("stop()"))
        layout.addLayout(row)
        row = QHBoxLayout()
        for which, color in (
            ("light", "rgba(200, 0, 0, 25%)"),
            ("dark", "rgba(0, 0, 200, 25%)"),
        ):
            button = self._button(
                row, f"Save As {which.capitalize()} Background", color
            )
            button.clicked.connect(
                lambda _c=False, w=which: parent.call(f"save_{w}_background()")
            )
            setattr(self, f"save_{which}_acq_button", button)
        layout.addLayout(row)

    def _button(self, row, text, color=None):
        button = _minimum(QPushButton(text))
        if color:
            button.setStyleSheet(_background(color))
        row.addWidget(button)
        return button

    def _combo(self, items):
        combo = _minimum(QComboBox())
        combo.setMinimumContentsLength(1)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.addItems(items)
        return combo

    def _field(self, param):
        # Qt emits returnPressed only for a number that the validator accepts.
        field = _minimum(number_field())
        field.setPlaceholderText("Set Value")
        field.returnPressed.connect(
            lambda: self._send(f"{param} = {float(field.text()):f}")
        )
        field.readback = QLabel("Readback Value")
        return field

    def set_integration_time_units(self, units):
        self.integration_time_lbl.setText(f"Integration Time ({units}):")

    def _send(self, assignment):
        if self.selected_device:
            self.parent.exec_command(f"{self.selected_device}.{assignment}")

    def on_acq_mode(self, _index):
        self._send(f'acquiremode = "{self.acq_mode_combo.currentText()}"')

    def on_detector_changed(self, _index):
        self.selected_device = self.detector_combo.currentText()
        if not self.selected_device:
            return
        self._populate_readbacks()
        for field in self.fields:
            field.setText(field.readback.text())
        self.parent.select_spectrometer(self.selected_device)

    def _switch_plot(self, checkbox, mode):
        """Show what *checkbox* selects. The boxes exclude each other."""
        for box in self.checkboxes:
            if box is not checkbox:
                box.setChecked(False)
        self.parent.draw(mode if checkbox.isChecked() else "normal")

    def clear_normalisation_checkboxes(self):
        for box in self.checkboxes:
            box.setChecked(False)

    def _populate_readbacks(self):
        try:
            self.parent.client.eval(f"{self.selected_device}.pollParams()")
        except NameError:
            return
        params = self.parent.client.getDeviceParams(self.selected_device)
        if not params:
            return
        for param, value in params.items():
            self._show_readback(param, value)
        self._show_status(params.get("status"))
        self._highlight_differing_readback_values()

    def handle_cache_key(self, key, value):
        param = key.rsplit("/", 1)[1]
        if param == "status":
            self._show_status(value)
        elif self._show_readback(param, value):
            self._highlight_differing_readback_values()

    def _show_readback(self, param, value):
        """Show the value of a parameter. Return False if the panel does not show it."""
        if param in ("integrationtime", "boxcarwidth"):
            field = self.integration_time if param[0] == "i" else self.boxcar_width
            field.readback.setText("----" if value is None else str(value))
        elif param == "acquiremode":
            self.acq_mode_combo.setCurrentText(str(value))
        elif param in self.valid_labels:
            self.valid_labels[param].setVisible(not value)
        else:
            return False
        return True

    def _show_status(self, status):
        match status:
            case [_, str(text), *_] if text:
                idle = "Done" in text or "Idle" in text
                color = GREEN if idle else BLUE if "Acquiring" in text else RED
                self.start_acq_button.setStyleSheet(_background(color))

    def _highlight_differing_readback_values(self):
        for field in self.fields:
            try:
                differs = float(field.text()) != float(field.readback.text())
            except ValueError:
                continue
            color = "rgba(255, 0, 0, 75%)" if differs else "rgba(255, 255, 255, 0%)"
            field.readback.setStyleSheet(_background(color))


class SpectrometerPanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        kinds = ("normal", "lightbackground", "darkbackground")
        self.arrays = {kind: np.array([]) for kind in kinds}
        self.x_axis = self.received = None
        self.mode = "normal"
        self.current_spectrometer = None

        self.plot = FrameView("Spectrum", totals=False)
        self.spectrometer_controller = SpectrometerControl(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(FrameCanvas(self.plot))
        splitter.addWidget(self.spectrometer_controller)
        QVBoxLayout(self).addWidget(splitter)

        client.livedata.connect(self.on_client_livedata)
        client.connected.connect(self.on_client_connected)
        client.cache.connect(self.on_client_cache)

    def on_client_connected(self):
        self.client.tell("eventunmask", ["livedata"])
        combo = self.spectrometer_controller.detector_combo
        combo.clear()
        combo.addItems(SPECTROMETERS)
        name = self.current_spectrometer
        self.select_spectrometer(name if name in SPECTROMETERS else SPECTROMETERS[0])

    def select_spectrometer(self, name):
        self.current_spectrometer = name
        wavelengths = self._eval(f"{name}._wavelengths")
        if wavelengths is None:
            return
        self.x_axis = Axis("wavelength", spectrum_array(wavelengths))
        for kind, attr in (
            ("normal", "_spectrum_array"),
            ("lightbackground", "_light_array"),
            ("darkbackground", "_dark_array"),
        ):
            self.arrays[kind] = spectrum_array(self._eval(f"{name}.{attr}"))
        units = self._eval(f"{name}.acquireunits")
        if units:
            self.spectrometer_controller.set_integration_time_units(units)
        self.spectrometer_controller.clear_normalisation_checkboxes()
        self.draw("normal")

    def _eval(self, expression):
        try:
            return self.client.eval(expression)
        except Exception as err:
            self.log.warning("%s: %s", expression, err)
            return None

    def on_client_cache(self, data):
        _, key, _, value = data
        device = self.spectrometer_controller.selected_device
        if not device or not key.startswith(f"{device}/"):
            return
        try:
            decoded = cache_load(value) if value else None
        except ValueError:
            decoded = None
        self.spectrometer_controller.handle_cache_key(key, decoded)

    def on_client_livedata(self, params, blobs):
        if params.get("det") != self.current_spectrometer:
            return
        try:
            _name, frame = next(frames(params, blobs))
        except (ValueError, KeyError, IndexError, TypeError, StopIteration) as err:
            self.log.warning("unreadable spectrometer data: %s", err)
            return
        if frame.data.ndim != 1:
            self.log.warning("Expected 1D spectrometer livedata")
            return
        kind = params["datadescs"][0].get("array_type")
        if kind in self.arrays:
            self.arrays[kind] = frame.data
            self.received = time.time()
            self.x_axis = axis(frame, frame.dims[0])
            if kind in REDRAWN_BY[self.mode]:
                self.draw(self.mode)

    def start_acquisition(self):
        self.call("prepare()")
        self.call("doAcquire()")

    def call(self, method):
        self.exec_command(f"{self.current_spectrometer}.{method}")

    def exec_command(self, command):
        self.client.tell("exec", command)

    def draw(self, mode):
        self.mode = mode
        if (x := self.x_axis) is None:
            return
        spectrum, light, dark = self.arrays.values()
        # The plot stays empty unless the arrays of the mode match the axis.
        if any(len(self.arrays[kind]) != len(x.values) for kind in REDRAWN_BY[mode]):
            x, data = Axis(x.dim, x.values[:0], x.unit), []
        elif mode == "subtraction":
            data = light - spectrum  # The sign is flipped on purpose.
        elif mode == "absorbance":
            with np.errstate(divide="ignore", invalid="ignore"):
                data = (light - dark) / (spectrum - dark)
                data = np.where(data > 0, np.log10(data), data)
        else:
            data = self.arrays[mode]
        unit = "" if mode == "absorbance" else "ADC counts"
        meta = {"label": "absorbance" if mode == "absorbance" else "intensity"}
        frame = curve_frame(x.dim, unit, x.values, data, x.unit, title=mode, meta=meta)
        self.plot.show_frame(frame, self.received)

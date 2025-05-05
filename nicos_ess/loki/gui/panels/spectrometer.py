import math
from enum import Enum

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.livewidget import DATATYPES
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
from nicos_ess.gui.panels.live_pyqt import process_axis_labels, process_data_arrays
from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView


class Mode(Enum):
    NORMAL = 0
    LIGHT_BACKGROUND = 1
    DARK_BACKGROUND = 2
    LIGHT_SUBTRACTION = 3
    ABSORBANCE = 4


class SpectrometerControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.parent = parent
        self.selected_device = None
        self.fields = []
        self.normalisation_checkboxes = set()

        self.init_ui()

        self.normalisation_checkboxes = {
            self.calculate_absorbance,
            self.subtract_light_background,
            self.display_light_backgrd,
            self.display_dark_backgrd,
        }

    def init_ui(self):
        layout = QVBoxLayout()

        settings_group = self.create_settings_group()
        layout.addWidget(settings_group)

        normal_group = self.create_normalisation_group()
        layout.addWidget(normal_group)

        acq_layout = self.create_acquisition_control()
        layout.addLayout(acq_layout)

        norm_acq_layout = self.create_normalisation_acquisition_control()
        layout.addLayout(norm_acq_layout)

        self.setLayout(layout)

    def create_settings_group(self):
        settings_group = QGroupBox("Settings")
        settings_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        settings_layout = QGridLayout()
        settings_layout.setContentsMargins(5, 5, 5, 5)
        settings_layout.setHorizontalSpacing(5)
        settings_layout.setVerticalSpacing(10)

        spectrometer_lbl = QLabel("Spectrometer:")
        spectrometer_widget = self.create_detector_combo()
        settings_layout.addWidget(spectrometer_lbl, 0, 0)
        settings_layout.addWidget(spectrometer_widget, 0, 1)

        acquisition_mode_lbl = QLabel("Acquisition Mode:")
        acquisition_mode_widget = self.create_acq_mode_combo()
        settings_layout.addWidget(acquisition_mode_lbl, 1, 0)
        settings_layout.addWidget(acquisition_mode_widget, 1, 1)

        self.integration_time_lbl = QLabel()
        self.set_integration_time_units("ms")
        integration_time_widget = self.create_integration_time_field()
        settings_layout.addWidget(self.integration_time_lbl, 2, 0)
        settings_layout.addWidget(integration_time_widget, 2, 1)
        settings_layout.addWidget(integration_time_widget.readback, 2, 2)
        self.fields.append((integration_time_widget, integration_time_widget.readback))

        boxcar_width_lbl = QLabel("Boxcar Width:")
        boxcar_width_widget = self.create_boxcar_width_field()
        settings_layout.addWidget(boxcar_width_lbl, 3, 0)
        settings_layout.addWidget(boxcar_width_widget, 3, 1)
        settings_layout.addWidget(boxcar_width_widget.readback, 3, 2)
        self.fields.append((boxcar_width_widget, boxcar_width_widget.readback))

        settings_layout.setRowStretch(5, 1)
        settings_layout.setColumnStretch(0, 1)
        settings_layout.setColumnStretch(1, 0)
        settings_layout.setColumnStretch(2, 0)

        settings_group.setLayout(settings_layout)
        return settings_group

    def set_integration_time_units(self, units):
        self.integration_time_lbl.setText(f"Integration Time ({units}):")

    def create_acquisition_control(self):
        def create_button(name, text, callback, color=None):
            button = QPushButton(text)
            button.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
            )
            if color:
                button.setStyleSheet(f"background-color: {color}")
            button.clicked.connect(callback)
            setattr(self, name, button)
            return button

        layout = QHBoxLayout()
        layout.addWidget(
            create_button(
                "start_acq_button",
                "Start Acquisition",
                self.parent.start_acquisition,
                "rgba(0, 200, 0, 75%)",
            )
        )
        layout.addWidget(
            create_button(
                "stop_acq_button", "Stop Acquisition", self.parent.stop_acquisition
            )
        )
        return layout

    def create_normalisation_acquisition_control(self):
        def create_button(name, text, callback, color=None):
            button = QPushButton(text)
            button.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
            )
            if color:
                button.setStyleSheet(f"background-color: {color}")
            button.clicked.connect(callback)
            setattr(self, name, button)
            return button

        layout = QHBoxLayout()
        layout.addWidget(
            create_button(
                "save_light_acq_button",
                "Save As Light Background",
                self.parent.save_light_background,
                "rgba(200, 0, 0, 25%)",
            )
        )
        layout.addWidget(
            create_button(
                "save_dark_acq_button",
                "Save As Dark Background",
                self.parent.save_dark_background,
                "rgba(0, 0, 200, 25%)",
            )
        )
        return layout

    def create_normalisation_group(self):
        normal_group = QGroupBox("Normalisation")
        normal_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        normal_layout = QGridLayout()
        normal_layout.setContentsMargins(5, 5, 5, 5)
        normal_layout.setHorizontalSpacing(5)
        normal_layout.setVerticalSpacing(10)

        self.display_light_backgrd = QCheckBox("Display Light Background")
        self.display_light_backgrd.clicked.connect(self._on_display_light_background)
        normal_layout.addWidget(self.display_light_backgrd, 0, 0)

        self.display_dark_backgrd = QCheckBox("Display Dark Background")
        self.display_dark_backgrd.clicked.connect(self._on_display_dark_background)
        normal_layout.addWidget(self.display_dark_backgrd, 1, 0)

        self.subtract_light_background = QCheckBox("Subtract Light Background")
        self.subtract_light_background.clicked.connect(
            self._on_subtract_light_background
        )
        normal_layout.addWidget(self.subtract_light_background, 2, 0)

        self.calculate_absorbance = QCheckBox("Calculate Absorbance")
        self.calculate_absorbance.clicked.connect(self._on_calculate_absorbance)
        normal_layout.addWidget(self.calculate_absorbance, 3, 0)

        self.light_backgrd_valid_label = QLabel(
            "Light background invalid - please acquire a new one"
        )
        self.light_backgrd_valid_label.setStyleSheet("color: red")
        self.light_backgrd_valid_label.setVisible(False)
        normal_layout.addWidget(self.light_backgrd_valid_label, 4, 0)

        self.dark_backgrd_valid_label = QLabel(
            "Dark background invalid - please acquire a new one"
        )
        self.dark_backgrd_valid_label.setStyleSheet("color: red")
        self.dark_backgrd_valid_label.setVisible(False)
        normal_layout.addWidget(self.dark_backgrd_valid_label, 5, 0)

        normal_layout.setRowStretch(6, 1)
        normal_group.setLayout(normal_layout)

        return normal_group

    def create_detector_combo(self):
        self.detector_combo = self.create_combo_box([], self.on_detector_changed)
        return self.detector_combo

    def create_acq_mode_combo(self):
        self.acq_mode_combo = self.create_combo_box(
            ["single", "continuous"], self.on_acq_mode_changed
        )
        self.on_acq_mode_changed(0)
        return self.acq_mode_combo

    def create_integration_time_field(self):
        self.integration_time = self.create_line_edit(
            "Set Value", self.on_integration_time_changed
        )
        return self.integration_time

    def create_boxcar_width_field(self):
        self.boxcar_width = self.create_line_edit(
            "Set Value", self.on_boxcar_width_changed
        )
        return self.boxcar_width

    def create_combo_box(self, items, callback):
        combo_box = QComboBox()
        combo_box.setMinimumContentsLength(1)
        combo_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo_box.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
        )
        combo_box.addItems(items)
        combo_box.currentIndexChanged.connect(callback)
        return combo_box

    def create_line_edit(self, placeholder, callback):
        line_edit = QLineEdit()
        line_edit.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
        )
        line_edit.setPlaceholderText(placeholder)
        line_edit.returnPressed.connect(callback)
        line_edit.readback = QLabel("Readback Value")
        return line_edit

    def on_detector_changed(self, index):
        self.selected_device = self.detector_combo.currentText()
        if not self.selected_device:
            return
        self.update_readback_values()
        for field, field_readback in self.fields:
            if isinstance(field, QLineEdit):
                field.setText(field_readback.text())
        self.parent.select_spectrometer(self.selected_device)

    def _all_unchecked(self):
        return not any([cb.isChecked() for cb in self.normalisation_checkboxes])

    def _uncheck_others(self, current_checkbox):
        for cb in self.normalisation_checkboxes.difference({current_checkbox}):
            cb.setChecked(False)

    def _switch_plot(self, checkbox, show_func):
        self._uncheck_others(checkbox)
        if self._all_unchecked():
            self.parent.show_raw_spectrum()
            return
        show_func()

    def _on_subtract_light_background(self):
        self._switch_plot(
            self.subtract_light_background, self.parent.show_background_subtraction
        )

    def _on_calculate_absorbance(self):
        self._switch_plot(
            self.calculate_absorbance, self.parent.show_dark_background_correction
        )

    def _on_display_light_background(self):
        self._switch_plot(self.display_light_backgrd, self.parent.show_light_background)

    def _on_display_dark_background(self):
        self._switch_plot(self.display_dark_backgrd, self.parent.show_dark_background)

    def update_readback_values(self):
        pass  # code below removed because needs fix: JIRA ECDC-4668
        # if not self.selected_device:
        #     return
        #
        # try:
        #     self.parent.client.eval(f"{self.selected_device}.pollParams()")
        # except NameError:
        #     return

        param_info = self.parent.client.getDeviceParams(self.selected_device)
        if not param_info:
            return

        self._update_text_fields(param_info)
        self._update_start_acq_button_style(param_info.get("status", (None, None))[1])
        self._highlight_differing_readback_values()
        self._update_warnings(param_info)

    def _update_warnings(self, param_info):
        if param_info["darkvalid"]:
            self.dark_backgrd_valid_label.setVisible(False)
        else:
            self.dark_backgrd_valid_label.setVisible(True)

        if param_info["lightvalid"]:
            self.light_backgrd_valid_label.setVisible(False)
        else:
            self.light_backgrd_valid_label.setVisible(True)

    def _update_text_fields(self, param_info):
        self.integration_time.readback.setText(str(param_info.get("integrationtime")))
        self.boxcar_width.readback.setText(str(param_info.get("boxcarwidth")))
        self.acq_mode_combo.setCurrentText(str(param_info.get("acquiremode")))

    def _update_start_acq_button_style(self, status):
        if status == "":
            return
        elif "Done" in status or "Idle" in status:
            self.start_acq_button.setStyleSheet(
                "background-color: rgba(0, 200, 0, 75%)"
            )
        elif "Acquiring" in status:
            self.start_acq_button.setStyleSheet(
                "background-color: rgba(0, 0, 255, 60%)"
            )
        else:
            self.start_acq_button.setStyleSheet(
                "background-color: rgba(255, 0, 0, 60%)"
            )

    def _highlight_differing_readback_values(self):
        for input_field, readback_field in self.fields:
            if input_field.text() == "":
                continue

            if float(input_field.text()) != float(readback_field.text()):
                readback_field.setStyleSheet("background-color: rgba(255, 0, 0, 75%)")
            else:
                readback_field.setStyleSheet(
                    "background-color: rgba(255, 255, 255, 0%)"
                )

    def _exec_command_if_device_selected(self, command_template, *args):
        if not self.selected_device:
            return
        command = command_template % ((self.selected_device,) + args)
        self.parent.exec_command(command)

    # TODO: move these to the panel
    def on_acq_mode_changed(self, index):
        mode = str(self.acq_mode_combo.currentText())
        self._exec_command_if_device_selected('%s.acquiremode = "%s"', mode)

    def on_integration_time_changed(self):
        integration_time = float(self.integration_time.text())
        self._exec_command_if_device_selected(
            "%s.integrationtime = %f", integration_time
        )

    def on_boxcar_width_changed(self):
        boxcar_width = float(self.boxcar_width.text())
        self._exec_command_if_device_selected("%s.boxcarwidth = %f", boxcar_width)

    def clear_normalisation_checkboxes(self):
        for checkbox in self.normalisation_checkboxes:
            checkbox.setChecked(False)


class SpectrometerPanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self.spectrum = np.array([])
        self.light_background = np.array([])
        self.dark_background = np.array([])
        self.x_axis = None
        self.mode = Mode.NORMAL
        self.spectrometers = []
        self.current_spectrometer = None

        self.build_ui()
        self.setup_connections()

    def setup_connections(self):
        self.client.livedata.connect(self.on_client_livedata)
        self.client.connected.connect(self.on_client_connected)
        self.client.cache.connect(self.on_client_cache)

    def build_ui(self):
        layout = QVBoxLayout()

        left_layout = QVBoxLayout()
        self.autoscale_btn = QPushButton("Autoscale")
        self.autoscale_btn.clicked.connect(self.on_autoscale)
        left_layout.addWidget(self.autoscale_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.plotwidget_1d = LineView(parent=self)
        self.plotwidget_1d.mode_checkbox.setVisible(False)
        self.plotwidget_1d.log_checkbox.setVisible(False)
        self.plotwidget_1d.clear_button.setVisible(False)
        left_layout.addWidget(self.plotwidget_1d)
        left_container = QWidget()
        left_container.setLayout(left_layout)

        self.spectrometer_controller = SpectrometerControl(self)

        view_splitter = QSplitter(Qt.Orientation.Horizontal)
        view_splitter.addWidget(left_container)
        view_splitter.addWidget(self.spectrometer_controller)

        layout.addWidget(view_splitter)
        self.setLayout(layout)

    def on_autoscale(self):
        self.plotwidget_1d.autoscale(axis="xy")

    def on_client_connected(self):
        self.client.tell("eventunmask", ["livedata"])
        self.spectrometers = self._get_spectrometer_names()
        self.spectrometer_controller.detector_combo.clear()
        self.spectrometer_controller.detector_combo.addItems(self.spectrometers)
        if not self.spectrometers:
            self.spectrometer_controller.clear_normalisation_checkboxes()
            self.clear_spectrums()
            self.show_raw_spectrum()
        elif self.current_spectrometer in self.spectrometers:
            self.select_spectrometer(self.current_spectrometer)
        else:
            self.select_spectrometer(self.spectrometers[0])

    def select_spectrometer(self, name):
        self.current_spectrometer = name

        raw_x_axis = self._eval(
            f"{self.current_spectrometer}._wavelengths",
            f"No wavelengths found for {self.current_spectrometer}",
        )
        if raw_x_axis is None:
            return
        self.x_axis = {"x": np.array(raw_x_axis)}

        spectrum = self._eval(
            f"{self.current_spectrometer}._spectrum_array",
            f"No spectrum found for {self.current_spectrometer}",
        )
        self.spectrum = np.array(spectrum) if spectrum is not None else np.array([])

        background = self._eval(
            f"{self.current_spectrometer}._light_array",
            f"No light spectrum found for {self.current_spectrometer}",
        )
        self.light_background = (
            np.array(background) if background is not None else np.array([])
        )

        dark = self._eval(
            f"{self.current_spectrometer}._dark_array",
            f"No dark spectrum found for {self.current_spectrometer}",
        )
        self.dark_background = np.array(dark) if dark is not None else np.array([])

        units = self._eval(
            f"{self.current_spectrometer}.acquireunits",
            f"No units found for {self.current_spectrometer}",
        )
        if units:
            self.spectrometer_controller.set_integration_time_units(units)
        self.spectrometer_controller.clear_normalisation_checkboxes()
        self.show_raw_spectrum()

    def _eval(self, command_str, message=None):
        try:
            return self.client.eval(command_str)
        except AttributeError:
            self.log.warning(message)
            return None
        except Exception as e:
            self.log.warning(e)
            return None

    def clear_spectrums(self):
        self.spectrum = np.array([])
        self.light_background = np.array([])
        self.dark_background = np.array([])

    def on_client_cache(self, data):
        self.spectrometer_controller.update_readback_values()

    def on_client_livedata(self, params, blobs):
        if params["det"] != self.current_spectrometer:
            return

        descriptions = params["datadescs"]

        normalized_type = self.normalize_type(descriptions[0]["dtype"])
        labels, _ = process_axis_labels(descriptions[0], blobs[1:])
        data = np.frombuffer(blobs[0], normalized_type)

        # pylint: disable=len-as-condition
        if len(data):
            arrays = process_data_arrays(
                0,
                params,
                np.frombuffer(data, descriptions[0]["dtype"]),
            )
            if arrays is None:
                return

            array_type = descriptions[0].get("array_type")

            if array_type == "normal":
                self.spectrum = arrays[0]
                self.x_axis = labels
            elif array_type == "lightbackground":
                self.light_background = arrays[0]
                self.x_axis = labels
            elif array_type == "darkbackground":
                self.dark_background = arrays[0]
                self.x_axis = labels
            else:
                return
            self.update_plot(array_type)

    def normalize_type(self, dtype):
        normalized_type = np.dtype(dtype).str
        if normalized_type not in DATATYPES:
            self.log.warning("Unsupported live data format: %s", normalized_type)
            return
        return normalized_type

    def _get_spectrometer_names(self):
        # TODO: get the names from the server
        return ["hr4", "qepro"]

    def start_acquisition(self):
        # Needed?
        self.exec_command(f"{self.current_spectrometer}.prepare()")
        # Don't set presets, run with config from here
        self.exec_command(f"{self.current_spectrometer}.doAcquire()")

    def stop_acquisition(self):
        self.exec_command(f"{self.current_spectrometer}.stop()")

    def save_light_background(self):
        self.exec_command(f"{self.current_spectrometer}.save_light_background()")

    def save_dark_background(self):
        self.exec_command(f"{self.current_spectrometer}.save_dark_background()")

    def exec_command(self, command):
        self.client.tell("exec", command)

    def show_light_background(self):
        self.mode = Mode.LIGHT_BACKGROUND
        self._update_plot(self.light_background, self.x_axis)

    def show_dark_background(self):
        self.mode = Mode.DARK_BACKGROUND
        self._update_plot(self.dark_background, self.x_axis)

    def show_raw_spectrum(self):
        self.mode = Mode.NORMAL
        self._update_plot(self.spectrum, self.x_axis)

    def show_background_subtraction(self):
        self.mode = Mode.LIGHT_SUBTRACTION
        # Flip the image
        data = np.multiply(self.spectrum - self.light_background, -1)
        self._update_plot(data, self.x_axis)

    def show_dark_background_correction(self):
        self.mode = Mode.ABSORBANCE
        calc_data = (self.light_background - self.dark_background) / (
            self.spectrum - self.dark_background
        )

        for i, d in enumerate(calc_data):
            try:
                calc_data[i] = math.log10(d)
            except ValueError:
                pass

        self._update_plot(calc_data, self.x_axis)

    def _update_plot(self, data, x_axis):
        self.plotwidget_1d.set_data([data], x_axis)

    def update_plot(self, array_type):
        if array_type == "normal" and self.mode == Mode.NORMAL:
            self.show_raw_spectrum()
        elif array_type == "lightbackground" and self.mode == Mode.LIGHT_BACKGROUND:
            self.show_light_background()
        elif array_type == "darkbackground" and self.mode == Mode.DARK_BACKGROUND:
            self.show_dark_background()
        elif (
            array_type in ["normal", "lightbackground"]
            and self.mode == Mode.LIGHT_SUBTRACTION
        ):
            self.show_background_subtraction()
        elif self.mode == Mode.ABSORBANCE:
            self.show_dark_background_correction()

# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import numpy as np

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
    QVBoxLayout,
    QWidget,
    QTimer,
)

from nicos_ess.gui.panels.live_pyqt import (
    DEFAULT_TAB_WIDGET_MAX_WIDTH,
    DEFAULT_TAB_WIDGET_MIN_WIDTH,
    MultiLiveDataPanel as DefaultMultiLiveDataPanel,
    Preview,
    layout_iterator,
)

READBACK_UPDATE_INTERVAL = 1000


class ADControl(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.parent = parent
        self.selected_device = None
        self.last_acquisition_time = 0.0
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(READBACK_UPDATE_INTERVAL)
        self.update_timer.setSingleShot(True)
        self.fields = []

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout()

        settings_group = self.create_settings_group()
        layout.addWidget(settings_group)

        self.normal_group = self.create_normalisation_group()
        self.acq_layout = self.create_acquisition_control()

        self.setLayout(layout)

    def setup_connections(self):
        self.parent.plotwidget.image_item.sigImageChanged.connect(self._on_correction)

    def create_settings_group(self):
        settings_group = QGroupBox("Settings")
        settings_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        settings_layout = QGridLayout()
        settings_layout.setContentsMargins(5, 5, 5, 5)
        settings_layout.setHorizontalSpacing(5)
        settings_layout.setVerticalSpacing(10)

        disp_fields = [
            ("Detector:", self.create_detector_combo, 0),
            ("Acquisition Time [s]:", self.create_acquisition_time_field, 1),
            (
                "Acquisition Period [s]:",
                self.create_acquisition_period_field,
                2,
            ),
            ("Coarse Threshold:", self.create_threshold_coarse_field, 3),
            ("Fine Threshold:", self.create_threshold_fine_field, 4),
        ]

        for label_text, field_method, row in disp_fields:
            label = QLabel(label_text)
            field_widget = field_method()
            settings_layout.addWidget(label, row, 0)
            settings_layout.addWidget(field_widget, row, 1)

            if hasattr(field_widget, "readback"):
                settings_layout.addWidget(field_widget.readback, row, 2)
                self.fields.append((field_widget, field_widget.readback))

        settings_layout.setRowStretch(len(disp_fields) + 1, 1)
        settings_layout.setColumnStretch(0, 1)
        settings_layout.setColumnStretch(1, 0)
        settings_layout.setColumnStretch(2, 0)

        settings_group.setLayout(settings_layout)
        return settings_group

    def create_normalisation_group(self):
        normal_group = QGroupBox()
        normal_group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        normal_layout = QGridLayout()
        normal_layout.setContentsMargins(5, 5, 5, 5)
        normal_layout.setHorizontalSpacing(5)
        normal_layout.setVerticalSpacing(10)

        self.store_flat_field_button = QPushButton("Store Flat Field")
        self.store_flat_field_button.clicked.connect(self._store_flat_field)
        normal_layout.addWidget(self.store_flat_field_button, 0, 0)

        self.flat_field_acquisition_time_label = QLabel("Acquisition Time")
        self.flat_field_acquisition_time_label.readback = QLabel("None")
        normal_layout.addWidget(self.flat_field_acquisition_time_label, 1, 0)
        normal_layout.addWidget(self.flat_field_acquisition_time_label.readback, 1, 1)

        self.flat_field_correction_cb = QCheckBox("Flat Field Correction")
        self.flat_field_correction_cb.clicked.connect(self._on_correction)
        self.display_flat_field_cb = QCheckBox("Display Flat Field")
        self.display_flat_field_cb.clicked.connect(self._on_preview_flat_field)
        normal_layout.addWidget(self.flat_field_correction_cb, 2, 0)
        normal_layout.addWidget(self.display_flat_field_cb, 2, 1)

        self.store_background_button = QPushButton("Store Background")
        self.store_background_button.clicked.connect(self._store_background)
        normal_layout.addWidget(self.store_background_button, 3, 0)

        self.background_acquisition_time_label = QLabel("Acquisition Time")
        self.background_acquisition_time_label.readback = QLabel("None")
        normal_layout.addWidget(self.background_acquisition_time_label, 4, 0)
        normal_layout.addWidget(self.background_acquisition_time_label.readback, 4, 1)

        self.background_subtraction_cb = QCheckBox("Background Subtraction")
        self.background_subtraction_cb.clicked.connect(self._on_correction)
        self.display_background_cb = QCheckBox("Display Background")
        self.display_background_cb.clicked.connect(self._on_preview_background)
        normal_layout.addWidget(self.background_subtraction_cb, 5, 0)
        normal_layout.addWidget(self.display_background_cb, 5, 1)

        normal_layout.setRowStretch(6, 1)

        normal_group.setLayout(normal_layout)
        return normal_group

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
                self.on_acq_start,
                "rgba(0, 200, 0, 75%)",
            )
        )
        layout.addWidget(
            create_button("stop_acq_button", "Stop Acquisition", self.on_acq_stop)
        )
        return layout

    def create_detector_combo(self):
        self.detector_combo = self.create_combo_box(
            ["det666", "det999"], self.on_detector_changed
        )
        return self.detector_combo

    def create_acquisition_time_field(self):
        self.acquisition_time = self.create_line_edit(
            "Set Value", self.on_acquisition_time_changed
        )
        return self.acquisition_time

    def create_acquisition_period_field(self):
        self.acquisition_period = self.create_line_edit(
            "Set Value", self.on_acquisition_period_changed
        )
        return self.acquisition_period

    def create_threshold_coarse_field(self):
        self.threshold_coarse = self.create_line_edit(
            "Set Value", self.on_threshold_coarse_changed
        )
        return self.threshold_coarse

    def create_threshold_fine_field(self):
        self.threshold_fine = self.create_line_edit(
            "Set Value", self.on_threshold_fine_changed
        )
        return self.threshold_fine

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

    def _get_image(self):
        image = self.parent.plotwidget.raw_image
        acq_time = self.last_acquisition_time
        if image is None:
            print("No image data to store.")
            return None, None
        return image, acq_time

    def _store_background(self):
        self.background_image, self.background_acq_time = self._get_image()
        self.background_acquisition_time_label.readback.setText(
            str(self.background_acq_time)
        )

    def _store_flat_field(self):
        self.flat_field_image, self.flat_field_acq_time = self._get_image()
        self.flat_field_acquisition_time_label.readback.setText(
            str(self.flat_field_acq_time)
        )

    def _on_preview_image(self, state, display_other_cb, image, other_image):
        self.parent.plotwidget.image_item.blockSignals(True)
        if state:
            display_other_cb.setChecked(False)
            self.parent.plotwidget.image_view_controller.disp_image = image
            self.parent.plotwidget.set_image(image, autoLevels=False, raw_update=False)
        else:
            if not display_other_cb.isChecked():
                self.parent.plotwidget.image_view_controller.disp_image = None
                self.parent.plotwidget.set_image(
                    other_image, autoLevels=False, raw_update=False
                )
        self.parent.plotwidget.image_item.blockSignals(False)
        self.update_blocked_signals()

    def _turn_off_correction(self):
        self.background_subtraction_cb.setChecked(False)
        self.flat_field_correction_cb.setChecked(False)

    def _turn_off_preview(self):
        self.display_background_cb.setChecked(False)
        self.display_flat_field_cb.setChecked(False)

    def _on_preview_background(self, state):
        self._turn_off_correction()
        self._on_preview_image(
            state,
            self.display_flat_field_cb,
            self.background_image,
            self.parent.plotwidget.raw_image,
        )

    def _on_preview_flat_field(self, state):
        self._turn_off_correction()
        self._on_preview_image(
            state,
            self.display_background_cb,
            self.flat_field_image,
            self.parent.plotwidget.raw_image,
        )

    def _apply_corrections(self, image):
        corrected_image = np.copy(image)

        if self.background_subtraction_cb.isChecked():
            corrected_image -= self.background_image

        if self.flat_field_correction_cb.isChecked():
            diff = self.flat_field_image - (
                self.background_image
                if self.background_subtraction_cb.isChecked()
                else 0
            )
            non_zero_diff = np.where(diff != 0, diff, 1)
            # corrected_image *= np.mean(diff) / non_zero_diff
            corrected_image /= non_zero_diff

        return corrected_image

    def _on_correction(self):
        self.parent.plotwidget.image_item.blockSignals(True)
        self._turn_off_preview()
        if not (
            self.flat_field_correction_cb.isChecked()
            or self.background_subtraction_cb.isChecked()
        ):
            self.parent.plotwidget.image_view_controller.disp_image = None
            self.parent.plotwidget.update_image()
            self.parent.plotwidget.image_item.blockSignals(False)
            self.update_blocked_signals()
            return

        raw_image = self.parent.plotwidget.raw_image
        if raw_image is None:
            print("No image data to apply correction.")
            self.parent.plotwidget.image_view_controller.disp_image = None
            self.parent.plotwidget.image_item.blockSignals(False)
            return

        corrected_image = self._apply_corrections(raw_image)
        self.parent.plotwidget.image_view_controller.disp_image = corrected_image
        self.parent.plotwidget.set_image(
            corrected_image, autoLevels=False, raw_update=False
        )
        self.parent.plotwidget.image_item.blockSignals(False)
        self.update_blocked_signals()

    def update_blocked_signals(self):
        self.parent.plotwidget.roi_changed()
        self.parent.plotwidget.line_roi_changed()
        self.parent.plotwidget.crosshair_roi_changed()
        self.parent.plotwidget.update_trace()
        self.parent.plotwidget.settings_histogram.item.imageChanged()

    def on_detector_changed(self, index):
        self.selected_device = self.detector_combo.currentText()
        if not self.selected_device:
            return
        self.update_readback_values()
        for field, field_readback in self.fields:
            if isinstance(field, QLineEdit):
                field.setText(field_readback.text())

    def update_readback_values(self):
        if self.update_timer.isActive():
            return

        if not self.selected_device:
            return

        self.parent.eval_command("%s.pollParams()" % self.selected_device, None)
        param_info = self.parent.client.getDeviceParams(self.selected_device)
        if not param_info:
            return

        self._update_text_fields(param_info)
        self._update_start_acq_button_style(param_info.get("status", (None, None))[1])
        self._highlight_differing_readback_values()
        self.update_timer.start()

    def _update_text_fields(self, param_info):
        self.acquisition_time.readback.setText(str(param_info.get("acquiretime")))
        self.acquisition_period.readback.setText(str(param_info.get("acquireperiod")))
        self.threshold_coarse.readback.setText(str(param_info.get("thresholdcoarse")))
        self.threshold_fine.readback.setText(str(param_info.get("thresholdfine")))

    def _update_start_acq_button_style(self, status):
        if status == "":  # pylint: disable=compare-to-empty-string
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
            if input_field.text() == "":  # pylint: disable=compare-to-empty-string
                continue

            if float(input_field.text()) != float(readback_field.text()):
                readback_field.setStyleSheet("background-color: rgba(255, 0, 0, 75%)")
            else:
                readback_field.setStyleSheet(
                    "background-color: rgba(255, 255, 255, 0%)"
                )

    def _eval_command_if_device_selected(self, command_template, *args):
        if not self.selected_device:
            return
        command = command_template % ((self.selected_device,) + args)
        self.parent.eval_command(command)

    def on_acq_start(self):
        # self._turn_off_correction()
        self._turn_off_preview()
        self.parent.plotwidget.image_view_controller.disp_image = None
        self.last_acquisition_time = float(self.acquisition_time.readback.text())
        self._eval_command_if_device_selected("%s.prepare()")
        # Don't set presets, run with config from here
        self._eval_command_if_device_selected("%s.doAcquire()")

    def on_acq_stop(self):
        self._eval_command_if_device_selected("%s.stop()")

    def on_acquisition_time_changed(self):
        acquisition_time = float(self.acquisition_time.text())
        self._eval_command_if_device_selected(
            "%s.doWriteAcquiretime(%f)", acquisition_time
        )
        self._eval_command_if_device_selected(
            '%s._cache.put(%s, "%s", %f)',
            self.selected_device,
            "acquiretime",
            acquisition_time,
        )

    def on_acquisition_period_changed(self):
        acquisition_period = float(self.acquisition_period.text())
        self._eval_command_if_device_selected(
            "%s.doWriteAcquireperiod(%f)", acquisition_period
        )
        self._eval_command_if_device_selected(
            '%s._cache.put(%s, "%s", %f)',
            self.selected_device,
            "acquireperiod",
            acquisition_period,
        )

    def on_threshold_coarse_changed(self):
        threshold_coarse = int(self.threshold_coarse.text())
        self._eval_command_if_device_selected(
            "%s.doWriteThresholdcoarse(%d)", threshold_coarse
        )
        self._eval_command_if_device_selected(
            '%s._cache.put(%s, "%s", %d)',
            self.selected_device,
            "thresholdcoarse",
            threshold_coarse,
        )

    def on_threshold_fine_changed(self):
        threshold_fine = int(self.threshold_fine.text())
        self._eval_command_if_device_selected(
            "%s.doWriteThresholdfine(%d)", threshold_fine
        )
        self._eval_command_if_device_selected(
            '%s._cache.put(%s, "%s", %d)',
            self.selected_device,
            "thresholdfine",
            threshold_fine,
        )


class MultiLiveDataPanel(DefaultMultiLiveDataPanel):
    def __init__(self, parent, client, options):
        DefaultMultiLiveDataPanel.__init__(self, parent, client, options)

        self.ad_controller = ADControl(self)
        self.tab_widget.addTab(self.ad_controller, "Detector Control")
        self.tab_widget.addTab(self.plotwidget.image_view_controller, "View Settings")
        self.tab_widget.addTab(self.ad_controller.normal_group, "Normalisation")
        self.tab_widget.addTab(self.scroll, "Previews")
        self.tab_layout.addLayout(self.ad_controller.acq_layout)

        self.connect_camera_controller_signals()

    def connect_camera_controller_signals(self):
        self.ad_controller.detector_combo.currentTextChanged.connect(
            self.on_ad_selected
        )

    def on_ad_selected(self, ad_name):
        if ad_name not in self._previews.keys():
            return
        self._change_detector_to_display(ad_name)

    def _cleanup_existing_previews(self):
        for item in layout_iterator(self.scroll_content.layout()):
            item.widget().deleteLater()
            del item
        self.ad_controller.detector_combo.clear()
        self._previews.clear()
        self._detectors.clear()

    def add_previews_to_layout(self, previews, det_name):
        for preview in previews:
            name = preview.widget().name
            self._previews[name] = Preview(name, det_name, preview)
            self._detectors[det_name].add_preview(name)
            if "collector" in det_name.lower():
                self.ad_controller.detector_combo.addItem(name)
            preview.widget().clicked.connect(self.on_preview_clicked)
            self.scroll_content.layout().addWidget(preview)

    def set_tab_widget_width(self):
        self.tab_widget.setMaximumWidth(DEFAULT_TAB_WIDGET_MAX_WIDTH)
        self.tab_widget.setMinimumWidth(DEFAULT_TAB_WIDGET_MIN_WIDTH)

    def on_client_cache(self, data):
        _, key, _, _ = data
        if (
            self.ad_controller.selected_device
            and self.ad_controller.selected_device in key
        ):
            self.ad_controller.update_readback_values()
        self.scroll.setMaximumWidth(self.ad_controller.size().width())
        if key == "exp/detlist":
            self.ad_controller.detector_combo.clear()
            self._cleanup_existing_previews()

#  -*- coding: utf-8 -*-
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
#
#   Stefanos Athanasopoulos <stefanos.athanasopoulos@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
"""ODIN Metrology System Panel."""

import csv

from collections import OrderedDict, namedtuple

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QHeaderView, QTableView, pyqtSlot, QFileDialog, Qt
from nicos.utils import findResource

from nicos_ess.gui.panels.panel import PanelBase
from nicos_ess.loki.gui.sample_holder_config import ReadOnlyDelegate
from nicos_ess.loki.gui.table_delegates import ComboBoxDelegate, CheckboxDelegate
from nicos_ess.loki.gui.table_helper import Clipboard, TableHelper
from nicos_ess.odin.gui.metrology_system_model import OdinMetrologySystemModel

COMPONENT_COLUMN_NAME = "Component"

COMPONENT_KEY = "component_name"

CHECKBOXES_COLUMN_NAME = "Checkboxes [temporary]"

CONFIRMED_DISTANCE = "confirmed_distance_from_sample"

SCANNED_DISTANCE_COLUMN_NAME = "Scanned distance from Sample - Beam axis [m]"

DISTANCE_FROM_SAMPLE = "distance_from_sample"

TABLE_QSS = "alternate-background-color: aliceblue;"

X_AXIS = "x"
Y_AXIS = "y"
Z_AXIS = "z"
ALPHA_ANGLE = "alpha"
BETA_ANGLE = "beta"
GAMMA_ANGLE = "gamma"

Column = namedtuple(
    "Column", ["header", "optional", "style", "can_bulk_update", "delegate"]
)


class MetrologySystemPanel(PanelBase):
    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/odin/gui/ui_files/metrology_system.ui"))
        self._dev_name = None
        self._dev_name_old = None
        self.parent_window = parent
        self.combo_delegate = ComboBoxDelegate()
        self.checkbox_delegate = CheckboxDelegate()

        self.columns = OrderedDict(
            {
                COMPONENT_KEY: Column(
                    COMPONENT_COLUMN_NAME,
                    False,
                    QHeaderView.ResizeMode.ResizeToContents,
                    True,
                    ReadOnlyDelegate(),
                ),
                DISTANCE_FROM_SAMPLE: Column(
                    SCANNED_DISTANCE_COLUMN_NAME,
                    False,
                    QHeaderView.ResizeMode.Stretch,
                    True,
                    ReadOnlyDelegate(),
                ),
                CHECKBOXES_COLUMN_NAME: Column(
                    CHECKBOXES_COLUMN_NAME,
                    False,
                    QHeaderView.ResizeMode.ResizeToContents,
                    True,
                    self.checkbox_delegate,
                ),
            }
        )
        self.columns_headers = list(self.columns.keys())
        self.lblScanWarn.setStyleSheet("color: red")
        self.lblScanWarn.setVisible(False)
        self.btnConfirm.setEnabled(False)
        self.lblConfirmTime.setVisible(True)
        self.lblConfirmTime.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._init_table_panel()
        self.view = None

        self.initialise_connection_status_listeners()
        self.client.setup.connect(self.on_client_setup)

    def _init_table_panel(self):
        headers = [column.header for column in self.columns.values()]
        mappings = {
            COMPONENT_COLUMN_NAME: COMPONENT_KEY,
            SCANNED_DISTANCE_COLUMN_NAME: DISTANCE_FROM_SAMPLE,
            CHECKBOXES_COLUMN_NAME: CHECKBOXES_COLUMN_NAME,
        }

        self.model = OdinMetrologySystemModel(headers, self.columns, mappings)
        self.tableView.setModel(self.model)
        self.tableView.setSelectionMode(QTableView.SelectionMode.ContiguousSelection)
        self.table_helper = TableHelper(self.tableView, self.model, Clipboard())

        for i, column in enumerate(self.columns.values()):
            if column.delegate:
                self.tableView.setItemDelegateForColumn(i, column.delegate)

        self.tableView.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        for i, column in enumerate(self.columns.values()):
            self.tableView.horizontalHeader().setSectionResizeMode(i, column.style)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setStyleSheet(TABLE_QSS)

    def sort_by_distance(self, components):
        sorted_components = sorted(components, key=lambda x: self.get_distance_value(x))
        return sorted_components

    def get_distance_value(self, component):
        distance = component.get(DISTANCE_FROM_SAMPLE)
        if distance != "Not detected":
            return abs(float(distance))
        else:
            return float("inf")

    def request_scan(self):
        extracted_data = self.exec_command(
            "component_tracking.read_metrology_system_messages()"
        )
        if not extracted_data:
            self.btnConfirm.setEnabled(False)
            self.lblScanWarn.setText("Could not retrieve positions!")
            self.lblScanWarn.setVisible(True)
            return
        print(extracted_data)
        sorted_data = self.sort_by_distance(extracted_data)
        self.model.raw_data = sorted_data
        self.lblScanWarn.setText("Scanned values are not confirmed!")
        self.lblScanWarn.setVisible(True)
        self.check_checkbox_status()
        self.btnConfirm.setEnabled(True)

    def check_checkbox_status(self):
        print(self.model.raw_data)

    def exec_command(self, command):
        return self.client.eval(command)

    @pyqtSlot()
    def on_btnScan_clicked(self):
        self.request_scan()

    @pyqtSlot()
    def on_btnConfirm_clicked(self):
        self.exec_command("component_tracking.confirm_components()")
        self.update_confirm_timestamp()
        self._reset_controls()

    @pyqtSlot()
    def on_btnCSV_clicked(self):
        self.export_as_csv()

    @pyqtSlot()
    def on_btnViewData_clicked(self):
        self.view_data()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self._find_device()
        self.lblConfirmTime.setVisible(True)
        self.setViewOnly(self.client.viewonly)

    def on_client_disconnected(self):
        self.model.raw_data = []
        self._disable_controls()
        PanelBase.on_client_disconnected(self)

    def _disable_controls(self):
        self.btnConfirm.setEnabled(False)
        self.btnScan.setEnabled(False)
        self.lblScanWarn.setVisible(False)
        self.btnCSV.setEnabled(False)
        self.btnViewData.setEnabled(False)
        self.lblConfirmTime.setVisible(False)

    def _reset_controls(self):
        self.btnConfirm.setEnabled(False)
        self.btnScan.setEnabled(True)
        self.lblScanWarn.setVisible(False)
        self.btnCSV.setEnabled(True)
        self.btnViewData.setEnabled(True)

    def setViewOnly(self, viewonly):
        if viewonly:
            self._disable_controls()
        else:
            self._reset_controls()

    def on_client_setup(self, data):
        self._find_device()

    def _find_device(self):
        devices = self.client.getDeviceList(
            "nicos_ess.odin.devices.component_tracking.ComponentTrackingDevice"
        )
        # Should only be one
        self._dev_name = devices[0] if devices else None
        self._register_listeners()

    def _register_listeners(self):
        # Only register once unless the device name changes.
        if self._dev_name and self._dev_name != self._dev_name_old:
            self._dev_name_old = self._dev_name
            self.client.register(self, f"{self._dev_name}/confirmed_components")
            self.client.on_connected_event()

    def on_keyChange(self, key, value, time, expired):
        if self._dev_name and key.startswith(self._dev_name):
            if key.endswith("/confirmed_components"):
                sorted_data = self.sort_by_distance(value)
                self.model.raw_data = sorted_data
                self.update_confirm_timestamp()
                self.get_scan_timestamp()

    def export_as_csv(self):
        options = QFileDialog().options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save as CSV", "", "CSV Files (*.csv)", options=options
        )
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        if file_path:
            with open(file_path, "w", newline="") as file:
                data_keys = [
                    COMPONENT_KEY,
                    DISTANCE_FROM_SAMPLE,
                    CONFIRMED_DISTANCE,
                    X_AXIS,
                    Y_AXIS,
                    Z_AXIS,
                    ALPHA_ANGLE,
                    BETA_ANGLE,
                    GAMMA_ANGLE,
                ]
                writer = csv.writer(file)
                writer.writerow([f"Scan timestamp: {self.get_scan_timestamp()}"])
                writer.writerow(data_keys)
                for data in self.model.raw_data:
                    writer.writerow([data[key] for key in data_keys])

    def view_data(self):
        new_columns = [
            CONFIRMED_DISTANCE,
            X_AXIS,
            Y_AXIS,
            Z_AXIS,
            ALPHA_ANGLE,
            BETA_ANGLE,
            GAMMA_ANGLE,
        ]
        filtered_self_columns = self.columns.copy()
        filtered_self_columns.pop(CHECKBOXES_COLUMN_NAME, None)
        columns = {
            **filtered_self_columns,
            **{
                name: Column(
                    name,
                    False,
                    QHeaderView.ResizeMode.ResizeToContents,
                    True,
                    ReadOnlyDelegate(),
                )
                for name in new_columns
            },
        }

        self.pop_up_table = QTableView()
        model = OdinMetrologySystemModel(list(columns.keys()), columns)
        self.pop_up_table.setModel(model)
        model.raw_data = self.model.raw_data

        for i in range(len(columns)):
            self.pop_up_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )

        padding = 10
        width = (
            self.pop_up_table.verticalHeader().width()
            + self.pop_up_table.horizontalHeader().length()
            + padding
        )
        height = (
            self.pop_up_table.horizontalHeader().height()
            + self.pop_up_table.verticalHeader().length()
            + padding
        )
        self.pop_up_table.resize(width, height)
        self.pop_up_table.show()

    def update_confirm_timestamp(self):
        confirm_timestamp = self.exec_command(
            "component_tracking.get_confirmed_timestamp()"
        )
        if confirm_timestamp == Ellipsis or confirm_timestamp is None:
            self.lblConfirmTime.setText(
                "No timestamp for last confirmed configuration found"
            )
        else:
            self.lblConfirmTime.setText(f"Last confirmed: {confirm_timestamp}")

    def get_scan_timestamp(self):
        scan_timestamp = self.exec_command("component_tracking.get_scan_timestamp()")
        if scan_timestamp == Ellipsis or scan_timestamp is None:
            return "Could not retrieve last scanned timestamp"
        return str(scan_timestamp)

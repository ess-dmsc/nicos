#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
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
#   Ebad Kamil <Ebad.Kamil@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************

"""LoKI Script Builder Panel."""

import os.path as osp
from collections import OrderedDict
from functools import partial

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QFileDialog, QHeaderView, QTableView, pyqtSlot
from nicos.utils import findResource

from nicos_ess.loki.gui.loki_panel import LokiPanelBase
from nicos_ess.loki.gui.loki_script_generator import ScriptFactory, TransOrder
from nicos_ess.loki.gui.loki_scriptbuilder_model import LokiScriptModel
from nicos_ess.loki.gui.loki_tableview import LokiTableViewBase
from nicos_ess.utilities.csv_utils import export_table_to_csv, \
    import_table_from_csv

TABLE_QSS = 'alternate-background-color: aliceblue;'


class LokiScriptBuilderPanel(LokiPanelBase, LokiTableViewBase):
    _available_trans_options = OrderedDict({
        'All TRANS First': TransOrder.TRANSFIRST,
        'All SANS First': TransOrder.SANSFIRST,
        'TRANS then SANS': TransOrder.TRANSTHENSANS,
        'SANS then TRANS': TransOrder.SANSTHENTRANS,
        'Simultaneous': TransOrder.SIMULTANEOUS
    })

    def __init__(self, parent, client, options):
        LokiPanelBase.__init__(self, parent, client, options)
        loadUi(self,
               findResource('nicos_ess/loki/gui/ui_files/loki_scriptbuilder.ui')
               )

        self.window = parent
        self.duration_options = ['Mevents', 'seconds', 'frames']

        self.permanent_columns = {
            'position': 'Position',
            'sample': 'Sample',
            'thickness': 'Thickness\n(mm)',
            'trans_duration': 'TRANS Duration',
            'sans_duration': 'SANS Duration'
        }

        self.optional_columns = {
            'temperature': ('Temperature', self.chkShowTempColumn),
            'pre-command': ('Pre-command', self.chkShowPreCommand),
            'post-command': ('Post-command', self.chkShowPostCommand)
        }
        # Set up trans order combo-box
        self.comboTransOrder.addItems(self._available_trans_options.keys())

        self.columns_in_order = list(self.permanent_columns.keys())
        self.columns_in_order.extend(self.optional_columns.keys())
        self.last_save_location = None
        self._init_table_panel()

    def _init_table_panel(self):
        headers = [
            self.permanent_columns[name]
            if name in self.permanent_columns
            else self.optional_columns[name][0]
            for name in self.columns_in_order
        ]

        self.model = LokiScriptModel(headers)
        self.tableView.setModel(self.model)
        self.set_base_view(self.tableView, self.model,
                           self.optional_columns, self.columns_in_order)
        self._init_right_click_context_menu()

        self.tableView.setSelectionMode(QTableView.ContiguousSelection)

        for name, details in self.optional_columns.items():
            _, checkbox = details
            checkbox.stateChanged.connect(
                partial(self._on_optional_column_toggled, name))
            self._hide_column(name)

        self._link_duration_combobox_to_column('sans_duration',
                                               self.comboSansDurationType)
        self._link_duration_combobox_to_column('trans_duration',
                                               self.comboTransDurationType)

        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.tableView.resizeColumnsToContents()
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setStyleSheet(TABLE_QSS)

        self._create_keyboard_shortcuts()

    @pyqtSlot()
    def on_cutButton_clicked(self):
        self._handle_cut_cells()

    @pyqtSlot()
    def on_copyButton_clicked(self):
        self._handle_copy_cells()

    @pyqtSlot()
    def on_pasteButton_clicked(self):
        self._handle_table_paste()

    @pyqtSlot()
    def on_addAboveButton_clicked(self):
        self._insert_row_above()

    @pyqtSlot()
    def on_addBelowButton_clicked(self):
        self._insert_row_below()

    @pyqtSlot()
    def on_deleteRowsButton_clicked(self):
        self._delete_rows()

    @pyqtSlot()
    def on_loadTableButton_clicked(self):
        try:
            filename = QFileDialog.getOpenFileName(
                self,
                'Open table',
                osp.expanduser('~') if self.last_save_location is None \
                    else self.last_save_location,
                'Table Files (*.txt *.csv)')[0]

            if not filename:
                return

            headers_from_file, data = import_table_from_csv(filename)

            if not set(headers_from_file).issubset(set(self.columns_in_order)):
                raise AttributeError('incorrect headers in file')
            # Clear existing table before populating from file
            self.on_clearTableButton_clicked()
            self._fill_table(headers_from_file, data)

            for optional in set(headers_from_file).intersection(
                set(self.optional_columns.keys())):
                self.optional_columns[optional][1].setChecked(True)
        except Exception as error:
            self.showError(f'Could not load {filename}:  {error}')

    def _fill_table(self, headers, data):
        # corresponding indices of elements in headers_from_file list to headers
        indices = [index for index, element in
                   enumerate(self.columns_in_order) if element in headers]

        table_data = []
        for row in data:
            # create appropriate length list to fill the table row
            row = self._fill_elements(row, indices, len(self.columns_in_order))
            table_data.append(row)

        self.model.table_data = table_data

    def _fill_elements(self, row, indices, length):
        """Returns a list with row elements placed in the given indices.
        """
        if len(row) == length:
            return row
        result = [''] * length
        # Slicing similar to numpy arrays result[indices] = row
        for index, value in zip(indices, row):
            result[index] = value
        return result

    @pyqtSlot()
    def on_saveTableButton_clicked(self):
        if self.is_data_in_hidden_columns():
            self.showError('Cannot save because data in optional column(s).'
                           'Select the optional column or clear the column.')
            return

        filename = QFileDialog.getSaveFileName(
            self,
            'Save table',
            osp.expanduser('~') if self.last_save_location is None
            else self.last_save_location,
            'Table files (*.txt *.csv)',
            initialFilter='*.txt;;*.csv')[0]

        if not filename:
            return
        if not filename.endswith(('.txt', '.csv')):
            filename = filename + '.csv'

        self.last_save_location = osp.dirname(filename)
        try:
            headers = self._extract_headers_from_table()
            data = self._extract_data_from_table()
            export_table_to_csv(data, filename, headers)
        except Exception as ex:
            self.showError(f'Cannot write table contents to {filename}:\n{ex}')

    def _link_duration_combobox_to_column(self, column_name, combobox):
        combobox.addItems(self.duration_options)
        combobox.currentTextChanged.connect(
            partial(self._on_duration_type_changed, column_name))
        self._on_duration_type_changed(column_name,
                                       combobox.currentText())

    @pyqtSlot()
    def on_bulkUpdateButton_clicked(self):
        self._do_bulk_update(self.txtValue.text())

    @pyqtSlot()
    def on_clearTableButton_clicked(self):
        self.model.clear()

    def _extract_labeled_data(self):
        hidden_column_names = self._get_hidden_column_names()
        labeled_data = []
        for row_data in self.model.table_data:
            labeled_row_data = dict(zip(self.columns_in_order, row_data))
            for key in hidden_column_names:
                del labeled_row_data[key]
            # Row will contribute to script only if all permanent columns
            # values are present
            if all(map(labeled_row_data.get, self.permanent_columns.keys())):
                labeled_data.append(labeled_row_data)
        return labeled_data

    @pyqtSlot()
    def on_generateScriptButton_clicked(self):
        if self.is_data_in_hidden_columns():
            self.showError('There is data in optional column(s) which will '
                           'not appear in the script')

        labeled_data = self._extract_labeled_data()

        if self._available_trans_options[self.comboTransOrder.currentText()]\
                == TransOrder.SIMULTANEOUS:
            if not all((data['sans_duration'] == data['trans_duration']
                        for data in labeled_data)):
                self.showError(
                        'Different SANS and TRANS duration specified in '
                        'SIMULTANEOUS mode. SANS duration will be used in '
                        'the script.'
                )

        _trans_order = self._available_trans_options[
            self.comboTransOrder.currentText()]
        template = ScriptFactory.from_trans_order(_trans_order).\
            generate_script(labeled_data,
                            self.comboTransDurationType.currentText(),
                            self.comboSansDurationType.currentText(),
                            self.sbTransTimes.value(),
                            self.sbSansTimes.value())

        self.mainwindow.codeGenerated.emit(template)

    def _on_duration_type_changed(self, column_name, value):
        column_number = self.columns_in_order.index(column_name)
        self._set_column_title(column_number,
                               f'{self.permanent_columns[column_name]}'
                               f'\n({value})')

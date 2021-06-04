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
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************

"""LoKI Sample Changers dialog."""
import itertools

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QDialog, QItemDelegate, QLineEdit, Qt, \
    QTableWidget, QTableWidgetItem
from nicos.utils import findResource

from nicos_ess.loki.gui.loki_panel import LokiPanelBase
from nicos_ess.utilities.validators import DoubleValidator


def validate(ui_element):
    validator_values = {  # in units of mm
        'bottom': 0.0,
        'top': 1000.0,
        'decimal': 5,
    }
    validator = DoubleValidator(**validator_values)
    ui_element.setValidator(validator)


class TableDelegate(QItemDelegate):
    # There is no direct validation call for `QTableWidget`. One straightforward
    # method is the use of delegations. Here, our delegate is a `QLineEdit`.
    def createEditor(self, parent, option, index):
        delegated_table = QLineEdit(parent)
        validate(delegated_table)
        return delegated_table


class ThermoCellHolderPositions(QDialog):

    def __init__(self, parent, client):
        QDialog.__init__(self, parent)
        self.client = client
        loadUi(self, findResource('nicos_ess/loki/gui/'
                                  'ui_files/sample_changers/'
                                  'thermo_cell_holder_positions.ui'))
        self.initialise_markups()
        for table in self._get_all_tables():
            table.setItemDelegate(TableDelegate())

        self._disable_all_positions_but_first()

        self.dialogButtonBox.rejected.connect(self.reject)
        self.dialogButtonBox.accepted.connect(self.accept)

    def initialise_markups(self):
        self.setWindowTitle('Cartridge Settings')
        self.setStyleSheet("background-color: whitesmoke;")
        for table in self._get_all_tables():
            table.setStyleSheet("background-color: white;")

    def _get_all_tables(self):
        _tables = itertools.chain(
                self.topRowGroup.findChildren(QTableWidget),
                self.bottomRowGroup.findChildren(QTableWidget)
            )
        return _tables

    def _disable_all_positions_but_first(self):
        for table in self._get_all_tables():
            self._disable(table)

    def _disable(self, table):
        # Whenever an item is set to a `QTableWidget`, that widget takes the
        # ownership and the item cannot be set to another widget. Thus, we
        # create an instance of an item for each cell.
        for i in range(1, self.firstRowFirstTable.rowCount()):
            for j in range(self.firstRowFirstTable.columnCount()):
                table.setItem(i, j, self._configure_item())

    @staticmethod
    def _configure_item():
        item = QTableWidgetItem(str(0.0))
        item.setFlags(Qt.ItemIsEnabled)
        item.setBackground(Qt.lightGray)
        return item


class ThermoCellHolderSettings(LokiPanelBase):
    def __init__(self, parent, client, options, frame):
        LokiPanelBase.__init__(self, parent, client, options)
        self.client = client
        self.frame = frame
        loadUi(self.frame, findResource('nicos_ess/loki/gui/'
                                        'ui_files/sample_changers/'
                                        'thermo_cell_holder_settings.ui'))
        self.initialise_validators()
        self.frame.cartridgeSettings.clicked.connect(
            self._active_holder_position_settings)

    def initialise_validators(self):
        for box in self.frame.findChildren(QLineEdit):
            validate(box)

    def _active_holder_position_settings(self):
        dialog = ThermoCellHolderPositions(self, self.client)
        if not dialog.exec_():
            return

        self._set_first_positions(dialog)

    def _set_first_positions(self, dialog):
        values = self._get_first_position_values(dialog)
        if not values:
            return

        _table = self.frame.firstPosTable
        for i in range(_table.rowCount()):
            for j in (0, 1):
                _item = QTableWidgetItem(values[i][j])
                _table.setItem(i, j, _item)

    def _get_first_position_values(self, dialog):
        # We need the values in a specific order. Besides, QT's algorithm of
        # returning children is not clear.
        ordered_tables = (
            dialog.firstRowFirstTable,
            dialog.secondRowFirstTable,
            dialog.firstRowSecondTable,
            dialog.secondRowSecondTable,
            dialog.firstRowThirdTable,
            dialog.secondRowThirdTable,
            dialog.firstRowFourthTable,
            dialog.secondRowFourthTable,
        )
        first_position_values = []
        for table in ordered_tables:
            first_position_values.append(self._read_values(table))
        return first_position_values

    @staticmethod
    def _read_values(table):
        # todo: This function will change upon implementation of the
        # todo: corresponding device.
        first_positions = []
        for j in range(0, 2):
            if table.item(0, j):
                first_positions.append(table.item(0, j).text())
            else:
                first_positions.append('0')
        return first_positions

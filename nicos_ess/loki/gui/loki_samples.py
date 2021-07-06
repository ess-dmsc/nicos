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
#  AÜC Hardal <ümit.hardal@ess.eu>
#
# *****************************************************************************

"""LoKI Samples Panel."""

from nicos.clients.gui.utils import loadUi
from nicos.utils import findResource
from nicos_ess.loki.gui.loki_data_model import LokiDataModel
from nicos_ess.loki.gui.loki_panel import LokiPanelBase
from nicos.guisupport.qt import QHeaderView, QTableView

TABLE_QSS = 'alternate-background-color: aliceblue;'


class LokiSamplePanel(LokiPanelBase):
    def __init__(self, parent, client, options):
        LokiPanelBase.__init__(self, parent, client, options)
        loadUi(self,
               findResource('nicos_ess/loki/gui/ui_files/loki_samples.ui')
               )
        self.window = parent

        self.permanent_columns = {
            'sample_name': 'Sample Name',
            'chemical_formula': 'Chemical Formula',
            'concentration': 'Concentration'
        }

        self.optional_columns = {
            'background': 'Background',
            'comments': 'Comments',
            'other': 'Other'
        }

        self.columns_in_order = list(self.permanent_columns.keys())
        self.optionalComboBox.addItems(self.optional_columns.values())
        self.optionalComboBox.setCurrentIndex(-1)
        self._init_table_panel()

    def _init_table_panel(self):
        headers = [
            self.permanent_columns[name]
            for name in self.columns_in_order
        ]

        self.model = LokiDataModel(headers)
        self.samplesTableView.setModel(self.model)
        self._init_tableview_markups()

    def _init_tableview_markups(self):
        self.samplesTableView.setSelectionMode(QTableView.ContiguousSelection)
        self.samplesTableView.horizontalHeader().setStretchLastSection(True)
        self.samplesTableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.samplesTableView.resizeColumnsToContents()
        self.samplesTableView.setAlternatingRowColors(True)
        self.samplesTableView.setStyleSheet(TABLE_QSS)

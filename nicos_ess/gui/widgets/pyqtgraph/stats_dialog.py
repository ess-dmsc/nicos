# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2023 by the NICOS contributors (see AUTHORS)
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

import csv

from nicos.guisupport.qt import (
    QDialog,
    QFileDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class StatisticsDialog(QDialog):
    def __init__(self, image_stats, roi_stats, crosshair_stats, parent=None):
        super().__init__(parent)
        self.image_stats = image_stats
        self.roi_stats = roi_stats
        self.crosshair_stats = crosshair_stats
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Value"])
        layout.addWidget(self.stats_table)

        self.populate_statistics()

        export_button = QPushButton("Export as CSV", self)
        export_button.clicked.connect(self.export_as_csv)
        layout.addWidget(export_button)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def _statistic_looper(self, stats):
        for stat_name, value in stats.items():
            row_position = self.stats_table.rowCount()
            self.stats_table.insertRow(row_position)
            self.stats_table.setItem(row_position, 0, QTableWidgetItem(stat_name))
            self.stats_table.setItem(row_position, 1, QTableWidgetItem(f"{value:.2f}"))

    def populate_statistics(self):
        for stats in [self.image_stats, self.roi_stats, self.crosshair_stats]:
            if stats:
                self._statistic_looper(stats)

    def export_as_csv(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Statistics", "", "CSV Files (*.csv)", options=options
        )
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        if file_path:
            with open(file_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Statistic", "Value"])
                for i in range(self.stats_table.rowCount()):
                    writer.writerow(
                        [
                            self.stats_table.item(i, 0).text(),
                            self.stats_table.item(i, 1).text(),
                        ]
                    )

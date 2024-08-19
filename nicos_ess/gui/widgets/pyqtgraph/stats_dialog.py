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

from nicos.guisupport.qt import (
    QDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QMessageBox,
    QHeaderView,
    Qt,
)


class PixelDialog(QDialog):
    def __init__(self, selected_pixels, parent=None):
        super().__init__(parent)
        self.selected_pixels = selected_pixels
        self.init_ui()
        self.populate_statistics(selected_pixels)

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["Column", "Row"])
        layout.addWidget(self.stats_table)

        self.add_row_button = QTableWidgetItem("+")
        self.add_row_button.setFlags(Qt.ItemIsEnabled)
        self.stats_table.insertRow(0)
        self.stats_table.setItem(0, 0, self.add_row_button)
        self.stats_table.setSpan(0, 0, 1, 2)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        save_button = QPushButton("Save Changes", self)
        save_button.clicked.connect(self.save_changes)
        layout.addWidget(save_button)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.connect_signals()

        self.setWindowTitle("Selected Pixels")

    def populate_statistics(self, pixels):
        for column, row in pixels:
            row_position = self.stats_table.rowCount()
            self.stats_table.insertRow(row_position)
            self.stats_table.setItem(row_position, 0, QTableWidgetItem(str(column)))
            self.stats_table.setItem(row_position, 1, QTableWidgetItem(str(row)))

    def save_changes(self):
        new_selected_pixels = []
        for row in range(1, self.stats_table.rowCount()):
            column_item = self.stats_table.item(row, 0)
            row_item = self.stats_table.item(row, 1)
            if column_item and row_item:
                column = int(column_item.text())
                row = int(row_item.text())
                new_selected_pixels.append((column, row))

        self.selected_pixels = new_selected_pixels
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_pixels()
        else:
            super().keyPressEvent(event)

    def delete_selected_pixels(self):
        selected_rows = self.stats_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No selection", "Please select a row to delete.")
            return

        for index in sorted(selected_rows, reverse=True):
            if index.row() != 0:
                self.stats_table.removeRow(index.row())

    def table_double_click(self, row, column):
        if row == 0:
            self.add_empty_row()

    def add_empty_row(self):
        row_position = self.stats_table.rowCount()
        self.stats_table.insertRow(row_position)
        self.stats_table.setItem(row_position, 0, QTableWidgetItem(""))
        self.stats_table.setItem(row_position, 1, QTableWidgetItem(""))

    def connect_signals(self):
        self.stats_table.cellDoubleClicked.connect(self.table_double_click)
        self.stats_table.itemClicked.connect(self.check_add_row_click)

    def check_add_row_click(self, item):
        if item.row() == 0:
            self.add_empty_row()

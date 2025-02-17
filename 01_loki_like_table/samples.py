import sys
import os
from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QShortcut,
    QTableView,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from samples_model import SampleTableModel
from table_helper import TableHelper, Clipboard
from csv_utils import (
    import_table_from_csv_file,
)


def get_icon(icon_name):
    icons_path = os.path.join("resources", "material", "icons")
    return QIcon(os.path.join(icons_path, icon_name))


TABLE_QSS = "alternate-background-color: aliceblue;"
SAMPLE_IDENTIFIER = "name"
SAMPLE_IDENTIFIER_COL_NAME = "Sample name"


class SampleTablePanel(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self._in_edit_mode = True
        self.last_save_location = None
        self._configure_sample_table()
        self._create_toolbar()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.sample_table)
        self.layout.insertWidget(0, self.toolbar.toolbar)

    def _configure_sample_table(self):
        columns = OrderedDict(
            {SAMPLE_IDENTIFIER_COL_NAME: SAMPLE_IDENTIFIER, "Notes": "notes"}
        )
        self.sample_model = SampleTableModel(columns)
        self.sample_table = QTableView()
        self.sample_table.setModel(self.sample_model)
        self.table_helper = TableHelper(
            self.sample_table, self.sample_model, Clipboard()
        )
        self.positions = []

        self.sample_table.setSelectionMode(QTableView.SelectionMode.ContiguousSelection)
        self.sample_table.horizontalHeader().setStretchLastSection(True)
        self.sample_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.sample_table.setAlternatingRowColors(True)
        self.sample_table.setStyleSheet(TABLE_QSS)
        self._create_keyboard_shortcuts()

    def _create_keyboard_shortcuts(self):
        for key, to_call in [
            (QKeySequence.StandardKey.Paste, self._on_paste),
            (QKeySequence.StandardKey.Cut, self._on_cut),
            (
                QKeySequence.StandardKey.Copy,
                self.table_helper.copy_selected_to_clipboard,
            ),
            ("Ctrl+Backspace", self._on_clear),
        ]:
            self._create_shortcut_key(key, to_call)

    def _create_shortcut_key(self, shortcut_keys, to_call):
        shortcut = QShortcut(shortcut_keys, self.sample_table)
        shortcut.activated.connect(to_call)
        shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)

    def _on_paste(self):
        if self._in_edit_mode:
            self.table_helper.paste_from_clipboard(expand=False)

    def _on_cut(self):
        if self._in_edit_mode:
            self.table_helper.cut_selected_to_clipboard()

    def _on_clear(self):
        if self._in_edit_mode:
            self.table_helper.clear_selected()

    def _create_toolbar(self):
        self.toolbar = TableToolBar()
        self.toolbar.open_action.triggered.connect(self._open_file)
        self.toolbar.save_action.triggered.connect(self._save_table)
        self.toolbar.add_row_below_action.triggered.connect(self._insert_row_below)
        self.toolbar.copy_row_action.triggered.connect(self._copy_row)
        self.toolbar.delete_row_action.triggered.connect(self._delete_rows)
        self.toolbar.add_col_right_action.triggered.connect(
            self._dialog_for_new_column_name
        )
        self.toolbar.move_col_right_action.triggered.connect(print)
        self.toolbar.move_col_left_action.triggered.connect(print)
        self.toolbar.rename_col_action.triggered.connect(print)
        self.toolbar.delete_col_action.triggered.connect(self._delete_cols)
        self.toolbar.clear_action.triggered.connect(self._clear_table)

    def _open_file(self):
        #####
        self.last_save_location = os.path.join(
            "~", "ess", "projects", "qt_testing", "loki_like_sample_table", "testdata"
        )
        #####
        try:
            filename = "testdata/two_samples_notes.csv"

            # filename = QFileDialog.getOpenFileName(
            #     self,
            #     "Open table",
            #     os.path.expanduser("~")
            #     if self.last_save_location is None
            #     else self.last_save_location,
            #     "Table files (*.csv)",
            # )[0]
            #
            # if not filename:
            #     return

            headers, data = import_table_from_csv_file(filename)
            print(headers)
            self.sample_model.delete_columns(
                list(range(1, len(self.sample_model.columns)))
            )

            ##### to do
            headers = [SAMPLE_IDENTIFIER_COL_NAME] + headers[1:]
            print(headers)
            if "notes" not in [header.lower() for header in headers]:
                headers.append("Notes")
            else:
                pass
            print(headers)
            new_columns = {}
            for i, header in enumerate(headers):
                if header not in self.sample_model.columns.keys():
                    self.sample_model.insert_column(i, header)
                    new_columns[header] = header
            print(new_columns)
            raw_data = []
            for row in data:
                raw_data.append(dict(zip(headers, row)))

            print(raw_data)

            # Clear existing table before populating from file
            self.sample_model.clear()
            self.sample_model.raw_data = raw_data
            # self._fill_table(headers, data)
            #
            # for name in headers:
            #     if name in self.columns and self.columns[name].optional:
            #         self.optional_columns_to_checkbox[name].setChecked(True)
        except Exception as error:
            print("There was a problem loading the selected file: " f"{error}")

    def _save_table(self):
        print(self.sample_model._raw_data)
        print(self.sample_model._table_data)
        pass
        # if self.is_data_in_hidden_columns():
        #     self.showError(
        #         "Cannot save because there is data in a non-visible "
        #         "optional column(s)."
        #     )
        #     return
        #
        # filename = QFileDialog.getSaveFileName(
        #     self,
        #     "Save table",
        #     osp.expanduser("~")
        #     if self.last_save_location is None
        #     else self.last_save_location,
        #     "Table files (*.txt)",
        #     initialFilter="*.txt",
        # )[0]
        #
        # if not filename:
        #     return
        # if not filename.endswith(".txt"):
        #     filename = filename + ".txt"
        #
        # self.last_save_location = osp.dirname(filename)
        # try:
        #     headers = self._extract_headers_from_table()
        #     data = self._extract_data_from_table()
        #     with open(filename, "w", encoding="utf-8") as file:
        #         # Record the duration types in the file before the csv block
        #         file.write(f"{self.comboTransDurationType.currentText()}\n")
        #         file.write(f"{self.comboSansDurationType.currentText()}\n")
        #         export_table_to_csv_stream(file, data, headers)
        # except Exception as ex:
        #     self.showError(f"Cannot write table contents to {filename}:\n{ex}")

    def _insert_row_below(self):
        if self.sample_model.num_entries == 0:
            self.sample_table.model().insert_row(0)
            self.sample_table.selectRow(0)
            return
        _, highest = self._get_selected_rows_limits()
        if highest is not None:
            position = highest + 1
        else:
            position = len(self.sample_model._raw_data)
        self.sample_table.model().insert_row(position)

    def _copy_row(self):
        lowest, highest = self._get_selected_rows_limits()
        new_data = []
        for index in range(lowest, highest + 1):
            row_data = self.sample_model._raw_data[index]
            new_data.append(row_data)

        new_data_with_indices = zip(
            range(highest + 1, highest + 1 + len(new_data)), new_data
        )
        for index, data in new_data_with_indices:
            self.sample_model._raw_data.insert(index, data)
            self.sample_model._table_data.insert(index, list(data.values()))
        self.sample_model._emit_update()

    def _delete_rows(self):
        to_remove = {
            index.row()
            for index in self.sample_table.selectedIndexes()
            if index.isValid() and index.row() < self.sample_model.num_entries
        }
        self.sample_table.model().remove_rows(to_remove)

    def _insert_col_right(self):
        column_name = self.dialog.column_name.text()
        _, highest = self._get_selected_cols_limits()
        position = (
            min(highest + 1, len(self.sample_model.columns) - 1) if highest else 1
        )
        self.sample_model.insert_column(position, column_name)

    def _delete_cols(self):
        to_remove = [index.column() for index in self.sample_table.selectedIndexes()]
        if len(to_remove) > 0:
            self.sample_model.delete_columns(to_remove)

    def _clear_table(self):
        self.sample_model.clear()

    def _dialog_for_new_column_name(self):
        self.dialog = ColNameDialog()
        if self.dialog.exec():
            self._insert_col_right()

    def _get_selected_rows_limits(self):
        lowest = None
        highest = None
        for index in self.sample_table.selectedIndexes():
            if lowest is None:
                lowest = index.row()
                highest = index.row()
                continue
            lowest = min(lowest, index.row())
            highest = max(highest, index.row())
        return lowest, highest

    def _get_selected_cols_limits(self):
        lowest = None
        highest = None
        for index in self.sample_table.selectedIndexes():
            if lowest is None:
                lowest = index.column()
                highest = index.column()
                continue
            lowest = min(lowest, index.column())
            highest = max(highest, index.column())
        return lowest, highest


class TableToolBar(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self._create_actions()
        self._create_toolbar()

    def _create_actions(self):
        self.open_action = QAction("Open\nFile", self)
        self.open_action.setIcon(get_icon("folder_open-24px.svg"))

        self.save_action = QAction("Export\nTable", self)
        self.save_action.setIcon(get_icon("save-24px.svg"))

        self.add_row_below_action = QAction("Add\nRow", self)
        self.add_row_below_action.setIcon(get_icon("add_row_below-24px.svg"))

        self.copy_row_action = QAction("Copy\nRow(s)", self)
        self.copy_row_action.setIcon(get_icon("add_row_below-24px.svg"))

        self.delete_row_action = QAction("Delete\nRow(s)", self)
        self.delete_row_action.setIcon(get_icon("delete_row-24px.svg"))

        self.add_col_right_action = QAction("Add\nColumn", self)
        self.add_col_right_action.setIcon(get_icon("add_col_right.svg"))

        self.move_col_right_action = QAction("Move\nColumn(s)\nRight", self)
        self.move_col_right_action.setIcon(get_icon("warning_orange-24px"))

        self.move_col_left_action = QAction("Move\nColumn(s)\nLeft", self)
        self.move_col_left_action.setIcon(get_icon("warning_orange-24px"))

        self.rename_col_action = QAction("Rename\nColumn", self)
        self.rename_col_action.setIcon(get_icon("warning_orange-24px"))

        self.delete_col_action = QAction("Delete\nColumn(s)", self)
        self.delete_col_action.setIcon(get_icon("delete_col.svg"))

        self.clear_action = QAction("Clear\nTable", self)
        self.clear_action.setIcon(get_icon("delete-24px.svg"))

        self.help_action = QAction("Help", self)
        self.help_action.setIcon(get_icon("hand.svg"))

    def _create_toolbar(self):
        self.toolbar = QToolBar("Builder")
        self._add_action(self.toolbar, self.open_action)
        self._add_action(self.toolbar, self.save_action)
        self.toolbar.addSeparator()
        self._add_action(self.toolbar, self.add_row_below_action)
        self._add_action(self.toolbar, self.copy_row_action)
        self._add_action(self.toolbar, self.delete_row_action)
        self._add_action(self.toolbar, self.add_col_right_action)

        self._add_action(self.toolbar, self.move_col_right_action)
        self._add_action(self.toolbar, self.move_col_left_action)
        self._add_action(self.toolbar, self.rename_col_action)
        self._add_action(self.toolbar, self.delete_col_action)
        self._add_action(self.toolbar, self.clear_action)
        self.toolbar.addSeparator()
        self._add_action(self.toolbar, self.help_action)

    def _add_action(self, toolbar, action):
        toolbar.addAction(action)
        widget = toolbar.widgetForAction(action)
        if isinstance(widget, QToolButton):
            widget.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)


class ColNameDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add column")

        dialog_btns = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.btn_box = QDialogButtonBox(dialog_btns)
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        line_layout = QHBoxLayout()
        message = QLabel("New column name:")
        self.column_name = QLineEdit()
        line_layout.addWidget(message)
        line_layout.addWidget(self.column_name)
        layout.addLayout(line_layout)
        layout.addWidget(self.btn_box)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)

        self.setWindowTitle("Widget Window")
        self.setGeometry(800, 800, 1200, 800)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.sample_table = SampleTablePanel()
        self.layout.addLayout(self.sample_table.layout)


if __name__ == "__main__":
    WidgetApp = QApplication([])
    WidgetWindow = MainWindow()
    WidgetWindow.show()

    sys.exit(WidgetApp.exec())

import os
import sys
from copy import deepcopy
from email.utils import UEMPTYSTRING

from nicos.guisupport.qt import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QKeySequence,
    QLabel,
    QLineEdit,
    QPushButton,
    QShortcut,
    Qt,
    QTableView,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from nicos_ess.gui.panels.panel import PanelBase
from nicos_ess.gui.panels.samples_model import SampleTableModel
from nicos_ess.gui.tables.table_helper import Clipboard, TableHelper
from nicos_ess.gui.utils import get_icon
from nicos_ess.utilities.csv_utils import (
    export_table_to_csv_stream,
    import_table_from_csv_file,
)

TABLE_QSS = "alternate-background-color: aliceblue;"
SAMPLE_IDENTIFIER = "name"
IDENTIFIER_COL_NAME = "Sample name"
DEFAULT_COLUMNS = [IDENTIFIER_COL_NAME, "Notes"]


class SampleTablePanel(PanelBase):
    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self._in_edit_mode = True
        self.to_monitor = ["sample/samples"]
        self._last_save_location = None

        self.table = SampleTable(DEFAULT_COLUMNS)
        self.toolbar = TableToolBar()
        self.buttons = ApplyDiscardButtons()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.toolbar.toolbar)
        self.layout.addWidget(self.table.view)
        self.layout.addLayout(self.buttons.layout)
        self.setLayout(self.layout)

        self.current_sample_data = deepcopy(self.table.model.raw_data)

        self._create_keyboard_shortcuts()
        self._connect_signals()
        self.initialise_connection_status_listeners()

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def on_keyChange(self, key, value, time, expired):
        print("key change, key:", key)
        # if not self.in_edit_mode and key in self.to_monitor:
        self.load_samples()

    def load_samples(self):
        self.table.model.clear()
        samples = self._get_samples()
        if len(samples) == 0:
            return

        current_headers = [header for header in self.table.model.column_headers]
        sample_headers = [header for header in samples[0].keys()]
        empty_columns = {
            header: "" for header in current_headers if header not in sample_headers
        }
        all_headers = list(sample_headers)
        all_headers.extend(x for x in current_headers if x not in all_headers)

        new_data = []
        for row in samples:
            row.update(empty_columns)
            new_data.append(row)

        self.table.model.add_missing_columns(all_headers)
        self.table.model.raw_data = new_data
        self.current_sample_data = deepcopy(self.table.model.raw_data)
        self.buttons.set_buttons_and_warning_behaviour(False)

    def _check_for_changes(self):
        changed = self.current_sample_data != self.table.model.raw_data
        self.buttons.set_buttons_and_warning_behaviour(changed)

    def _apply_changes(self):
        self.buttons.set_buttons_and_warning_behaviour(False)
        self._set_samples()
        self.current_sample_data = deepcopy(self.table.model.raw_data)

    def _discard_changes(self):
        self.table.model.raw_data = deepcopy(self.current_sample_data)

    def _get_samples(self):
        samples = self.client.eval("session.experiment.get_samples()", {})
        if len(samples) != 0:
            samples = self.rename_sample_id_column(samples)
            return samples
        else:
            return []

    def rename_sample_id_column(self, samples):
        new_samples = []
        for sample in samples:
            id_col = {}
            id_col[IDENTIFIER_COL_NAME] = sample.pop(SAMPLE_IDENTIFIER)
            updated_sample = id_col.update(sample)
            print(updated_sample)
            new_samples.append(updated_sample)
        return new_samples

    def _set_samples(self):
        if self.table.model.raw_data == self.current_sample_data:
            return

        samples = {}
        for index, sample in enumerate(self.table.model.raw_data):
            if sample[IDENTIFIER_COL_NAME] == "":
                sample[SAMPLE_IDENTIFIER] = f"sample {index + 1}"
            else:
                sample[SAMPLE_IDENTIFIER] = sample[IDENTIFIER_COL_NAME]
            sample.pop(IDENTIFIER_COL_NAME)
            samples[index] = sample
        self.client.run(f"Exp.sample.set_samples({dict(samples)})")

    def _open_file(self):
        #####
        self._last_save_location = os.path.join(
            "~", "ess", "projects", "qt_testing", "loki_like_sample_table", "testdata"
        )
        #####
        try:
            filename = QFileDialog.getOpenFileName(
                self,
                "Open table",
                os.path.expanduser("~")
                if self._last_save_location is None
                else self._last_save_location,
                "Table files (*.csv)",
            )[0]
            if not filename:
                return

            headers, data = import_table_from_csv_file(filename)
            headers = [IDENTIFIER_COL_NAME] + headers[1:]

            raw_data = []
            for row in data:
                raw_data.append(dict(zip(headers, row)))

            self.table.model.clear()
            self.table.model.add_missing_columns(headers)
            self.table.model.raw_data = raw_data

        except Exception as error:
            print(f"There was a problem loading the selected file: {error}")

    def _save_table(self):
        filename = QFileDialog.getSaveFileName(
            self,
            "Save table",
            os.path.expanduser("~")
            if self._last_save_location is None
            else self._last_save_location,
            "Table files (*.csv)",
            initialFilter="*.csv",
        )[0]

        if not filename:
            return
        if not filename.endswith(".csv"):
            filename = filename + ".csv"

        self._last_save_location = os.path.dirname(filename)
        try:
            headers = self.table.model.column_headers
            data = self.table.model.table_data
            with open(filename, "w", encoding="utf-8") as file:
                export_table_to_csv_stream(file, data, headers)
        except Exception as ex:
            self.showError(f"Cannot write table contents to {filename}:\n{ex}")

    def _add_row_below(self):
        if self.table.model.num_entries == 0:
            self.table.model.insert_row(0)
            self.table.view.selectRow(0)
            return
        _, highest = self.table.selected_rows_limits
        if highest is not None:
            row_index = highest + 1
        else:
            row_index = len(self.table.model.raw_data)
        self.table.model.insert_row(row_index)

    def _copy_row(self):
        lowest, highest = self.table.selected_rows_limits
        if highest is None:
            return

        copied_data = list(self.table.model.raw_data)[lowest : highest + 1]
        data_above_insert = self.table.model.raw_data[: highest + 1]
        data_below_insert = self.table.model.raw_data[highest + 1 :]

        new_data = data_above_insert + copied_data + data_below_insert
        self.table.model.raw_data = new_data

    def _delete_rows(self):
        to_remove = {
            index.row()
            for index in self.table.view.selectedIndexes()
            if index.isValid() and index.row() < self.table.model.num_entries
        }
        self.table.model.remove_rows(to_remove)

    def _prepare_add_column(self):
        self._dialog_for_add_column()

    def _dialog_for_add_column(self):
        self.dialog = ColNameDialog()
        self.dialog.setWindowTitle("Add column")
        if self.dialog.exec():
            self._add_col_right()

    def _add_col_right(self):
        column_name = self.dialog.column_name.text()
        _, highest = self.table.selected_cols_limits
        if highest is not None:
            column_index = highest + 1
        else:
            column_index = len(self.table.model.raw_data)
        self.table.model.insert_column(column_index, column_name)

    def _prepare_rename_column(self):
        lowest, highest = self.table.selected_cols_limits
        if lowest != highest:
            return
        self._dialog_for_renaming_column()

    def _dialog_for_renaming_column(self):
        self.dialog = ColNameDialog()
        self.dialog.setWindowTitle("Rename column")
        if self.dialog.exec():
            self._rename_col()

    def _rename_col(self):
        lowest, _ = self.table.selected_cols_limits
        new_column_name = self.dialog.column_name.text()
        self.table.model.rename_column(lowest, new_column_name)

    def _delete_cols(self):
        to_remove = [index.column() for index in self.table.view.selectedIndexes()]
        if 0 in to_remove:
            to_remove = [index for index in to_remove if index != 0]
        if len(to_remove) > 0:
            self.table.model.delete_columns(to_remove)

    def _info_dialog(self, message):
        self.dialog = InfoDialog()
        self.dialog.message.setText(message)
        self.dialog.exec()

    def _clear_table(self):
        self.table.model.clear()

    def _create_keyboard_shortcuts(self):
        for key, to_call in [
            (QKeySequence.StandardKey.Paste, self._on_paste),
            (QKeySequence.StandardKey.Cut, self._on_cut),
            (
                QKeySequence.StandardKey.Copy,
                self.table.helper.copy_selected_to_clipboard,
            ),
            ("Ctrl+Backspace", self._on_clear),
        ]:
            self._create_shortcut_key(key, to_call)

    def _create_shortcut_key(self, shortcut_keys, to_call):
        shortcut = QShortcut(shortcut_keys, self.table.view)
        shortcut.activated.connect(to_call)
        shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)

    def _on_paste(self):
        if self._in_edit_mode:
            self.table.helper.paste_from_clipboard(expand=False)

    def _on_cut(self):
        if self._in_edit_mode:
            self.table.helper.cut_selected_to_clipboard()

    def _on_clear(self):
        if self._in_edit_mode:
            self.table.helper.clear_selected()

    def _connect_signals(self):
        self.toolbar.open_action.triggered.connect(self._open_file)
        self.toolbar.save_action.triggered.connect(self._save_table)
        self.toolbar.add_row_below_action.triggered.connect(self._add_row_below)
        self.toolbar.copy_row_action.triggered.connect(self._copy_row)
        self.toolbar.delete_row_action.triggered.connect(self._delete_rows)
        self.toolbar.add_col_right_action.triggered.connect(self._prepare_add_column)
        # self.toolbar.move_col_right_action.triggered.connect(self._move_cols_right)
        # self.toolbar.move_col_left_action.triggered.connect(self._move_cols_left)
        self.toolbar.rename_col_action.triggered.connect(self._prepare_rename_column)
        self.toolbar.delete_col_action.triggered.connect(self._delete_cols)
        self.toolbar.clear_action.triggered.connect(self._clear_table)

        self.table.model.data_updated.connect(self._check_for_changes)

        self.buttons.btn_apply.clicked.connect(self._apply_changes)
        self.buttons.btn_discard.clicked.connect(self._discard_changes)


class SampleTable:
    def __init__(self, columns):
        self.model = SampleTableModel(columns)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.helper = TableHelper(self.view, self.model, Clipboard())
        self.view.setSelectionMode(QTableView.SelectionMode.ContiguousSelection)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.view.setAlternatingRowColors(True)
        self.view.setStyleSheet(TABLE_QSS)

    @property
    def selected_rows_limits(self):
        lowest = None
        highest = None
        for index in self.view.selectedIndexes():
            if lowest is None:
                lowest = index.row()
                highest = index.row()
                continue
            lowest = min(lowest, index.row())
            highest = max(highest, index.row())
        return lowest, highest

    @property
    def selected_cols_limits(self):
        lowest = None
        highest = None
        for index in self.view.selectedIndexes():
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
        self.copy_row_action = QAction("Copy\nRows", self)
        self.copy_row_action.setIcon(get_icon("add_row_below-24px.svg"))
        self.delete_row_action = QAction("Delete\nRows", self)
        self.delete_row_action.setIcon(get_icon("delete_row-24px.svg"))
        self.add_col_right_action = QAction("Add\nColumn", self)
        self.add_col_right_action.setIcon(get_icon("add_col_right.svg"))
        # self.move_col_right_action = QAction("Move\nColumns", self)
        # self.move_col_right_action.setIcon(get_icon("move_col_right.svg"))
        # self.move_col_left_action = QAction("Move\nColumns", self)
        # self.move_col_left_action.setIcon(get_icon("move_col_left.svg"))
        self.rename_col_action = QAction("Rename\nColumn", self)
        self.rename_col_action.setIcon(get_icon("rename_col.svg"))
        self.delete_col_action = QAction("Delete\nColumns", self)
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
        # self._add_action(self.toolbar, self.move_col_right_action)
        # self._add_action(self.toolbar, self.move_col_left_action)
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


class ApplyDiscardButtons(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.lbl_warning = QLabel("Changes to the samples have not been applied!")
        self.btn_apply = QPushButton("Apply")
        self.btn_discard = QPushButton("Discard")
        self.lbl_warning.setStyleSheet("font-weight: bold;color: red;")
        self.btn_apply.setFixedWidth(80)
        self.btn_discard.setFixedWidth(80)
        self.layout.addStretch()
        self.layout.addWidget(self.lbl_warning)
        self.layout.addWidget(self.btn_apply)
        self.layout.addWidget(self.btn_discard)

        self.set_buttons_and_warning_behaviour(False)

    def set_buttons_and_warning_behaviour(self, changed):
        self.btn_apply.setEnabled(changed)
        self.btn_discard.setEnabled(changed)
        self.lbl_warning.setVisible(changed)


class ColNameDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
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


class InfoDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("Info")
        dialog_btns = QDialogButtonBox.Close
        self.btn_box = QDialogButtonBox(dialog_btns)
        self.btn_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel()
        layout.addWidget(message)
        layout.addWidget(self.btn_box)
        self.setLayout(layout)

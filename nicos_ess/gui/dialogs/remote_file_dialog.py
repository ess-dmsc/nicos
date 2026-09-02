import os
import time

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QAbstractItemView,
    QAbstractTableModel,
    QDialog,
    QHeaderView,
    QMessageBox,
    QRegularExpression,
    QRegularExpressionValidator,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from nicos.utils import findResource
from nicos_ess.gui.utils import get_icon

USER_SCRIPT = 0
INSTRUMENT_SCRIPT = 1
FOLDER_ICON = get_icon("folder_open-24px.svg")
FILE_ICON = get_icon("document-24px.svg")


class FileTableModel(QAbstractTableModel):
    data_updated = pyqtSignal()

    def __init__(self, headers):
        super().__init__()
        self._headers = headers
        self._table_data = []

    def headerData(self, section, orientation, role):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self._headers[section]

    def columnCount(self, index):
        return len(self._headers)

    def rowCount(self, index):
        return len(self._table_data)

    def _emit_update(self):
        self.layoutChanged.emit()
        self.data_updated.emit()

    def sort(self, column, order):
        if column == 0 and order == Qt.SortOrder.DescendingOrder:
            self._table_data.sort(key=lambda x: x[0])
        elif column == 0 and order == Qt.SortOrder.AscendingOrder:
            self._table_data.sort(key=lambda x: x[0], reverse=True)
        elif column == 1 and order == Qt.SortOrder.DescendingOrder:
            self._table_data.sort(key=lambda x: x[2])
        elif column == 1 and order == Qt.SortOrder.AscendingOrder:
            self._table_data.sort(key=lambda x: x[2], reverse=True)
        self._emit_update()

    def data(self, index, role):
        row, column = index.row(), index.column()
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._table_data[row][column]

        if role == Qt.ItemDataRole.DecorationRole and column == 0:
            # All table data is stored as strings
            if self._table_data[row][3]:
                return FOLDER_ICON
            return FILE_ICON

    def get_row(self, row_index):
        if 0 <= row_index < len(self._table_data):
            return self._table_data[row_index]
        return None

    def set_data(self, data):
        self._table_data = data
        self._emit_update()


class RemoteFileDialog(QDialog):
    @classmethod
    def get_file(cls, parent, client, directory="", save=False, admin=False, name=None):
        dialog = cls(parent, client, directory, save, admin, name)
        if dialog.exec() == 1:
            return dialog.get_selected_file(), dialog.is_inst_script
        return None, False

    def __init__(self, parent, client, directory, save, admin, name):
        QDialog.__init__(self, parent)
        loadUi(self, findResource("nicos_ess/gui/dialogs/remote_file_dialog.ui"))

        self.client = client
        self.save = save
        self.admin = admin
        self.is_inst_script = False
        self.rel_directory = []

        # We store the raw modification time but don't show it.
        # When we sort on modification time we use the raw value
        # which is in seconds since 1970.
        self.table_model = FileTableModel(["Name", "Modified", "Raw modified", "is_dir"])

        self.file_table.setModel(self.table_model)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.file_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.file_table.setColumnHidden(2, True)
        self.file_table.setColumnHidden(3, True)
        self.file_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.file_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.file_table.setShowGrid(False)
        self.file_table.setSortingEnabled(True)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.btn_ok.setDefault(True)

        self.file_table.selectionModel().currentRowChanged.connect(
            self.on_selection_changed
        )

        # Limit what chars are acceptable in a file name
        self.txt_filename.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9._=+-]+"), self)
        )

        self.file_table.doubleClicked.connect(self.on_file_double_clicked)

        if self.save:
            self.setWindowTitle("Save Script File As")
            self.btn_ok.setText("Save")
            self.btn_ok.setEnabled(False)
            self.txt_filename.textChanged.connect(self.on_filename_changed)
            if name is not None:
                self.txt_filename.setText(name.strip())
        else:
            self.setWindowTitle("Open Script File")
            self.txt_filename.hide()
            self.lbl_name.hide()

        if self.save or not self.admin:
            self.lbl_script_type.hide()
            self.combo_script_type.hide()

        self.combo_script_type.currentIndexChanged.connect(
            self.on_combo_script_type_changed
        )

        self._update_files_list()
        self._update_path_controls()

    def _update_files_list(self, directory=""):
        self.abs_directory, (files_info, directories) = self.client.eval(
            f"session.experiment.list_user_scripts_directory('{directory}')", (None, None)
        )
        if files_info is None:
            raise RuntimeError("Could not retrieve files from NICOS server")

        directories.sort()
        files_info.sort(key=lambda x: x[0])
        self.filenames = {x[0] for x in files_info}

        raw_data = [
            (
                name,
                "",
                "",
                True,
            )
            for name  in directories
        ]

        for name, modified in files_info:
            raw_data.append(
                (
                    name,
                    time.ctime(modified),
                    int(modified),
                    False,
                )
            )

        self.table_model.set_data(raw_data)
        self.file_table.clearSelection()

    def on_selection_changed(self, current, _previous):
        row = self.table_model.get_row(current.row())
        if row and not row[3]:
            self.txt_filename.setText(row[0])

    def on_filename_changed(self, name):
        self.btn_ok.setEnabled(name.strip() != "")

    @pyqtSlot()
    def on_btn_ok_pressed(self):
        if self.save:
            filename = self.txt_filename.text().strip()

            if filename in self.filenames:
                message = (
                    f'A file named "{filename}" already exists.\n'
                    "Do you want to replace it?"
                )
                buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                rc = QMessageBox.question(self, "Replace File?", message, buttons)
                if rc == QMessageBox.StandardButton.No:
                    return
            self.accept()

        if not self.file_table.selectionModel().selectedRows():
            # Ignore "open" if nothing selected
            return

        row = self.file_table.selectionModel().selectedRows()[0]

        # Clicking 'open' on a folder should open the folder.
        if row[3]:
            self.rel_directory.append(row[0])
            path = "/".join(self.rel_directory)
            self._update_files_list(path)
            self._update_path_controls()
            return

        self.accept()

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def _get_sanitised_filename(self):
        filename = os.path.join(self.abs_directory, self.txt_filename.text().strip())
        if not filename.endswith(".py"):
            filename += ".py"
        return filename

    def get_selected_file(self):
        return self._get_sanitised_filename()

    def on_combo_script_type_changed(self, i):
        if i == USER_SCRIPT:
            self.abs_directory, files_info = self.client.eval(
                "session.experiment.list_user_scripts_directory()", (None, None)
            )
            self.is_inst_script = False
        else:
            self.abs_directory, files_info = self.client.eval(
                "session.experiment.list_instrument_scripts_directory()", (None, None)
            )
            self.is_inst_script = True

        if files_info is None:
            raise RuntimeError("Could not retrieve files from NICOS server")

        self._update_files_list(files_info)

    def on_file_double_clicked(self, index):
        is_dir = self.table_model.data(
            self.table_model.index(index.row(), 3),
            Qt.ItemDataRole.DisplayRole,
        )
        filename = self.table_model.data(
            self.table_model.index(index.row(), 0),
            Qt.ItemDataRole.DisplayRole,
        )

        if is_dir:
            self.rel_directory.append(filename)
            path = "/".join(self.rel_directory)
            self._update_files_list(path)
            self._update_path_controls()
        else:
            self.txt_filename.setText(filename)
            self.on_btn_ok_pressed()

    def _update_path_controls(self):
        path = "/".join(self.rel_directory)
        if path:
            self.txt_path.setVisible(True)
            self.lbl_path.setVisible(True)
            self.btn_up.setVisible(True)

            self.txt_path.setText(path)
        else:
            self.txt_path.setVisible(False)
            self.lbl_path.setVisible(False)
            self.btn_up.setVisible(False)

    @pyqtSlot()
    def on_btn_up_pressed(self):
        self.rel_directory.pop()
        path = "/".join(self.rel_directory)
        self._update_files_list(path)
        self._update_path_controls()

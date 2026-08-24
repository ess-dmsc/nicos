import os
import time

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMessageBox,
    QRegularExpression,
    QRegularExpressionValidator,
    Qt,
    pyqtSlot,
)
from nicos.guisupport.tablemodel import TableModel
from nicos.utils import findResource

USER_SCRIPT = 0
INSTRUMENT_SCRIPT = 1


class FileTableModel(TableModel):
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

        # We store the raw modification time but don't show it.
        # When we sort on modification time we use the raw value
        # which is in seconds since 1970.
        self.table_model = FileTableModel(["Name", "Modified", "Raw modified"])

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
        self.file_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
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

        self.directory, files_info = self.client.eval(
            "session.experiment.list_user_scripts_directory()", (None, None)
        )
        if files_info is None:
            raise RuntimeError("Could not retrieve files from NICOS server")

        self._update_files_list(files_info)

    def _update_files_list(self, files_info):
        files_info.sort(key=lambda x: x[0])
        self.filenames = {x[0] for x in files_info}

        self.table_model.raw_data = [
            {
                "Name": name,
                "Modified": time.ctime(modified),
                "Raw modified": int(modified),
            }
            for name, modified in files_info
        ]

        if files_info and not self.save:
            first = self.table_model.index(0, 0)
            self.file_table.setCurrentIndex(first)
            self.on_selection_changed(first, None)

    def on_selection_changed(self, current, _previous):
        filename = self.table_model.data(
            current,
            Qt.ItemDataRole.DisplayRole,
        )
        self.txt_filename.setText(filename)

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

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def _get_sanitise_filename(self):
        filename = os.path.join(self.directory, self.txt_filename.text().strip())
        if not filename.endswith(".py"):
            filename += ".py"
        return filename

    def get_selected_file(self):
        return self._get_sanitise_filename()

    def on_combo_script_type_changed(self, i):
        if i == USER_SCRIPT:
            self.directory, files_info = self.client.eval(
                "session.experiment.list_user_scripts_directory()", (None, None)
            )
            self.is_inst_script = False
        else:
            self.directory, files_info = self.client.eval(
                "session.experiment.list_instrument_scripts_directory()", (None, None)
            )
            self.is_inst_script = True

        if files_info is None:
            raise RuntimeError("Could not retrieve files from NICOS server")

        self._update_files_list(files_info)

    def on_file_double_clicked(self, index):
        filename = self.table_model.data(
            self.table_model.index(index.row(), 0),
            Qt.ItemDataRole.DisplayRole,
        )
        self.txt_filename.setText(filename)
        self.on_btn_ok_pressed()

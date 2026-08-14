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
    def get_file(cls, parent, client, directory="", save=False):
        dialog = cls(parent, client, directory, save)
        if dialog.exec() == 1:
            return dialog.get_selected_file()
        return None

    def __init__(self, parent, client, directory, save):
        QDialog.__init__(self, parent)
        loadUi(self, findResource("nicos_ess/gui/dialogs/remote_file_dialog.ui"))

        self.client = client
        self.save = save

        files_info = self.client.eval(
            f"session.experiment.list_server_directory('{directory}')", None
        )
        if files_info is None:
            print("TODO: something went wrong")
            return
        files_info.sort(key=lambda x: x[0])
        self.filenames = {x[0] for x in files_info}

        # We store the raw modification time but don't show it.
        # When we sort on modification time we use the raw value
        # which is in seconds since 1970.
        self.table_model = FileTableModel(["Name", "Modified", "Raw modified"])
        self.table_model.raw_data = [
            {
                "Name": name,
                "Modified": time.ctime(modified),
                "Raw modified": int(modified),
            }
            for name, modified in files_info
        ]
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

        if files_info and not save:
            first = self.table_model.index(0, 0)
            self.file_table.setCurrentIndex(first)

        # Limit what chars are acceptable in a file name
        self.txt_filename.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9._=+-]+"), self)
        )

        if save:
            self.setWindowTitle("Save Script File As")
            self.btn_ok.setText("Save")
            self.btn_ok.setEnabled(False)
            self.file_table.selectionModel().currentRowChanged.connect(
                self.on_selection_changed
            )
            self.txt_filename.textChanged.connect(self.on_filename_changed)
        else:
            self.setWindowTitle("Open Script File")
            self.txt_filename.hide()
            self.lbl_name.hide()

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
            entered_name = self.txt_filename.text()
            if not entered_name.endswith(".py"):
                entered_name += ".py"

            if entered_name in self.filenames:
                message = f'A file named "{entered_name}" already exists.\nDo you want to replace it?'
                buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                rc = QMessageBox.question(self, "Replace File?", message, buttons)
                if rc == QMessageBox.StandardButton.No:
                    return

        self.accept()

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def get_selected_file(self):
        if self.save:
            return self.txt_filename.text()

        indexes = self.file_table.selectedIndexes()
        if indexes:
            return self.table_model.data(
                indexes[0],
                Qt.ItemDataRole.DisplayRole,
            )
        return None

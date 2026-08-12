import time
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    Qt,
    QDialog,
    pyqtSlot,
    QHeaderView,
    QAbstractItemView,
)
from nicos.utils import findResource
from nicos.guisupport.tablemodel import TableModel


class FileTableModel(TableModel):
    def sort(self, column, order):
        print("SORTING", column, order)
        print(self._table_data)
        if column == 0 and order == Qt.SortOrder.DescendingOrder:
            self._table_data.sort(key=lambda x: x[0])
        elif column == 0 and order == Qt.SortOrder.AscendingOrder:
            self._table_data.sort(key=lambda x: x[0], reverse=True)
        elif column == 1 and order == Qt.SortOrder.DescendingOrder:
            self._table_data.sort(key=lambda x: x[2])
        elif column == 1 and order == Qt.SortOrder.AscendingOrder:
            self._table_data.sort(key=lambda x: x[2], reverse=True)
        print("AFTER", self._table_data)
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
        loadUi(self, findResource("nicos_ess/gui/dialogs/file_open.ui"))

        self.client = client
        self.save = save

        files = self.client.eval(
            f"session.experiment.list_server_directory('{directory}')", None
        )
        if files is None:
            print("TODO: something went wrong")
            return
        files.sort(key=lambda x: x[0])

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
            for name, modified in files
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

        if files and not save:
            first = self.table_model.index(0, 0)
            self.file_table.setCurrentIndex(first)

        if save:
            self.setWindowTitle("Save Script File As")
            self.btn_ok.setText("Save")
        else:
            self.setWindowTitle("Open Script File")
            self.txt_filename.hide()
            self.lbl_name.hide()

    @pyqtSlot()
    def on_btn_ok_pressed(self):
        self.accept()

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def get_selected_file(self):
        print("HERE!")
        if self.save:
            print("HERE!")
            return self.txt_filename.text()

        indexes = self.file_table.selectedIndexes()
        if indexes:
            return self.table_model.data(
                indexes[0],
                Qt.ItemDataRole.DisplayRole,
            )
        return None

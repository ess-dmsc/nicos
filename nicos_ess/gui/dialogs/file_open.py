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


class FileOpenDialog(QDialog):
    @classmethod
    def get_file(cls, parent, client, directory=""):
        dialog = cls(parent, client, directory)
        if dialog.exec() == 1:
            return dialog.get_selected_file()
        return None

    def __init__(self, parent, client, directory=""):
        QDialog.__init__(self, parent)
        loadUi(self, findResource("nicos_ess/gui/dialogs/file_open.ui"))

        self.client = client

        files = self.client.eval(
            f"session.experiment.list_server_directory('{directory}')", None
        )
        files.sort()
        if files is None:
            print("TODO: something went wrong")
            return

        self.table_model = TableModel(["Name", "Size", "Modified"])
        self.table_model.raw_data = [
            {"Name": name, "Size": "128 kB", "Modified": "yesterday"} for name in files
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
        self.file_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.file_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        if files:
            first = self.table_model.index(0, 0)
            self.file_table.setCurrentIndex(first)

    @pyqtSlot()
    def on_btn_open_pressed(self):
        self.accept()

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def get_selected_file(self):
        indexes = self.file_table.selectedIndexes()
        if indexes:
            return self.table_model.data(
                indexes[0],
                Qt.ItemDataRole.DisplayRole,
            )
        return None

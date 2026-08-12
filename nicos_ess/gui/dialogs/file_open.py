from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    Qt,
    QDialog,
    QPixmap,
    QSize,
    QAbstractListModel,
    pyqtSlot,
)
from nicos.utils import findResource


class FileModel(QAbstractListModel):
    def __init__(self, files=None):
        super().__init__()
        self.files = files or []

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            text = self.files[index.row()]
            return text

    def rowCount(self, index):
        return len(self.files)


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

        self.model = FileModel(files)
        self.file_list.setModel(self.model)
        if files:
            first = self.model.index(0, 0)
            self.file_list.setCurrentIndex(first)

    @pyqtSlot()
    def on_btn_open_pressed(self):
        self.accept()

    @pyqtSlot()
    def on_btn_cancel_pressed(self):
        self.reject()

    def get_selected_file(self):
        indexes = self.file_list.selectedIndexes()
        if indexes:
            return self.model.files[indexes[0].row()]
        return None

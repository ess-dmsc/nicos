from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QDialog,
    QHeaderView,
    QStandardItem,
    QStandardItemModel,
    pyqtSignal,
    pyqtSlot,
)
from nicos.protocols.cache import OP_TELL, cache_load
from nicos.utils import findResource


class SampleDialog(QDialog):
    """Dialog to view the current sample and select another one."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        super().__init__(parent)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/sample.ui"))

        self.devices_panel = parent
        self.devname = devname
        self.samples = {}
        self.current_sample_number = None

        self.metadata_model = QStandardItemModel(0, 2, self)
        self.metadata_model.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.metadataTable.setModel(self.metadata_model)
        self.metadataTable.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )

        params = parent.client.getDeviceParams(devname)
        self._set_samples(params.get("samples", {}))
        self._show_sample(params.get("samplenumber"))
        self.resize(self.width(), self.sizeHint().height())

    def _set_samples(self, samples):
        self.samples = {n: s for n, s in (samples or {}).items() if "name" in s}
        self.samples_CB.clear()
        for number, sample in self.samples.items():
            self.samples_CB.addItem(f"{number} : {sample['name']}", number)

    def _show_sample(self, sample_number):
        self.current_sample_number = sample_number
        sample = self.samples.get(sample_number, {})
        self.sampleName.setText(sample.get("name", ""))
        self.samples_CB.setCurrentIndex(self.samples_CB.findData(sample_number))

        self.metadata_model.removeRows(0, self.metadata_model.rowCount())
        for key, value in sample.items():
            if key != "name":
                self.metadata_model.appendRow(
                    [QStandardItem(str(key)), QStandardItem(str(value))]
                )

    @pyqtSlot()
    def on_set_btn_clicked(self):
        sample_number = self.samples_CB.currentData()
        if sample_number is not None:
            self.devices_panel.exec_command(f"{self.devname}.select({sample_number!r})")

    @pyqtSlot()
    def on_btn_close_clicked(self):
        self.close()

    def on_cache_params(self, subkey, value):
        if subkey != "samples" or not value:
            return
        # keep a pick the user has not applied yet
        pending = self.samples_CB.currentData()
        self._set_samples(cache_load(value))
        self._show_sample(self.current_sample_number)
        if pending in self.samples:
            self.samples_CB.setCurrentIndex(self.samples_CB.findData(pending))

    def on_cache(self, time, subkey, op, value):
        if op == OP_TELL and value and subkey == "samplenumber":
            self._show_sample(cache_load(value))

    def closeEvent(self, event):
        event.accept()
        self.closed.emit(self.devname.lower())

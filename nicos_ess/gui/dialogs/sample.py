from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QStandardItem,
    QStandardItemModel,
    pyqtSignal,
)
from nicos.utils import findResource
from nicos_ess.gui.panels.utils import (
    attach_status_resources,
)


class SampleDialog(QDialog):
    """Dialog opened to control and view details for a sample device."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        super().__init__(parent)

        attach_status_resources(self)
        loadUi(
            self,
            findResource("nicos_ess/gui/panels/ui_files/sample.ui"),
        )

        self.log = log
        self.devices_panel = parent
        self.client = parent.client
        self.devname = devname
        self.devinfo = devinfo

        self.samples = {}
        self.title.setText("Current sample: ")
        self.sampleName.setText("")
        self.load_samples()
        self.set_up_metadata_table()

    def set_up_metadata_table(self):
        """QTableView setup"""
        table = self.metadataTable
        self.metadata_model = QStandardItemModel(self)
        self.metadata_model.setHorizontalHeaderLabels(["Parameter", "Value"])
        table.setModel(self.metadata_model)
        font = table.font()
        font.setPointSize(max(font.pointSize() - 4, 7))
        table.setFont(font)
        table.horizontalHeader().setFont(font)
        table.verticalHeader().setDefaultSectionSize(table.fontMetrics().height() + 4)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def load_samples(self):
        """Initial load of available samples from the experiment session"""

        raw_samples = self.client.eval(
            "session.experiment.get_samples()",
            [],
        )
        if isinstance(raw_samples, dict):
            raw_samples = raw_samples.values()

        self.samples = {
            sample["name"]: sample for sample in (raw_samples or []) if "name" in sample
        }

        self.samples_CB.clear()
        self.samples_CB.addItems(list(self.samples.keys()))

    def on_set_btn_pressed(self):
        sample_name = self.samples_CB.currentText()
        self.update_current_sample(sample_name)

    def update_current_sample(self, sample_name):
        """Update sample name and metadata table"""

        self.sampleName.setText(f"{sample_name}")
        sample = self.samples.get(sample_name)

        self.metadata_model.removeRows(0, self.metadata_model.rowCount())
        if not sample:
            return

        for key, value in sample.items():
            if key == "name":
                continue
            key_item = QStandardItem(str(key))
            value_item = QStandardItem(str(value))
            key_item.setEditable(False)
            value_item.setEditable(False)
            self.metadata_model.appendRow([key_item, value_item])

    def on_btn_close_pressed(self):
        self.close()
        self.closed.emit(self)

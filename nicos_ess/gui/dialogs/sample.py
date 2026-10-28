from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QStandardItem,
    QStandardItemModel,
    Qt,
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
        self.metadata_model = QStandardItemModel(0, 2, self)
        self.metadata_model.setHorizontalHeaderLabels(["Parameter", "Value"])
        table.setModel(self.metadata_model)

        font = table.font()
        font.setPointSizeF(max(font.pointSizeF() * 0.8, 7))
        table.setFont(font)  # headers inherit this

        vh = table.verticalHeader()
        vh.hide()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setDefaultSectionSize(table.fontMetrics().height() + 4)

        hh = table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setStretchLastSection(True)
        hh.setHighlightSections(False)

        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        table.setWordWrap(False)

    def load_samples(self):
        """Initial load of available samples from the experiment session"""

        raw_samples = self.client.eval(
            "session.experiment.sample.samples",
            {},
        )
        samples = (
            raw_samples.items()
            if isinstance(raw_samples, dict)
            else enumerate(raw_samples or [])
        )

        self.samples = {
            number: sample for number, sample in samples if "name" in sample
        }

        self.samples_CB.clear()
        for number, sample in self.samples.items():
            self.samples_CB.addItem(f"{number} : {sample['name']}", number)

    def on_set_btn_pressed(self):
        sample_number = self.samples_CB.currentData()
        self.update_current_sample(sample_number)

    def update_current_sample(self, sample_number):
        """Update sample name and metadata table"""

        sample = self.samples.get(sample_number)
        self.sampleName.setText(sample["name"] if sample else "")

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

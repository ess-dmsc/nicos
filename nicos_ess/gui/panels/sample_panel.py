from PyQt5 import QtCore, QtWidgets

from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    Qt,
    QTableView,
    QVBoxLayout,
)
from nicos.guisupport.tablemodel import TableModel
from nicos_ess.gui.panels.panel import PanelBase

SAMPLE_FIELDS = [
    "name",
    "formula",
    "number of",
    "mass/volume",
    "density",
    "temperature",
    "electric field",
    "magnetic field",
]
SAMPLE_MAPPINGS = {
    "number of": "number_of",
    "mass/volume": "mass_volume",
    "electric field": "electric_field",
    "magnetic field": "magnetic_field",
}


class SamplePanel(PanelBase):
    panelName = "Sample configuration"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options

        self.create_table()
        self._build_ui()

    def create_table(self):
        self.model = TableModel(
            headings=SAMPLE_FIELDS, mappings=SAMPLE_MAPPINGS, transposed=True
        )
        self.table = QTableView()
        self.table.setModel(self.model)

    def _build_ui(self):
        self._create_widgets()
        self._set_layout()
        self._prepare_table()

    def _create_widgets(self):
        self.label = QLabel("Sample information")
        self.button_add = QPushButton("Add")
        self.button_delete = QPushButton("Delete")
        self.button_apply = QPushButton("Apply")
        self.button_discard = QPushButton("Discard changes")
        self.edits_warning = QLabel(
            "Changes to the experiment proposal have not been applied!"
        )

    def _set_layout(self):
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addStretch(2)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setStretchLastSection(False)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.button_add)
        button_layout.addWidget(self.button_delete)
        button_layout.addStretch()

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label, alignment=QtCore.Qt.AlignTop)
        top_layout.addLayout(table_layout)
        top_layout.addLayout(button_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.edits_warning)
        right_layout.addWidget(self.button_discard, alignment=Qt.AlignRight)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.button_apply)
        bottom_layout.addStretch()
        bottom_layout.addLayout(right_layout)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

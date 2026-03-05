from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QSizePolicy

from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
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


class SamplePanel(PanelBase):
    panelName = "Sample configuration"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options

        self.sample_table = self.create_table_data()
        self._build_ui()

    def create_table_data(self):
        samples = {key: "" for key in SAMPLE_FIELDS}
        return samples

    def _build_ui(self):
        self._create_widgets()
        self._set_up_layout()
        self._prepare_table()

    def _create_widgets(self):
        self.label = QLabel("Sample information")
        self.table = QTableWidget()
        self.button_add = QPushButton("Add")
        self.button_delete = QPushButton("Delete")
        self.button_apply = QPushButton("Apply")
        self.button_discard = QPushButton("Discard changes")
        self.edits_warning = QLabel(
            "Changes to the experiment proposal have not been applied!"
        )

    def _set_up_layout(self):
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addStretch(2)

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

    def _prepare_table(self):
        for i, key in enumerate(self.sample_table.keys()):
            self.table.insertRow(i)
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(key))
        # self.table.setColumnCount(1)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setStretchLastSection(False)

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QSizePolicy

from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
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

        self.sample_table = self.build_sample_table()
        self.build_ui()

    def build_sample_table(self):
        samples = {key: "" for key in SAMPLE_FIELDS}
        return samples

    def build_ui(self):
        self.layout = QHBoxLayout(self)
        self.label = QLabel("Sample information")

        self.table_layout = QVBoxLayout()
        self.table = QTableWidget()
        for i, key in enumerate(self.sample_table.keys()):
            self.table.insertRow(i)
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(key))
        # self.table.setColumnCount(1)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setStretchLastSection(False)
        self.table_layout.addWidget(self.table)
        self.table_layout.addStretch(2)

        button_layout = QVBoxLayout()
        self.button_add = QPushButton("Add")
        self.button_delete = QPushButton("Delete")
        button_layout.addWidget(self.button_add)
        button_layout.addWidget(self.button_delete)
        button_layout.addStretch()

        self.layout.addWidget(self.label, alignment=QtCore.Qt.AlignTop)
        self.layout.addLayout(self.table_layout)
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)


#
# from nicos_ess.gui.panels.panel import PanelBase
# from nicos.guisupport.qt import QVBoxLayout, QLabel, QPushButton
#
# class SamplePanel(PanelBase):
#
#     def __init__(self, parent, client, options):
#         PanelBase.__init__(self, parent, client, options)
#
#         self._buildUI()
#
#     def _buildUI(self):
#         layout = QVBoxLayout(self)
#
#         self.label = QLabel('Hello NICOS', self)
#         self.button = QPushButton('Click me', self)
#
#         layout.addWidget(self.label)
#         layout.addWidget(self.button)
#
#         self.setLayout(layout)

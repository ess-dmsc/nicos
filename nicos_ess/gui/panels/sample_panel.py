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

        self.sample_table = self.create_table_data()
        self.build_ui()

    def create_table_data(self):
        samples = {key: "" for key in SAMPLE_FIELDS}
        return samples

    def build_ui(self):
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.label = QLabel("Sample information")

        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        for i, key in enumerate(self.sample_table.keys()):
            self.table.insertRow(i)
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(key))
        # self.table.setColumnCount(1)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setStretchLastSection(False)
        table_layout.addWidget(self.table)
        table_layout.addStretch(2)

        button_layout = QVBoxLayout()
        self.button_add = QPushButton("Add")
        self.button_delete = QPushButton("Delete")
        button_layout.addWidget(self.button_add)
        button_layout.addWidget(self.button_delete)
        button_layout.addStretch()

        top_layout.addWidget(self.label, alignment=QtCore.Qt.AlignTop)
        top_layout.addLayout(table_layout)
        top_layout.addLayout(button_layout)

        bottom_layout = QHBoxLayout()
        self.button_apply = QPushButton("Apply")
        self.button_discard = QPushButton("Discard changes")
        self.edits_warning = QLabel(
            "Changes to the experiment proposal have not been applied!"
        )

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.edits_warning)
        right_layout.addWidget(self.button_discard)
        bottom_layout.addWidget(self.button_apply)
        bottom_layout.addStretch()
        bottom_layout.addLayout(right_layout)

        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)


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

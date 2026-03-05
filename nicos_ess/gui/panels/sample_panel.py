from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QDialogButtonBox

from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    Qt,
    QTableView,
    QVBoxLayout,
    pyqtSlot,
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
        self._connect_signals()

    def create_table(self):
        self.model = TableModel(
            headings=SAMPLE_FIELDS, mappings=SAMPLE_MAPPINGS, transposed=True
        )
        self.table = QTableView()
        self.table.setModel(self.model)

    def _build_ui(self):
        self._create_widgets()
        self._set_layout()

    def _create_widgets(self):
        self.label = QLabel("Sample information")
        self.button_add = QPushButton("Add")
        self.button_delete = QPushButton("Delete")
        self.label_warning = QLabel(
            "Changes to the experiment proposal have not been applied!"
        )
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply)
        self.button_box.addButton(
            "Discard Changes", QDialogButtonBox.ButtonRole.ResetRole
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

        self.button_box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.label_warning.setStyleSheet("color: red; font-weight: bold")
        # self.label_warning.setVisible(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label, alignment=Qt.AlignTop)
        top_layout.addLayout(table_layout)
        top_layout.addLayout(button_layout)

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.label_warning, alignment=Qt.AlignRight)
        bottom_layout.addWidget(self.button_box)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def _connect_signals(self):
        self.button_add.clicked.connect(self.on_button_add_clicked)
        self.button_delete.clicked.connect(self.on_button_delete_clicked)

    @pyqtSlot()
    def on_button_add_clicked(self):
        self.model.insert_row(self.model.num_entries)
        self._format_table()

    @pyqtSlot()
    def on_button_delete_clicked(self):
        to_remove = {
            index.column()
            for index in self.table.selectedIndexes()
            if index.isValid() and index.column() < self.model.num_entries
        }
        self.model.remove_rows(to_remove)
        self._format_table()

    def _format_table(self):
        width = self.table.width() - self.table.verticalHeader().width()
        num_cols = self.model.columnCount(0)
        for i in range(num_cols):
            self.table.setColumnWidth(i, width // num_cols)

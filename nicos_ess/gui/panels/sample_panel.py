from copy import deepcopy

from nicos.guisupport.qt import (
    QAbstractItemView,
    QAbstractScrollArea,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
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

        self.old_settings = []
        self.new_settings = []
        self.to_monitor = ["sample/samples"]

        self._create_table()
        self._build_ui()
        self._connect_signals()
        self.initialise_connection_status_listeners()

    def _create_table(self):
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

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.button_add)
        button_layout.addWidget(self.button_delete)
        button_layout.addStretch()

        self.button_box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.label_warning.setStyleSheet("color: red; font-weight: bold")

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
        self.button_box.clicked.connect(self.on_button_box_clicked)
        self.model.data_updated.connect(self._check_for_changes)

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.setup.connect(self.on_client_setup)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def on_client_setup(self, data):
        if "system" in data[0]:
            self._update_sample_info()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self._update_sample_info()

    def on_client_disconnected(self):
        self._update_model([])
        self.old_settings = []
        self.new_settings = []
        PanelBase.on_client_disconnected(self)

    def setViewOnly(self, viewonly):
        self.set_table_read_only(self.table, viewonly)
        self.button_add.setEnabled(not viewonly)
        self.button_delete.setEnabled(not viewonly)
        if viewonly:
            self._set_buttons_and_warning_behaviour(False)
        else:
            self._check_for_changes()

    def set_table_read_only(self, table, read_only):
        if read_only:
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        else:
            table.setEditTriggers(
                QAbstractItemView.EditTrigger.AnyKeyPressed
                | QAbstractItemView.EditTrigger.EditKeyPressed
                | QAbstractItemView.EditTrigger.DoubleClicked
            )

    def _set_buttons_and_warning_behaviour(self, value):
        for button in self.button_box.buttons():
            role = self.button_box.buttonRole(button)
            button.setEnabled(value)
            if role == QDialogButtonBox.ButtonRole.ResetRole:
                button.setVisible(value)
        self.label_warning.setVisible(value)

    def _check_for_changes(self):
        has_changed = self.model.raw_data != self.old_settings
        self._set_buttons_and_warning_behaviour(has_changed)

    def on_keyChange(self, key, value, time, expired):
        if key in self.to_monitor:
            self._update_sample_info()

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

    def on_button_box_clicked(self, button):
        role = self.button_box.buttonRole(button)
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self.apply_changes()
        elif role == QDialogButtonBox.ButtonRole.ResetRole:
            self.discard_changes()

    def _format_table(self):
        width = self.table.width() - self.table.verticalHeader().width()
        num_cols = self.model.columnCount(0)
        for i in range(num_cols):
            self.table.setColumnWidth(i, width // num_cols)

    def apply_changes(self):
        print("apply clicked")
        if self.mainwindow.current_status != "idle":
            self.showInfo("Cannot change settings while a script is running!")
            return
        try:
            self._set_samples()
            self._update_sample_info()
        except Exception as error:
            self.showError(str(error))
        print(self.model.raw_data)

    def discard_changes(self):
        print("discard clicked")
        self._update_sample_info()
        self._check_for_changes()

    def _update_model(self, samples):
        self.model.raw_data = deepcopy(samples)

    def _set_samples(self):
        print("setting samples")
        if self.model.raw_data == self.old_settings:
            return

        samples = {}
        for index, sample in enumerate(self.model.raw_data):
            if not sample.get("name", ""):
                sample["name"] = f"sample {index + 1}"
            samples[index] = sample
        self.client.run(f"Exp.sample.set_samples({dict(samples)})")

    def _update_sample_info(self):
        samples = self.client.eval("session.experiment.get_samples()", {})
        self.old_settings = samples
        self.new_settings = deepcopy(self.old_settings)
        self._update_panel()

    def _update_panel(self):
        self._update_model(self.old_settings)
        self._format_table()

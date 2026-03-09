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
    "number_of",
    "mass_or_vol",
    "density",
    "temperature",
    "electric_field",
    "magnetic_field",
]

SAMPLE_MAPPINGS = {
    "mass_or_vol": "mass_volume",
}


class SampleData:
    def __init__(self, data=None):
        self.data = data if data else []
        self.headers = SAMPLE_FIELDS
        self.mapping = SAMPLE_MAPPINGS

    def _set_samples(self, samples):
        self.data = deepcopy(samples)

    def __eq__(self, other):
        return self.data == other


class SamplePanel(PanelBase):
    panelName = "Sample configuration"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.options = options

        self.old_settings = SampleData()
        self.to_monitor = ["sample/samples"]

        self.samples = SampleData()
        self._create_table(self.samples)
        self._build_ui()
        self._connect_signals()
        self.initialise_connection_status_listeners()

    def _create_table(self, sample_data):
        self.model = TableModel(
            headings=sample_data.headers, mappings=sample_data.mapping, transposed=True
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
        for cache_key in self.to_monitor:
            self.client.register(self, cache_key)

    def on_client_setup(self, data):
        if "system" in data[0]:
            self._update_sample_info()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self._update_sample_info()

    def on_client_disconnected(self):
        self.old_settings = SampleData()
        self.samples = SampleData()
        self._update_model(self.samples.data)
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
        has_changed = self.samples != self.model.raw_data
        self._set_buttons_and_warning_behaviour(has_changed)

    def on_keyChange(self, key, value, time, expired):
        if key in self.to_monitor:
            self._update_sample_info()

    @pyqtSlot()
    def on_button_add_clicked(self):
        self.model.insert_row(self.model.num_entries)

    @pyqtSlot()
    def on_button_delete_clicked(self):
        to_remove = {
            index.column()
            for index in self.table.selectedIndexes()
            if index.isValid() and index.column() < self.model.num_entries
        }
        self.model.remove_rows(to_remove)

    def on_button_box_clicked(self, button):
        role = self.button_box.buttonRole(button)
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self.apply_changes()
        elif role == QDialogButtonBox.ButtonRole.ResetRole:
            self.discard_changes()

    def apply_changes(self):
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
        self._update_sample_info()
        self._check_for_changes()

    def _update_model(self, samples):
        self.model.raw_data = deepcopy(samples)

    def _set_samples(self):
        if self.samples == self.model.raw_data:
            return

        samples = {}
        for index, sample in enumerate(self.model.raw_data):
            if not sample.get("name", ""):
                sample["name"] = f"sample {index + 1}"
            samples[index] = sample
        self.client.run(f"Exp.sample.set_samples({dict(samples)})")

    def _update_sample_info(self):
        samples = self.client.eval("session.experiment.get_samples()", {})
        self.old_settings = SampleData(samples)
        self.samples = deepcopy(self.old_settings)
        self._update_panel()

    def _update_panel(self):
        self._update_model(self.old_settings.data)

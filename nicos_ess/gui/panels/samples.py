from nicos.guisupport.qt import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    pyqtSignal,
)
from nicos_ess.gui.panels.panel import PanelBase


class SampleModel:
    updated = pyqtSignal()

    def __init__(self, client):
        self.client = client
        self.data = {}

    def load_data(self):
        samples = self.client.eval("session.experiment.get_samples()")
        self.data = samples


class SamplePanel(PanelBase):
    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)

        self._build_ui()
        self.samples = SampleModel(self.client)
        self.initialise_connection_status_listeners()

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self.samples.load_data()
        self.update_tree_widget_data()

    def update_tree_widget_data(self):
        for sample in self.samples.data:
            item = QTreeWidgetItem(self.tree, [sample["name"]])
            self.tree.addTopLevelItem(item)

    def update_table_widget_data(self, current, previous):
        if current:
            selected_sample = current.text(0)
            self.table.clearContents()
            for sample in self.samples.data:
                if sample["name"] == selected_sample:
                    for i, (key, value) in enumerate(sample.items()):
                        self.table.setItem(i, 0, QTableWidgetItem(str(key)))
                        self.table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _build_ui(self):
        self._create_widgets()
        self._set_layout()
        self._format_layout()
        self._add_signals()

    def _create_widgets(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Samples")
        self.btn_new = QPushButton("New")
        self.btn_remove = QPushButton("Remove")
        self.btn_duplicate = QPushButton("Duplicate")

        self.table = QTableWidget()
        self.table.setRowCount(100)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Label", "Value"])
        self.btn_edit = QPushButton("Edit")
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")

    def _set_layout(self):
        tree_btn_layout = QHBoxLayout()
        tree_btn_layout.addWidget(self.btn_new)
        tree_btn_layout.addWidget(self.btn_duplicate)
        tree_btn_layout.addWidget(self.btn_remove)
        tree_btn_layout.addStretch()
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self.tree)
        tree_layout.addLayout(tree_btn_layout)

        table_btn_layout = QHBoxLayout()
        table_btn_layout.addWidget(self.btn_edit)
        table_btn_layout.addWidget(self.btn_save)
        table_btn_layout.addWidget(self.btn_cancel)
        table_btn_layout.addStretch()
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addLayout(table_btn_layout)

        self.layout = QHBoxLayout()
        self.layout.addLayout(tree_layout)
        self.layout.addLayout(table_layout)
        self.setLayout(self.layout)

    def _format_layout(self):
        def _initial_label_column_width():
            self.table.setColumnWidth(0, 200)

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        QTimer.singleShot(0, _initial_label_column_width)

        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def _add_signals(self):
        self.tree.currentItemChanged.connect(self.update_table_widget_data)

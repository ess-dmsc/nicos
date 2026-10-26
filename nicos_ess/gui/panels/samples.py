from nicos.guisupport.qt import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QObject,
    QPushButton,
    QStyledItemDelegate,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    pyqtSignal,
)
from nicos_ess.gui.panels.panel import PanelBase


class SampleModel(QObject):
    updated = pyqtSignal()

    def __init__(self, client):
        QObject.__init__(self)
        self.client = client
        self.data = {}

    def load_data(self):
        samples = self.client.eval("session.experiment.get_samples()")
        self.data = samples
        self.updated.emit()


class SamplePanel(PanelBase):
    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)

        self.samples = SampleModel(self.client)
        self.edit_ongoing = False
        self._build_ui()
        self.initialise_connection_status_listeners()

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.register(self, "sample/samples")

    def on_keyChange(self, key, value, time, expired):
        if key == "sample/samples":
            self.samples.load_data()
            self.update_tree_widget_data()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self.samples.load_data()
        self.update_tree_widget_data()

    def update_tree_widget_data(self):
        self.tree.clear()
        for i, sample in enumerate(self.samples.data):
            item = QTreeWidgetItem(self.tree, [sample["name"]])
            item.setData(0, Qt.ItemDataRole.UserRole, i)

    def _add_table_data(self, data):
        for i, (key, value) in enumerate(data.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _on_sample_selected(self):
        self.table.clearContents()
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if index < len(self.samples.data):
            self._add_table_data(self.samples.data[index])

    def on_text_changed(self, row, col, text):
        if row == 0 and col == 1:
            selected_item = self.tree.selectedItems()[0]
            selected_item.setText(0, text)

    def _new_sample_btn_clicked(self):
        self.edit_ongoing = True
        new_sample_index = len(self.samples.data)
        item = QTreeWidgetItem(self.tree, ["Sample"])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)
        self.table.clearContents()
        self.table.setItem(0, 0, QTableWidgetItem("name"))
        self.table.setItem(0, 1, QTableWidgetItem("Sample"))

    def _duplicate_sample_btn_clicked(self):
        self.edit_ongoing = True
        sample_to_duplicate = self.tree.selectedItems()[0]
        index = sample_to_duplicate.data(0, Qt.ItemDataRole.UserRole)
        name = sample_to_duplicate.text(0)
        new_sample_index = len(self.samples.data)
        item = QTreeWidgetItem(self.tree, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)
        self._add_table_data(self.samples.data[index])

    def _cancel_changes_btn_clicked(self):
        self.edit_ongoing = False
        self.update_tree_widget_data()

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
        self.tree.itemSelectionChanged.connect(self._on_sample_selected)
        self.samples.updated.connect(self.update_tree_widget_data)
        self.btn_new.clicked.connect(self._new_sample_btn_clicked)
        self.btn_duplicate.clicked.connect(self._duplicate_sample_btn_clicked)
        self.btn_cancel.clicked.connect(self._cancel_changes_btn_clicked)
        self.live_edit = LiveEditDelegate(self.on_text_changed, self.table)
        self.table.setItemDelegate(self.live_edit)


class LiveEditDelegate(QStyledItemDelegate):
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self.callback = callback

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        editor.textChanged.connect(
            lambda text: self.callback(index.row(), index.column(), text)
        )
        return editor

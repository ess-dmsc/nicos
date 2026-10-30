from copy import deepcopy

from nicos.guisupport.qt import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyledItemDelegate,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from nicos_ess.gui.panels.panel import PanelBase


class SamplePanel(PanelBase):
    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)

        self.samples = []
        self.edit_ongoing = False
        self._build_ui()
        self.initialise_connection_status_listeners()

    def load_sample_data(self, data=None):
        if data is not None:
            self.samples = [dict(x) for x in data.values()]
        else:
            self.samples = self.client.eval("session.experiment.get_samples()")

    def save_sample_data(self, samples):
        self.client.run(f"Exp.set_samples({samples})")

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.register(self, "sample/samples")

    def on_keyChange(self, key, value, time, expired):
        if key == "sample/samples":
            self.load_sample_data(value)
            self.update_tree_widget_data()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self.load_sample_data()
        self.update_tree_widget_data()

    def update_tree_widget_data(self):
        self.tree.clear()
        for i, sample in enumerate(self.samples):
            item = QTreeWidgetItem(self.tree, [sample["name"]])
            item.setData(0, Qt.ItemDataRole.UserRole, i)

    def _add_table_data(self, data):
        data = deepcopy(data)
        sample = data.pop("name")
        self.sample_edit.setText(str(sample))
        for i, (key, value) in enumerate(data.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _on_sample_selected(self):
        self.table.clearContents()
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if index < len(self.samples):
            self._add_table_data(self.samples[index])

    def on_text_changed(self, row, col, text):
        if self.edit_ongoing:
            self.changes_label.setText("Changes made to samples, save or cancel")
            if row == 0 and col == 1:
                selected_item = self.tree.selectedItems()[0]
                selected_item.setText(0, text)

    def on_sample_name_changed(self, text):
        self.changes_label.setText("Changes made to samples, save or cancel")
        selected_item = self.tree.selectedItems()[0]
        selected_item.setText(0, text)

    def _new_sample_btn_clicked(self):
        self.edit_ongoing = True
        self.changes_label.setText("Changes made to samples, save or cancel")
        new_sample_index = len(self.samples)
        item = QTreeWidgetItem(self.tree, ["Sample"])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)
        self.table.clearContents()
        self.table.setItem(0, 0, QTableWidgetItem("name"))
        self.table.setItem(0, 1, QTableWidgetItem("Sample"))

    def _duplicate_sample_btn_clicked(self):
        self.edit_ongoing = True
        self.changes_label.setText("Changes made to samples, save or cancel")
        sample_to_duplicate = self.tree.selectedItems()[0]
        index = sample_to_duplicate.data(0, Qt.ItemDataRole.UserRole)
        name = sample_to_duplicate.text(0)
        new_sample_index = len(self.samples)
        item = QTreeWidgetItem(self.tree, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)
        self._add_table_data(self.samples[index])

    def _save_btn_clicked(self):
        sample_data = self.samples
        edited_index = self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)
        table_data = self._get_table_data()
        if edited_index < len(self.samples):
            sample_data[edited_index] = table_data
        else:
            sample_data.append(table_data)
        self.save_sample_data(sample_data)

    def _get_table_data(self):
        table_data = {}
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) is None:
                continue
            key = self.table.item(row, 0).text()
            val = self.table.item(row, 1).text()
            table_data[key] = val
        return table_data

    def _cancel_changes_btn_clicked(self):
        self.edit_ongoing = False
        self.changes_label.setText("")
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

        self.sample_label = QLabel("Sample:")
        self.sample_edit = QLineEdit()
        self.metadata_label = QLabel("Metadata:")
        self.table = QTableWidget()
        self.table.setRowCount(100)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.btn_edit = QPushButton("Edit")
        self.btn_save = QPushButton("Apply changes")
        self.btn_cancel = QPushButton("Discard changes")

        self.changes_label = QLabel()

    def _set_layout(self):
        tree_btn_layout = QHBoxLayout()
        tree_btn_layout.addWidget(self.btn_new)
        tree_btn_layout.addWidget(self.btn_duplicate)
        tree_btn_layout.addWidget(self.btn_remove)
        tree_btn_layout.addStretch()
        self.tree_layout = QVBoxLayout()
        self.tree_layout.addWidget(self.tree)
        self.tree_layout.addLayout(tree_btn_layout)

        table_header_layout = QHBoxLayout()
        table_header_layout.addWidget(self.sample_label)
        table_header_layout.addWidget(self.sample_edit)
        table_btn_layout = QHBoxLayout()
        table_btn_layout.addWidget(self.btn_edit)
        table_btn_layout.addWidget(self.btn_save)
        table_btn_layout.addWidget(self.btn_cancel)
        table_btn_layout.addStretch()
        table_btn_layout.addWidget(self.changes_label)
        self.table_layout = QVBoxLayout()
        self.table_layout.addLayout(table_header_layout)
        self.table_layout.addWidget(self.metadata_label)
        self.table_layout.addWidget(self.table)
        self.table_layout.addLayout(table_btn_layout)

        self.layout = QHBoxLayout()
        self.layout.addLayout(self.tree_layout)
        self.layout.addLayout(self.table_layout)
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
        self.changes_label.setStyleSheet("color: red; font-weight: bold;")
        self.sample_label.setStyleSheet("font-weight: bold;")
        self.metadata_label.setStyleSheet("font-weight: bold;")
        self.tree_layout.setContentsMargins(0, 0, 20, 0)

    def _add_signals(self):
        self.tree.itemSelectionChanged.connect(self._on_sample_selected)
        # self.samples.updated.connect(self.update_tree_widget_data)
        self.btn_new.clicked.connect(self._new_sample_btn_clicked)
        self.btn_duplicate.clicked.connect(self._duplicate_sample_btn_clicked)
        self.btn_save.clicked.connect(self._save_btn_clicked)
        self.btn_cancel.clicked.connect(self._cancel_changes_btn_clicked)
        self.table_live_edit = LiveEditDelegate(self.on_text_changed, self.table)
        self.table.setItemDelegate(self.table_live_edit)
        self.sample_edit.textEdited.connect(self.on_sample_name_changed)


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

from copy import deepcopy

from nicos.guisupport.qt import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
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

        self.applied_samples = []
        self.pending_samples = []
        self._build_ui()
        self.ignore_table_changes = False
        self._on_sample_selected()  # start with nothing selected
        self.initialise_connection_status_listeners()

    def set_sample_data(self, data):
        self.applied_samples = data
        self.pending_samples = deepcopy(self.applied_samples)

    def save_sample_data(self, samples):
        # Setting the samples will trigger an on_keyChange.
        self.client.run(f"Exp.set_samples({samples})")

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.register(self, "sample/samples")

    def on_keyChange(self, key, value, time, expired):
        if key == "sample/samples":
            self.set_sample_data([dict(x) for x in value.values()])
            self.update_tree_widget_data()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self.set_sample_data(self.client.eval("session.experiment.get_samples()"))
        self.update_tree_widget_data()

    def has_changes(self):
        return self.pending_samples != self.applied_samples

    def _update_reminder_label(self):
        if self.has_changes():
            self.apply_reminder_label.setText(
                "Changes to the samples have not been applied!"
            )
        else:
            self.apply_reminder_label.setText("")

    def _update_enabled_widgets(self):
        has_selection = bool(self.tree.selectedItems())
        self.txt_sample_name.setEnabled(has_selection)
        self.table.setEnabled(has_selection)
        self.btn_duplicate.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def update_tree_widget_data(self):
        selected_row = self.tree.indexOfTopLevelItem(self.tree.currentItem())
        self.tree.clear()
        for i, sample in enumerate(self.pending_samples):
            item = QTreeWidgetItem(self.tree, [sample["name"]])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
        self._on_sample_selected()
        self.tree.setCurrentItem(self.tree.topLevelItem(selected_row))

    def _populate_table(self, data):
        data = deepcopy(data)

        sample = data.pop("name")
        self.txt_sample_name.setText(str(sample))
        for i, (key, value) in enumerate(data.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _on_sample_selected(self):
        self.ignore_table_changes = True
        self.table.clearContents()
        self.txt_sample_name.clear()
        selected_items = self.tree.selectedItems()
        if selected_items:
            index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if index < len(self.pending_samples):
                self._populate_table(self.pending_samples[index])
        self._update_reminder_label()
        self._update_enabled_widgets()
        self.ignore_table_changes = False

    def on_sample_name_changed(self, text):
        selected_item = self.tree.selectedItems()[0]
        selected_item.setText(0, text)
        index = selected_item.data(0, Qt.ItemDataRole.UserRole)
        self.pending_samples[index]["name"] = text
        self._update_reminder_label()

    def on_table_item_changed(self, item):
        if self.ignore_table_changes:
            return
        index = self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)
        name = self.pending_samples[index]["name"]
        self.pending_samples[index] = {"name": name, **self._get_table_data()}
        self._update_reminder_label()

    def _new_sample_btn_clicked(self):
        new_sample_index = len(self.pending_samples)
        new_name = "untitled"
        self.pending_samples.append({"name": new_name})

        item = QTreeWidgetItem(self.tree, [new_name])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)

    def _duplicate_sample_btn_clicked(self):
        sample_to_duplicate = self.tree.selectedItems()[0]
        index = sample_to_duplicate.data(0, Qt.ItemDataRole.UserRole)
        name = sample_to_duplicate.text(0)
        new_sample_index = len(self.pending_samples)

        self.pending_samples.append(deepcopy(self.pending_samples[index]))
        self.pending_samples[~0]["name"] = name

        item = QTreeWidgetItem(self.tree, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, new_sample_index)
        self.tree.setCurrentItem(item)

    def _apply_changes_btn_clicked(self):
        if self._has_duplicate_property_names():
            self.showError("Please make sure no metadata has the same property name")
            return
        self.save_sample_data(self.pending_samples)

    def _has_duplicate_property_names(self):
        cells = [self.table.item(row, 0) for row in range(self.table.rowCount())]
        names = [cell.text() for cell in cells if cell is not None]
        return len(names) != len(set(names))

    def _get_table_data(self):
        table_data = {}
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) is None:
                continue
            key = self.table.item(row, 0).text()
            val_item = self.table.item(row, 1)
            val = val_item.text() if val_item else ""
            table_data[key] = val
        return table_data

    def _discard_changes_btn_clicked(self):
        self.pending_samples = deepcopy(self.applied_samples)
        self.update_tree_widget_data()

    def _delete_sample_btn_clicked(self):
        selected_item = self.tree.selectedItems()[0]
        index = selected_item.data(0, Qt.ItemDataRole.UserRole)

        del self.pending_samples[index]
        self.update_tree_widget_data()
        new_index = max(index - 1, 0)
        self.tree.setCurrentItem(self.tree.topLevelItem(new_index))

    def _build_ui(self):
        self._create_widgets()
        self._set_layout()
        self._format_layout()
        self._add_signals()

    def _create_widgets(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Samples")
        self.btn_new = QPushButton("New")
        self.btn_delete = QPushButton("Delete")
        self.btn_duplicate = QPushButton("Duplicate")

        self.sample_label = QLabel("Sample:")
        self.txt_sample_name = QLineEdit()
        self.metadata_label = QLabel("Metadata:")
        self.table = QTableWidget()
        self.table.setRowCount(100)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.btn_apply_changes = QPushButton("Apply changes")
        self.btn_discard_changes = QPushButton("Discard changes")

        self.apply_reminder_label = QLabel()

    def _set_layout(self):
        tree_btn_layout = QHBoxLayout()
        tree_btn_layout.addWidget(self.btn_new)
        tree_btn_layout.addWidget(self.btn_duplicate)
        tree_btn_layout.addWidget(self.btn_delete)
        tree_btn_layout.addStretch()
        self.tree_layout = QVBoxLayout()
        self.tree_layout.addWidget(self.tree)
        self.tree_layout.addLayout(tree_btn_layout)

        table_header_layout = QHBoxLayout()
        table_header_layout.addWidget(self.sample_label)
        table_header_layout.addWidget(self.txt_sample_name)
        table_btn_layout = QHBoxLayout()
        table_btn_layout.addStretch()
        table_btn_layout.addWidget(self.btn_apply_changes)
        table_btn_layout.addWidget(self.btn_discard_changes)
        self.table_layout = QVBoxLayout()
        self.table_layout.addLayout(table_header_layout)
        self.table_layout.addWidget(self.metadata_label)
        self.table_layout.addWidget(self.table)
        self.table_layout.addWidget(self.apply_reminder_label)
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
        self.btn_apply_changes.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.apply_reminder_label.setStyleSheet("color: red; font-weight: bold;")
        self.apply_reminder_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.sample_label.setStyleSheet("font-weight: bold;")
        self.metadata_label.setStyleSheet("font-weight: bold;")
        self.tree_layout.setContentsMargins(0, 0, 20, 0)

    def _add_signals(self):
        self.tree.itemSelectionChanged.connect(self._on_sample_selected)
        self.btn_new.clicked.connect(self._new_sample_btn_clicked)
        self.btn_duplicate.clicked.connect(self._duplicate_sample_btn_clicked)
        self.btn_delete.clicked.connect(self._delete_sample_btn_clicked)
        self.btn_apply_changes.clicked.connect(self._apply_changes_btn_clicked)
        self.btn_discard_changes.clicked.connect(self._discard_changes_btn_clicked)
        self.txt_sample_name.textEdited.connect(self.on_sample_name_changed)
        self.table.itemChanged.connect(self.on_table_item_changed)

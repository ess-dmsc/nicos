from copy import deepcopy

from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QListWidgetItem, Qt, QTableWidgetItem
from nicos.utils import findResource
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
            self.update_list_widget_data()

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self.set_sample_data(self.client.eval("session.experiment.get_samples()"))
        self.update_list_widget_data()

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
        has_selection = bool(self.list.selectedItems())
        self.txt_sample_name.setEnabled(has_selection)
        self.table.setEnabled(has_selection)
        self.btn_duplicate.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def update_list_widget_data(self):
        selected_row = self.list.currentRow()
        self.list.clear()
        for i, sample in enumerate(self.pending_samples):
            item = QListWidgetItem(sample["name"])
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list.addItem(item)
        self._on_sample_selected()
        self.list.setCurrentRow(selected_row)

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
        selected_items = self.list.selectedItems()
        if selected_items:
            index = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if index < len(self.pending_samples):
                self._populate_table(self.pending_samples[index])
        self._update_reminder_label()
        self._update_enabled_widgets()
        self.ignore_table_changes = False

    def on_sample_name_changed(self, text):
        selected_item = self.list.selectedItems()[0]
        selected_item.setText(text)
        index = selected_item.data(Qt.ItemDataRole.UserRole)
        self.pending_samples[index]["name"] = text
        self._update_reminder_label()

    def on_table_item_changed(self, item):
        if self.ignore_table_changes:
            return
        index = self.list.currentItem().data(Qt.ItemDataRole.UserRole)
        name = self.pending_samples[index]["name"]
        self.pending_samples[index] = {"name": name, **self._get_table_data()}
        self._update_reminder_label()

    def _new_sample_btn_clicked(self):
        new_sample_index = len(self.pending_samples)
        new_name = "untitled"
        self.pending_samples.append({"name": new_name})

        item = QListWidgetItem(new_name)
        item.setData(Qt.ItemDataRole.UserRole, new_sample_index)
        self.list.addItem(item)
        self.list.setCurrentItem(item)

    def _duplicate_sample_btn_clicked(self):
        sample_to_duplicate = self.list.currentItem()
        index = sample_to_duplicate.data(Qt.ItemDataRole.UserRole)
        name = sample_to_duplicate.text()
        new_sample_index = len(self.pending_samples)

        self.pending_samples.append(deepcopy(self.pending_samples[index]))
        self.pending_samples[~0]["name"] = name

        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, new_sample_index)
        self.list.addItem(item)
        self.list.setCurrentItem(item)

    def _apply_changes_btn_clicked(self):
        if self._has_duplicate_property_names():
            self.showError("Please make sure no metadata has the same property name.")
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
        self.update_list_widget_data()

    def _delete_sample_btn_clicked(self):
        selected_item = self.list.currentItem()
        index = selected_item.data(Qt.ItemDataRole.UserRole)

        del self.pending_samples[index]
        self.update_list_widget_data()
        new_index = max(index - 1, 0)
        self.list.setCurrentRow(new_index)

    def _build_ui(self):
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/samples.ui"))
        self.table.setColumnWidth(0, 200)
        self._add_signals()

    def _add_signals(self):
        self.list.itemSelectionChanged.connect(self._on_sample_selected)
        self.btn_new.clicked.connect(self._new_sample_btn_clicked)
        self.btn_duplicate.clicked.connect(self._duplicate_sample_btn_clicked)
        self.btn_delete.clicked.connect(self._delete_sample_btn_clicked)
        self.btn_apply_changes.clicked.connect(self._apply_changes_btn_clicked)
        self.btn_discard_changes.clicked.connect(self._discard_changes_btn_clicked)
        self.txt_sample_name.textEdited.connect(self.on_sample_name_changed)
        self.table.itemChanged.connect(self.on_table_item_changed)

from copy import copy

from nicos.guisupport.qt import (
    pyqtSignal,
    QListWidgetItem,
    Qt,
    QTableWidgetItem,
    QVBoxLayout,
)

from nicos_ess.gui.panels.panel import PanelBase

from nicos_ess.gui.widgets.sample_widgets import (
    AddSampleDialog,
    ErrorDialog,
    RemoveSampleDialog,
    SamplePanelWidgets,
)

DEFAULT_PROPERTIES = []
SAMPLE_IDENTIFIER_KEY = "name"


class SamplePanel(PanelBase):
    panelName = "Sample info panel"
    samples_edited = pyqtSignal(object)

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options
        self.to_monitor = ["sample/samples"]

        self.old_sample_info = []
        self.new_sample_info = []

        self._in_edit_mode = False
        self._properties_in_edit = {}
        self._tentative_new_sample = None
        self._table_selected_row = None

        self.widgets = SamplePanelWidgets()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.widgets.sample_panel_widget)
        self.setLayout(self.layout)
        self.connect_signals()
        self.initialise_connection_status_listeners()

    @property
    def in_edit_mode(self):
        return self._in_edit_mode

    @in_edit_mode.setter
    def in_edit_mode(self, value):
        self._in_edit_mode = value
        self.samples_edited.emit(value)

    def add_sample_btn_clicked(self):
        self._create_add_dialog()
        self.widgets.add_dialog.exec()

    def confirm_add(self):
        new_sample_id = self._get_new_sample_id()
        valid_check = self._valid_new_sample(new_sample_id)
        if valid_check[0] is True:
            self._add_empty_sample(new_sample_id)
            self._add_sample_id_to_selector(new_sample_id)
            self._select_sample(new_sample_id)
            self.widgets.add_dialog.close()
            self._tentative_new_sample = new_sample_id
            self.edit_sample_clicked()
        else:
            self.widgets.add_dialog.message.setText(valid_check[1])

    def cancel_add(self):
        self.widgets.add_dialog.close()

    def remove_sample_btn_clicked(self):
        self._create_remove_dialog()
        selected_sample_id = self._get_current_selected()
        label_text = f"Remove sample: '{selected_sample_id}'"
        self.widgets.remove_dialog.message.setText(label_text)
        self.widgets.remove_dialog.exec()

    def confirm_remove(self):
        self.in_edit_mode = True
        selected_sample_id = self._get_current_selected()
        self._remove_sample(selected_sample_id)
        self._remove_sample_values_from_table()
        self._remove_sample_id_from_selector(selected_sample_id)
        self.widgets.remove_dialog.close()
        self._check_for_changes()

    def cancel_remove(self):
        self.widgets.remove_dialog.close()

    def edit_sample_clicked(self):
        self._hide_edit_customise_buttons()
        self._show_edit_control_buttons()
        self._lock_sample_selector()
        nrows = self._number_of_rows_in_table()
        for i in range(nrows):
            item = self._get_table_item(i, self.widgets.VALUE_COL_INDEX)
            self.editable_item(item)

    def save_edit_clicked(self):
        self.in_edit_mode = True
        new_id = self._get_table_cell_text(0, self.widgets.VALUE_COL_INDEX)
        old_id = self._get_current_selected()
        if new_id != old_id:
            valid_check = self._valid_new_sample(new_id)
            if valid_check[0] is True:
                self._replace_sample_id_in_selector(old_id, new_id)
            else:
                self._show_error_dialog(valid_check[1])
                return
        self._tentative_new_sample = None
        self._update_sample_after_edit(old_id, new_id)
        self._select_sample(new_id)
        self._hide_edit_control_buttons()
        self._show_edit_customise_buttons()
        self._make_table_read_only()
        self._unlock_sample_selector()
        self._check_for_changes()

    def customise_clicked(self):
        self._hide_edit_customise_buttons()
        self._show_customise_control_buttons()
        self._lock_sample_selector()
        self._store_properties_before_edit()
        self._make_properties_editable()
        self._remove_sample_values_from_table()
        self.widgets.create_add_row_button(self.add_row_clicked)
        self.widgets.create_delete_row_button(self.delete_row_clicked)
        self._insert_table_row()
        self._add_button_to_last_row()

    def add_row_clicked(self):
        if self._table_selected_row:
            self._remove_button_from_previously_selected_row(self._table_selected_row)
        self._remove_button_from_last_row()
        self._insert_table_row()
        self._make_properties_editable()
        self._add_button_to_last_row()
        self.widgets.create_add_row_button(self.add_row_clicked)
        self._add_button_to_last_row()
        self._clear_table_selection()

    def delete_row_clicked(self):
        row = self._get_selected_row()
        i = row - 1
        if len(self._properties_in_edit) > i:
            key = list(self._properties_in_edit.keys())[i]
            self._properties_in_edit.pop(key)
        self._delete_table_row(row)
        self._clear_table_selection()

    def save_prop_clicked(self):
        self.in_edit_mode = True
        self._hide_customise_control_buttons()
        self._show_edit_customise_buttons()
        self._unlock_sample_selector()
        self._make_table_read_only()
        if self._table_selected_row:
            self._remove_button_from_previously_selected_row(self._table_selected_row)
        self._remove_button_from_last_row()
        self._delete_empty_table_rows()
        self._update_sample_properties()
        selected_sample_id = self._get_current_selected()
        if selected_sample_id:
            sample = self.get_loaded_sample(selected_sample_id)
            self._add_sample_to_table(sample)
            self._enable_remove_and_edit_buttons(True)
        else:
            self._enable_remove_and_edit_buttons(False)
        self._check_for_changes()

    def cancel_clicked(self):
        self._hide_edit_control_buttons()
        self._hide_customise_control_buttons()
        self._show_edit_customise_buttons()
        if self._table_selected_row:
            self._remove_button_from_previously_selected_row(self._table_selected_row)
        self._remove_button_from_last_row()
        self._add_properties_to_table()
        selected_sample_id = self._get_current_selected()
        if selected_sample_id:
            if self._tentative_new_sample:
                self._remove_sample_id_from_selector(self._tentative_new_sample)
                self._remove_sample_values_from_table()
                self._tentative_new_sample = None
                self.selection_updated()
            else:
                sample = self.get_loaded_sample(selected_sample_id)
                self._add_sample_to_table(sample)
                self._enable_remove_and_edit_buttons(True)
        else:
            self._remove_sample_values_from_table()
            self._enable_remove_and_edit_buttons(False)
        self._delete_empty_table_rows()
        self._make_table_read_only()
        self._unlock_sample_selector()

    def selection_updated(self):
        self.empty_table_values()
        selected_sample_id = self._get_current_selected()
        if selected_sample_id:
            sample = self.get_loaded_sample(selected_sample_id)
            self._add_sample_to_table(sample)
            self._enable_remove_and_edit_buttons(True)
        else:
            self._enable_remove_and_edit_buttons(False)

    def table_cell_clicked(self, row, col):
        if self.widgets.btn_save_prop.isVisible():
            if self._table_selected_row:
                self._remove_button_from_previously_selected_row(
                    self._table_selected_row
                )
            self._table_selected_row = row
            if row == 0 or col == self.widgets.VALUE_COL_INDEX:
                return
            nrows = self._number_of_rows_in_table()
            if row != 0 and row < nrows - 1:
                self.widgets.create_delete_row_button(self.delete_row_clicked)
                self._add_button_to_selected_row(row)

    def connect_signals(self):
        self.widgets.btn_add.clicked.connect(self.add_sample_btn_clicked)
        self.widgets.btn_remove.clicked.connect(self.remove_sample_btn_clicked)
        self.widgets.btn_edit.clicked.connect(self.edit_sample_clicked)
        self.widgets.btn_custom.clicked.connect(self.customise_clicked)
        self.widgets.btn_save_edit.clicked.connect(self.save_edit_clicked)
        self.widgets.btn_save_prop.clicked.connect(self.save_prop_clicked)
        self.widgets.btn_cancel.clicked.connect(self.cancel_clicked)
        self.widgets.selector.itemSelectionChanged.connect(self.selection_updated)
        self.widgets.info_table.cellClicked.connect(self.table_cell_clicked)
        self.widgets.btn_apply.clicked.connect(self.apply_changes)
        self.widgets.btn_discard.clicked.connect(self.discard_changes)

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def on_client_connected(self):
        PanelBase.on_client_connected(self)
        self._button_behaviour_on_connect()

    def on_client_disconnected(self):
        self._in_edit_mode = False
        self._clear_table()
        self._clear_selector()
        self._clear_data()
        PanelBase.on_client_disconnected(self)

    def setViewOnly(self, viewonly):
        self.widgets.btn_add.setEnabled(not viewonly)
        self.widgets.btn_remove.setEnabled(not viewonly)
        self.widgets.btn_edit.setEnabled(not viewonly)
        self.widgets.btn_custom.setEnabled(not viewonly)
        self.widgets.btn_save_edit.setEnabled(not viewonly)
        self.widgets.btn_save_prop.setEnabled(not viewonly)
        self.widgets.btn_cancel.setEnabled(not viewonly)
        self.widgets.selector.setEnabled(not viewonly)
        self.widgets.info_table.setEnabled(not viewonly)
        self._set_buttons_and_warning_behaviour(False)

    def _check_for_changes(self):
        has_changed = self.new_sample_info != self.old_sample_info
        self._set_buttons_and_warning_behaviour(has_changed)

    def apply_changes(self):
        if self.mainwindow.current_status != "idle":
            self.showInfo("Cannot change settings while a script is running!")
            return
        try:
            self._set_samples()
            self._set_buttons_and_warning_behaviour(False)
        except Exception as error:
            self.showError(str(error))

    def discard_changes(self):
        self.load_samples()
        self._check_for_changes()

    def _set_buttons_and_warning_behaviour(self, changed):
        self.widgets.btn_apply.setEnabled(changed)
        self.widgets.btn_discard.setEnabled(changed)
        self.widgets.label_warning.setVisible(changed)

    def _button_behaviour_on_connect(self):
        self.widgets.btn_remove.setEnabled(False)
        self.widgets.btn_edit.setEnabled(False)

    def on_keyChange(self, key, value, time, expired):
        print("key change, key:", key)
        if not self.in_edit_mode and key in self.to_monitor:
            self.load_samples()

    def load_samples(self, samples=None):
        self.old_sample_info = samples if samples else self._get_samples()
        self.new_sample_info = copy(self.old_sample_info)
        self._set_starting_properties()
        if len(self.new_sample_info) > 0:
            self._add_all_sample_ids_to_selector()

    def _get_samples(self):
        samples = self.client.eval("session.experiment.get_samples()", {})
        if len(samples) != 0:
            return samples
        else:
            return []

    def _set_samples(self):
        if self.new_sample_info == self.old_sample_info:
            return
        samples = {}
        for index, sample in enumerate(self.new_sample_info):
            if not sample.get("name", ""):
                sample["name"] = f"sample {index + 1}"
            samples[index] = sample
        self.client.run(f"Exp.sample.set_samples({dict(samples)})")

    def get_loaded_sample(self, sample_id):
        for sample in self.new_sample_info:
            if sample[SAMPLE_IDENTIFIER_KEY] == sample_id:
                return sample

    def _clear_table(self):
        self.widgets.info_table.setRowCount(0)

    def _clear_selector(self):
        self.widgets.selector.clear()

    def _clear_data(self):
        self.old_sample_info = []
        self.new_sample_info = []
        self._sample_properties = []
        self._properties_in_edit = {}
        self._table_selected_row = None

    def _create_add_dialog(self):
        self.widgets.add_dialog = AddSampleDialog()
        self.widgets.add_dialog.button_box.accepted.connect(self.confirm_add)
        self.widgets.add_dialog.button_box.rejected.connect(self.cancel_add)

    def _create_remove_dialog(self):
        self.widgets.remove_dialog = RemoveSampleDialog()
        self.widgets.remove_dialog.button_box.accepted.connect(self.confirm_remove)
        self.widgets.remove_dialog.button_box.rejected.connect(self.cancel_remove)

    def _create_error_dialog(self):
        self.widgets.error_dialog = ErrorDialog()
        self.widgets.error_dialog.button_box.accepted.connect(self._close_error_dialog)

    def _show_error_dialog(self, message):
        self._create_error_dialog()
        self.widgets.error_dialog.message.setText(message)
        self.widgets.error_dialog.exec()

    def _close_error_dialog(self):
        self.widgets.error_dialog.close()

    def _store_properties_before_edit(self):
        self._properties_in_edit = {}
        for i in range(1, self._number_of_rows_in_table()):
            prop = self._get_table_cell_text(i, self.widgets.PROPERTY_COL_INDEX)
            self._properties_in_edit[i] = prop

    def _update_sample_after_edit(self, old_id, new_id):
        sample = {SAMPLE_IDENTIFIER_KEY: new_id}
        for i in range(1, self._number_of_rows_in_table()):
            key = self._get_table_cell_text(i, self.widgets.PROPERTY_COL_INDEX)
            val = self._get_table_cell_text(i, self.widgets.VALUE_COL_INDEX)
            sample[key] = val
        self._remove_sample(old_id)
        self._add_sample(sample)

    def _update_sample_properties(self):
        updated_properties = self._get_properties_from_table()
        self._sample_properties = updated_properties
        updated_samples = []
        for sample in self.new_sample_info:
            updated_sample = self._get_sample_with_new_properties(
                sample, updated_properties
            )
            updated_samples.append(updated_sample)
        self.new_sample_info = updated_samples

    def _get_sample_with_new_properties(self, sample, updated_properties):
        updated_sample = {}
        new_property_counter = 0
        for i, (k, v) in enumerate(sample.items()):
            if i == 0:
                updated_sample[k] = v
                continue
            if i in self._properties_in_edit.keys():
                new_key = updated_properties[new_property_counter]
                updated_sample[new_key] = v
                new_property_counter += 1
        if len(updated_properties) > len(self._properties_in_edit):
            new_properties = updated_properties[len(self._properties_in_edit) :]
            for p in new_properties:
                updated_sample[p] = ""
        return updated_sample

    def _get_default_properties(self):
        return DEFAULT_PROPERTIES

    def _get_properties_from_loaded_sample(self):
        sample = self.new_sample_info[0]
        properties = [
            prop for prop in sample.keys() if not prop == SAMPLE_IDENTIFIER_KEY
        ]
        return properties

    def _get_properties_from_table(self):
        properties = []
        if self._number_of_rows_in_table() > 1:
            for i in range(1, self._number_of_rows_in_table()):
                prop = self._get_table_cell_text(i, self.widgets.PROPERTY_COL_INDEX)
                properties.append(prop)
        return properties

    def _get_new_sample_id(self):
        return self.widgets.add_dialog.sample_id.text()

    def _valid_new_sample(self, sample_id):
        if sample_id == "":
            return False, "Please add a sample id"
        elif sample_id in self.get_existing_selector_items():
            return False, "Sample already exist"
        return True, ""

    def _add_empty_sample(self, sample_id):
        new_sample = {SAMPLE_IDENTIFIER_KEY: sample_id}
        properties = self._get_properties_from_table()
        if len(properties) > 0:
            for prop in properties:
                new_sample[prop] = ""
        self._add_sample(new_sample)

    def _add_sample(self, sample):
        self.new_sample_info.append(sample)

    def _remove_sample(self, sample_id):
        for i, sample in enumerate(self.new_sample_info):
            if sample[SAMPLE_IDENTIFIER_KEY] == sample_id:
                del self.new_sample_info[i]
                break

    def _add_all_sample_ids_to_selector(self):
        self.widgets.selector.clear()
        for sample in self.new_sample_info:
            sample_id = sample[SAMPLE_IDENTIFIER_KEY]
            self._add_sample_id_to_selector(sample_id)

    def _replace_sample_id_in_selector(self, old_id, new_id):
        self._remove_sample_id_from_selector(old_id)
        self._add_sample_id_to_selector(new_id)

    def _add_sample_id_to_selector(self, sample_id):
        item = QListWidgetItem(sample_id)
        self.widgets.selector.addItem(item)

    def _remove_sample_id_from_selector(self, sample_id):
        row = self._get_cell_row_with_matching_text(sample_id)
        self.widgets.selector.takeItem(row)

    def _select_sample(self, sample_id):
        item = self.widgets.selector.findItems(sample_id, Qt.MatchExactly)
        self.widgets.selector.setCurrentItem(item[0])

    def _get_current_selected(self):
        selected_items = self.widgets.selector.selectedItems()
        if len(selected_items) != 0:
            return selected_items[0].text()

    def get_existing_selector_items(self):
        return [
            self.widgets.selector.item(x).text()
            for x in range(self.widgets.selector.count())
        ]

    def _set_starting_properties(self):
        if len(self.new_sample_info) > 0:
            properties = self._get_properties_from_loaded_sample()
        else:
            properties = self._get_default_properties()
        self._sample_properties = properties
        keys = [SAMPLE_IDENTIFIER_KEY] + properties
        for i, prop in enumerate(keys):
            self._insert_table_row()
            self._set_table_cell_text(prop, i, self.widgets.PROPERTY_COL_INDEX)

    def _add_properties_to_table(self):
        keys = [SAMPLE_IDENTIFIER_KEY] + self._sample_properties
        for i, prop in enumerate(keys):
            if i >= self._number_of_rows_in_table():
                self._insert_table_row()
            self._set_table_cell_text(prop, i, self.widgets.PROPERTY_COL_INDEX)

    def _add_sample_to_table(self, sample):
        row_count = self.widgets.info_table.rowCount()
        for i, (key, val) in enumerate(sample.items()):
            if i >= row_count:
                self.widgets.info_table.insertRow(i)
            key_item = self.read_only_item(QTableWidgetItem(key))
            val_item = self.read_only_item(QTableWidgetItem(val))
            self.widgets.info_table.setItem(
                i, self.widgets.PROPERTY_COL_INDEX, key_item
            )
            self.widgets.info_table.setItem(i, self.widgets.VALUE_COL_INDEX, val_item)

    def _make_properties_editable(self):
        nrows = self._number_of_rows_in_table()
        for i in range(1, nrows):
            self._make_table_cell_editable(i, self.widgets.PROPERTY_COL_INDEX)

    def _remove_sample_values_from_table(self):
        nrows = self._number_of_rows_in_table()
        for i in range(nrows):
            self._set_table_cell_text("", i, self.widgets.VALUE_COL_INDEX)

    def _delete_empty_table_rows(self):
        empty_rows = []
        for row in range(1, self._number_of_rows_in_table()):
            key = self._get_table_cell_text(row, self.widgets.PROPERTY_COL_INDEX)
            if key == "":
                empty_rows.append(row)
        if len(empty_rows) > 0:
            for row in sorted(empty_rows, reverse=True):
                self._delete_table_row(row)

    def _add_button_to_last_row(self):
        row = self._number_of_rows_in_table() - 1
        self._set_table_cell_widget(
            self.widgets.add_row_btn, row, self.widgets.PROPERTY_COL_INDEX
        )

    def _remove_button_from_last_row(self):
        row = self._number_of_rows_in_table() - 1
        self._delete_table_cell_widget(row, self.widgets.PROPERTY_COL_INDEX)

    def _add_button_to_selected_row(self, row):
        self._set_table_cell_widget(
            self.widgets.delete_row_btn, row, self.widgets.VALUE_COL_INDEX
        )

    def _remove_button_from_previously_selected_row(self, row):
        self._delete_table_cell_widget(row, self.widgets.VALUE_COL_INDEX)

    def _number_of_rows_in_table(self):
        return self.widgets.info_table.rowCount()

    def _get_selected_row(self):
        return self.widgets.info_table.currentRow()

    def _clear_table_selection(self):
        self.widgets.info_table.clearSelection()

    def _get_table_cell_text(self, row, col):
        item = self.widgets.info_table.item(row, col)
        if item:
            return item.text()
        else:
            return ""

    def _set_table_cell_text(self, text, row, col):
        item = self.read_only_item(QTableWidgetItem(text))
        self.widgets.info_table.setItem(row, col, item)

    def _make_table_cell_editable(self, row, col):
        self.editable_item(self.widgets.info_table.item(row, col))

    def _set_table_cell_widget(self, widget, row, col):
        self.widgets.info_table.setCellWidget(row, col, widget)

    def _delete_table_cell_widget(self, row, col):
        self.widgets.info_table.removeCellWidget(row, col)

    def _get_table_item(self, row, col):
        return self.widgets.info_table.item(row, col)

    def _get_cell_row_with_matching_text(self, text):
        items = self.widgets.selector.findItems(text, Qt.MatchExactly)
        if len(items) == 1:
            return self.widgets.selector.indexFromItem(items[0]).row()

    def _insert_table_row(self, i=None):
        if not i:
            i = self._number_of_rows_in_table()
        self.widgets.info_table.insertRow(i)
        self._set_table_cell_text("", i, self.widgets.PROPERTY_COL_INDEX)
        self._set_table_cell_text("", i, self.widgets.VALUE_COL_INDEX)

    def _delete_table_row(self, row):
        self.widgets.info_table.removeRow(row)

    def _make_table_read_only(self):
        for i in range(self.widgets.info_table.rowCount()):
            item_prop = self.widgets.info_table.item(i, self.widgets.PROPERTY_COL_INDEX)
            item_val = self.widgets.info_table.item(i, self.widgets.VALUE_COL_INDEX)
            self.read_only_item(item_prop)
            self.read_only_item(item_val)

    def empty_table_values(self):
        nrows = self._number_of_rows_in_table()
        if nrows == 0:
            return
        self.widgets.info_table.item(0, self.widgets.VALUE_COL_INDEX).setText("")

    def editable_item(self, item):
        item.setFlags(
            item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable
        )
        return item

    def read_only_item(self, item):
        item.setFlags(
            item.flags() & ~(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable)
        )
        return item

    def _show_edit_customise_buttons(self):
        self.widgets.btn_edit.show()
        self.widgets.btn_edit.setEnabled(True)
        self.widgets.btn_custom.show()
        self.widgets.btn_custom.setEnabled(True)

    def _hide_edit_customise_buttons(self):
        self.widgets.btn_edit.hide()
        self.widgets.btn_custom.hide()

    def _show_edit_control_buttons(self):
        self.widgets.btn_save_edit.show()
        self.widgets.btn_save_edit.setEnabled(True)
        self.widgets.btn_cancel.show()
        self.widgets.btn_cancel.setEnabled(True)

    def _hide_edit_control_buttons(self):
        self.widgets.btn_save_edit.hide()
        self.widgets.btn_cancel.hide()

    def _show_customise_control_buttons(self):
        self.widgets.btn_save_prop.show()
        self.widgets.btn_save_prop.setEnabled(True)
        self.widgets.btn_cancel.show()
        self.widgets.btn_cancel.setEnabled(True)

    def _hide_customise_control_buttons(self):
        self.widgets.btn_save_prop.hide()
        self.widgets.btn_cancel.hide()

    def _lock_sample_selector(self):
        self.widgets.selector.setEnabled(False)
        self.widgets.btn_add.setEnabled(False)
        self.widgets.btn_remove.setEnabled(False)

    def _unlock_sample_selector(self):
        self.widgets.selector.setEnabled(True)
        self.widgets.btn_add.setEnabled(True)
        self.widgets.btn_remove.setEnabled(True)

    def _enable_remove_and_edit_buttons(self, flag=True):
        self.widgets.btn_remove.setEnabled(flag)
        self.widgets.btn_edit.setEnabled(flag)

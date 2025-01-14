from nicos.guisupport.qt import (
    QListWidgetItem,
    Qt,
    QTableWidgetItem,
    QVBoxLayout,
)

from nicos_ess.gui.panels.panel import PanelBase
from nicos_ess.gui.widgets.sample_widgets import (
    AddSampleDialog,
    RemoveSampleDialog,
    SamplePanelWidgets,
)

DEFAULT_PROPERTIES = ["A", "B", "C", "D"]
SAMPLE_IDENTIFIER_KEY = "name"


class SamplePanel(PanelBase):
    panelName = "Sample info panel"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options
        self.to_monitor = ["sample/samples"]
        self._in_edit_mode = False
        self._samples_loaded = None
        self._sample_properties = {}
        self._sample_properties_edit = {}
        self._table_selected_row = None
        self._add_row_flag = False
        self._mode = None

        self.widgets = SamplePanelWidgets()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.widgets.sample_panel_widget)
        self.setLayout(self.layout)
        self.connect_signals()
        self.initialise_connection_status_listeners()

    def add_sample_btn_clicked(self):
        self._create_add_dialog()
        self.widgets.add_dialog.exec()

    def confirm_add(self):
        new_sample_id = self._get_new_sample_id()
        valid_check = self._valid_new_sample(new_sample_id)
        if valid_check is True:
            self._add_empty_sample(new_sample_id)
            self._add_sample_id_to_selector(new_sample_id)
            self._select_sample(new_sample_id)
            self.widgets.add_dialog.close()
        else:
            self.widgets.add_dialog.message.setText(valid_check)

    def cancel_add(self):
        self.widgets.add_dialog.close()

    def remove_sample_btn_clicked(self):
        self._create_remove_dialog()
        selected_sample_id = self._get_current_selected()
        label_text = f"Remove sample: '{selected_sample_id}'"
        self.widgets.remove_dialog.message.setText(label_text)
        self.widgets.remove_dialog.exec()

    def confirm_remove(self):
        selected_sample_id = self._get_current_selected()
        self._remove_sample(selected_sample_id)
        self._remove_sample_id_from_selector(selected_sample_id)
        self.widgets.remove_dialog.close()

    def cancel_remove(self):
        self.widgets.remove_dialog.close()

    def edit_sample_clicked(self):
        nrows = self._number_of_rows_in_table()
        for i in range(nrows):
            item = self._get_table_item(i, self.widgets.VALUE_COL_INDEX)
            self.editable_item(item)

    def customise_clicked(self):
        self._mode = "customise"
        self._save_properties_before_edit()
        self._make_properties_editable()
        self._remove_sample_values_from_table()
        self.widgets.create_add_row_button(self.add_row_clicked)
        self.widgets.create_delete_row_button(self.delete_row_clicked)
        self._insert_table_row()
        self._add_button_to_last_row()

    def _save_properties_before_edit(self):
        nrows = self._number_of_rows_in_table()
        properties = {}
        for i in range(1, nrows):
            prop = self._get_table_cell_text(i, self.widgets.PROPERTY_COL_INDEX)
            properties[i] = prop
        self._sample_properties = properties
        self._sample_properties_edit = properties

    def table_cell_clicked(self, row, col):
        if self._mode != "customise":
            return
        if self._table_selected_row:
            self._remove_button_from_previously_selected_row(self._table_selected_row)
        self._table_selected_row = row
        if row == 0 or col == self.widgets.VALUE_COL_INDEX:
            return
        nrows = self._number_of_rows_in_table()
        if row != 0 and row < nrows - 1:
            self.widgets.create_delete_row_button(self.delete_row_clicked)
            self._add_button_to_selected_row(row)

    def _number_of_rows_in_table(self):
        return self.widgets.info_table.rowCount()

    def _make_properties_editable(self):
        nrows = self._number_of_rows_in_table()
        for i in range(1, nrows):
            self._make_table_cell_editable(i, self.widgets.PROPERTY_COL_INDEX)

    def _remove_sample_values_from_table(self):
        nrows = self._number_of_rows_in_table()
        for i in range(nrows):
            self._set_table_cell_text("", i, self.widgets.VALUE_COL_INDEX)

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
        self._delete_table_row(row)
        properties_edit = {}
        for key, val in self._sample_properties_edit.items():
            if key < row:
                properties_edit[key] = val
            elif key == row:
                continue
            else:
                properties_edit[key - 1] = val
        self._sample_properties_edit = properties_edit
        print(self._sample_properties_edit)
        self._clear_table_selection()

    # Sample.samples = {0: {"name": "S1", "A": "a1", "B": "b1", "C": "c1", "D": "d1"}, 1: {"name": "S2", "A": "a2", "B": "b2", "C": "c2", "D": "d2"}} # noqa

    def save_clicked(self):
        """
        update values in self._samples_in_edit
        make table non editable
        hide cancel and save buttons
        show edit and customize buttons
        """
        self._mode = None
        sample_id = self.widgets.info_table.item(0, self.widgets.VALUE_COL_INDEX).text()
        if sample_id:
            selected_sample_id = self._get_current_selected()
            sample = {SAMPLE_IDENTIFIER_KEY: sample_id}
            for i in range(1, self.widgets.info_table.rowCount()):
                key = self.widgets.info_table.item(
                    i, self.widgets.PROPERTY_COL_INDEX
                ).text()
                val = self.widgets.info_table.item(
                    i, self.widgets.VALUE_COL_INDEX
                ).text()
                sample[key] = val
            self._remove_sample(selected_sample_id)
            self.add_sample(sample)
            if sample_id != selected_sample_id:
                self._remove_sample_id_from_selector(selected_sample_id)
                self._add_sample_id_to_selector(sample_id)
                self._select_sample(sample_id)
        else:
            print(self._sample_properties_edit)

        self.make_table_read_only()

    def cancel_clicked(self):
        self._mode = None
        self.empty_table()
        selected_sample_id = self._get_current_selected()
        if selected_sample_id:
            sample = self.get_sample(selected_sample_id)
            self.add_sample_to_table(sample)

    def selection_updated(self):
        """
        if sample selected: add values to table
        if no sample selected: remove values from table
        """
        self.empty_table()
        selected_sample_id = self._get_current_selected()
        if selected_sample_id:
            sample = self.get_sample(selected_sample_id)
            self.add_sample_to_table(sample)

    def on_keyChange(self, key, value, time, expired):
        print("key change, key:", key)
        if not self._in_edit_mode and key in self.to_monitor:
            self._samples_loaded = self._get_samples()
            self._set_starting_properties()
            if len(self._samples_loaded) > 0:
                self.add_all_sample_ids_to_selector()
            # self._sample_properties = self._get_sample_properties()
            # for sample_property in self._sample_properties:
            #     self.add_property_to_table(sample_property)
            # self.load_sample_selector_items()
            # print(self._samples_in_edit)

    def _get_samples(self):
        samples = self.client.eval("session.experiment.get_samples()", {})
        if len(samples) != 0:
            return samples
        else:
            return []

    def add_all_sample_ids_to_selector(self):
        existing_items = self.get_existing_selector_items()
        for sample in self._samples_loaded:
            sample_id = sample[SAMPLE_IDENTIFIER_KEY]
            if sample_id not in existing_items:
                self._add_sample_id_to_selector(sample_id)

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def connect_signals(self):
        self.widgets.btn_add.clicked.connect(self.add_sample_btn_clicked)
        self.widgets.btn_remove.clicked.connect(self.remove_sample_btn_clicked)
        self.widgets.btn_edit.clicked.connect(self.edit_sample_clicked)
        self.widgets.btn_custom.clicked.connect(self.customise_clicked)
        self.widgets.btn_save.clicked.connect(self.save_clicked)
        self.widgets.btn_cancel.clicked.connect(self.cancel_clicked)
        self.widgets.selector.itemSelectionChanged.connect(self.selection_updated)
        self.widgets.btn_TEST_PRINT.clicked.connect(self.TEST_PRINT_CLICKED)
        self.widgets.info_table.cellClicked.connect(self.table_cell_clicked)

    def _set_starting_properties(self):
        properties = self._get_properties()
        keys = [SAMPLE_IDENTIFIER_KEY] + properties
        for i, prop in enumerate(keys):
            self._insert_table_row()
            self._set_table_cell_text(prop, i, self.widgets.PROPERTY_COL_INDEX)

    def _set_table_cell_text(self, text, row, col):
        item = self.read_only_item(QTableWidgetItem(text))
        self.widgets.info_table.setItem(row, col, item)

    def _set_table_cell_widget(self, widget, row, col):
        self.widgets.info_table.setCellWidget(row, col, widget)

    def _get_table_cell_text(self, row, col):
        item = self.widgets.info_table.item(row, col)
        if item:
            return item.text()

    def _get_selected_row(self):
        return self.widgets.info_table.currentRow()

    def _delete_table_cell_widget(self, row, col):
        self.widgets.info_table.removeCellWidget(row, col)

    def _make_table_cell_editable(self, row, col):
        self.editable_item(self.widgets.info_table.item(row, col))

    def _insert_table_row(self, i=None):
        if not i:
            i = self._number_of_rows_in_table()
        self.widgets.info_table.insertRow(i)
        self._set_table_cell_text("", i, self.widgets.PROPERTY_COL_INDEX)
        self._set_table_cell_text("", i, self.widgets.VALUE_COL_INDEX)

    def _delete_table_row(self, row):
        self.widgets.info_table.removeRow(row)

    def _clear_table_selection(self):
        self.widgets.info_table.clearSelection()

    def _create_add_dialog(self):
        self.widgets.add_dialog = AddSampleDialog()
        self.widgets.add_dialog.button_box.accepted.connect(self.confirm_add)
        self.widgets.add_dialog.button_box.rejected.connect(self.cancel_add)

    def _create_remove_dialog(self):
        self.widgets.remove_dialog = RemoveSampleDialog()
        self.widgets.remove_dialog.button_box.accepted.connect(self.confirm_remove)
        self.widgets.remove_dialog.button_box.rejected.connect(self.cancel_remove)

    def _get_new_sample_id(self):
        return self.widgets.add_dialog.sample_id.text()

    def _valid_new_sample(self, sample_id):
        if sample_id == "":
            return "Please add a sample id"
        # elif sample exist: return False
        return True

    def _add_empty_sample(self, sample_id):
        new_sample = {key: "" for key in self.get_all_sample_properties()}
        new_sample[SAMPLE_IDENTIFIER_KEY] = sample_id
        properties = self._get_properties()
        if len(properties) > 0:
            for prop in properties:
                new_sample[prop] = ""
        self.add_sample(new_sample)

    def _get_properties(self):
        properties = []
        if self._samples_loaded and len(self._samples_loaded) > 0:
            sample = self._samples_loaded[0]
            properties = [
                prop for prop in sample.keys() if prop != SAMPLE_IDENTIFIER_KEY
            ]
        else:
            if DEFAULT_PROPERTIES:
                properties = DEFAULT_PROPERTIES
        return properties

    def add_sample(self, sample):
        self._samples_loaded.append(sample)

    def _add_sample_id_to_selector(self, sample_id):
        item = QListWidgetItem(sample_id)
        self.widgets.selector.addItem(item)

    def add_sample_to_table(self, sample):
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

    def _select_sample(self, sample_id):
        item = self.widgets.selector.findItems(sample_id, Qt.MatchExactly)
        self.widgets.selector.setCurrentItem(item[0])

    def _get_current_selected(self):
        selected_items = self.widgets.selector.selectedItems()
        if len(selected_items) != 0:
            return selected_items[0].text()

    def _remove_sample(self, sample_id):
        for i, sample in enumerate(self._samples_loaded):
            if sample[SAMPLE_IDENTIFIER_KEY] == sample_id:
                del self._samples_loaded[i]
                break

    def _remove_sample_id_from_selector(self, sample_id):
        row = self._get_cell_row_with_matching_text(sample_id)
        self.widgets.selector.takeItem(row)

    def _get_table_item(self, row, col):
        return self.widgets.info_table.item(row, col)

    def _get_cell_row_with_matching_text(self, text):
        items = self.widgets.selector.findItems(text, Qt.MatchExactly)
        if len(items) == 1:
            return self.widgets.selector.indexFromItem(items[0]).row()

    def make_table_read_only(self):
        for i in range(self.widgets.info_table.rowCount()):
            item_prop = self.widgets.info_table.item(i, self.widgets.PROPERTY_COL_INDEX)
            item_val = self.widgets.info_table.item(i, self.widgets.VALUE_COL_INDEX)
            self.read_only_item(item_prop)
            self.read_only_item(item_val)

    def TEST_PRINT_CLICKED(self):
        print(self._samples_loaded)

    def get_sample(self, sample_id):
        for sample in self._samples_loaded:
            if sample[SAMPLE_IDENTIFIER_KEY] == sample_id:
                return sample

    def empty_table(self):
        nrows = self._number_of_rows_in_table()
        if nrows == 0:
            return
        self.widgets.info_table.item(0, self.widgets.VALUE_COL_INDEX).setText("")
        self.widgets.info_table.setRowCount(1)

    def get_existing_selector_items(self):
        return [
            self.widgets.selector.item(x).text()
            for x in range(self.widgets.selector.count())
        ]

    def get_any_item(self):
        item = self.widgets.selector.item(0)
        if item:
            return item.text()

    def clear_sample_selection(self):
        self.widgets.selector.clearSelection()

    # def get_all_sample_properties(self):
    #     properties = [SAMPLE_IDENTIFIER_KEY]
    #     if len(self._samples_loaded) > 0:
    #         for sample in self._samples_loaded:
    #             keys = [prop for prop in sample.keys() if prop not in properties]
    #             properties.extend(keys)
    #     return properties

    ### --------------------------------------------------- ###


#     def toggle_lock_or_unlock_widgets(self):
#         if self.mode in ["add", "edit", "customize"]:
#             self.widgets.selector.setEnabled(False)
#             self.widgets.btn_add.setEnabled(False)
#             self.widgets.btn_edit.setEnabled(False)
#             self.widgets.btn_remove.setEnabled(False)
#             self.widgets.btn_custom.setEnabled(False)
#         else:
#             selected_sample = self.get_current_selected()
#             self.widgets.selector.setEnabled(True)
#             self.widgets.btn_add.setEnabled(True)
#             self.widgets.btn_custom.setEnabled(True)
#             if selected_sample:
#                 self.widgets.btn_edit.setEnabled(True)
#                 self.widgets.btn_remove.setEnabled(True)
#             else:
#                 self.widgets.btn_edit.setEnabled(False)
#                 self.widgets.btn_remove.setEnabled(False)
#
#     def show_cancel_save_buttons(self):
#         self.widgets.btn_cancel.show()
#         self.widgets.btn_save.show()
#
#     def hide_cancel_save_buttons(self):
#         self.widgets.btn_cancel.hide()
#         self.widgets.btn_save.hide()
#
#     def show_add_property_button(self):
#         self.widgets.btn_add_prop.show()
#
#     def hide_add_property_button(self):
#         self.widgets.btn_add_prop.hide()
#
#     def execute_add_sample(self):
#         current_samples = self._get_samples()
#         new_sample = self.create_new_sample()
#         updated_samples = {}
#         if len(current_samples) > 0:
#             for i, cur_sample in enumerate(current_samples):
#                 updated_samples[i] = cur_sample
#                 updated_samples[i + 1] = new_sample
#         else:
#             updated_samples[0] = new_sample
#         self.update_proposal(updated_samples)
#
#     def execute_edit_sample(self):
#         current_samples = self._get_samples()
#         edited_sample = self.create_edited_sample()
#         edited_id = edited_sample[SAMPLE_IDENTIFIER_KEY]
#         updated_samples = {}
#         for i, cur_sample in enumerate(current_samples):
#             if cur_sample[SAMPLE_IDENTIFIER_KEY] == edited_id:
#                 updated_samples[i] = edited_sample
#             else:
#                 updated_samples[i] = cur_sample
#         self.update_proposal(updated_samples)
#
#     def update_proposal(self, updated_samples):
#         self.client.run(f"Exp.sample.set_samples({updated_samples})")
#
#     def set_initial_view(self):
#         for i, sample_prop in enumerate(DEFAULT_PROPERTIES):
#             self.add_sample_info_row_to_layout()
#             sample_info_row = self.sample_info_widgets[i]
#             sample_info_row.key_lab.setText(str(sample_prop))
#
#     def create_saved_sample(self):
#         new_sample = {}
#         for sample_info_row in self.sample_info_widgets:
#             key = sample_info_row.key_lab.text()
#             val = sample_info_row.val_edt.text()
#             new_sample.update({key: val})
#         return new_sample
#
#     def create_edited_sample(self):
#         edited_sample = {}
#         for sample_info_row in self.sample_info_widgets:
#             key = sample_info_row.key_lab.text()
#             if key == SAMPLE_IDENTIFIER_KEY:
#                 val = sample_info_row.val_lab.text()
#             else:
#                 val = sample_info_row.val_edt.text()
#             edited_sample.update({key: val})
#         return edited_sample
#
#     def show_empty_view(self):
#         self.widgets.btn_remove.setEnabled(False)
#         self.widgets.btn_edit.hide()
#         self.widgets.btn_cancel.hide()
#         self.widgets.btn_save.hide()
#         # self.show_empty_sample_widgets()
#
#     def show_sample_view(self):
#         self.hide_add_property_button()
#         self.hide_cancel_save_buttons()
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.key_lab.show()
#             sample_info_row.key_edt.hide()
#             sample_info_row.val_lab.show()
#             sample_info_row.val_edt.hide()
#
#     def show_add_sample_view(self):
#         self.widgets.btn_save.setText("Save sample")
#         self.show_cancel_save_buttons()
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.key_lab.show()
#             sample_info_row.key_edt.hide()
#             sample_info_row.val_lab.hide()
#             sample_info_row.val_edt.show()
#
#     def show_edit_sample_view(self):
#         self.widgets.btn_save.setText("Save changes")
#         self.show_cancel_save_buttons()
#         for sample_info_row in self.sample_info_widgets:
#             if sample_info_row.key_lab.text() == SAMPLE_IDENTIFIER_KEY:
#                 sample_info_row.key_lab.show()
#                 sample_info_row.key_edt.hide()
#                 sample_info_row.val_lab.show()
#                 sample_info_row.val_edt.hide()
#             else:
#                 sample_info_row.key_lab.show()
#                 sample_info_row.key_edt.hide()
#                 sample_info_row.val_lab.hide()
#                 sample_info_row.val_edt.show()
#
#     def show_customize_view(self):
#         self.widgets.btn_save.setText("Save changes")
#         self.show_add_property_button()
#         self.show_cancel_save_buttons()
#         self.widgets.header_val.hide()
#         for sample_info_row in self.sample_info_widgets:
#             if sample_info_row.key_lab.text() in DEFAULT_PROPERTIES:
#                 sample_info_row.key_lab.show()
#                 sample_info_row.key_edt.hide()
#                 sample_info_row.val_lab.hide()
#                 sample_info_row.val_edt.hide()
#             else:
#                 sample_info_row.key_lab.hide()
#                 sample_info_row.key_edt.show()
#                 sample_info_row.val_lab.hide()
#                 sample_info_row.val_edt.hide()
#
#     def set_key_widget_text(self, sample_id=None):
#         if sample_id is not None:
#             sample = self._get_sample(sample_id)
#             keys = sample.keys()
#         else:
#             keys = DEFAULT_PROPERTIES
#         for i, key in enumerate(keys):
#             if i >= len(self.sample_info_widgets):
#                 self.add_sample_info_row_to_layout()
#             sample_info_row = self.sample_info_widgets[i]
#             sample_info_row.key_lab.setText(str(key))
#             sample_info_row.key_edt.setText(str(key))
#
#     def set_val_widget_text(self, sample_id):
#         sample = self._get_sample(sample_id)
#         for i, val in enumerate(sample.values()):
#             sample_info_row = self.sample_info_widgets[i]
#             sample_info_row.val_lab.setText(str(val))
#             sample_info_row.val_edt.setText(str(val))
#
#     def reset_key_widget_text(self):
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.key_lab.setText("")
#             sample_info_row.key_edt.setText("")
#
#     def reset_val_widget_text(self):
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.val_lab.setText("")
#             sample_info_row.val_edt.setText("")
#
#     def show_empty_sample_widgets(self):
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.key_lab.show()
#             sample_info_row.key_edt.hide()
#             sample_info_row.val_lab.hide()
#             sample_info_row.val_edt.hide()
#
#     def show_view_sample_widgets(self):
#         for sample_info_row in self.sample_info_widgets:
#             sample_info_row.key_lab.show()
#             sample_info_row.key_edt.hide()
#             sample_info_row.val_lab.show()
#             sample_info_row.val_edt.hide()
#
#     def show_remove_sample_dialog(self):
#         selected_sample = self.widgets.selector.currentItem().text()
#         label_text = f"Remove sample: '{selected_sample}'"
#         self.remove_sample_dialog.message.setText(label_text)
#         self.remove_sample_dialog.exec()
#
#     def add_sample_info_row_to_layout(self):
#         row_i = len(self.sample_info_widgets) + 1
#         row = SampleInfoRow()
#         self.sample_info_widgets.append(row)
#         self.widgets.sample_info_grid_layout.addWidget(row.key_lab, row_i, 0)
#         self.widgets.sample_info_grid_layout.addWidget(row.key_edt, row_i, 0)
#         self.widgets.sample_info_grid_layout.addWidget(row.val_lab, row_i, 1)
#         self.widgets.sample_info_grid_layout.addWidget(row.val_edt, row_i, 1)
#         self.widgets.sample_info_grid_layout.addWidget(row.message, row_i, 2)
#
#     def on_client_connected(self):
#         self.setViewOnly(self.client.viewonly)
#
#     # def on_client_disconnected(self):
#     #     if not self._in_edit_mode:
#     #         self._clear_data()
#
#     # def update_sample_selector_items(self):
#     #     sample_ids = self._get_sample_ids()
#     #     print(sample_ids)
#     #     if self.mode == "add":
#     #
#     #     selector_items = self.get_selector_items()
#     #     new_samples = set(sample_ids) - set(selector_items)
#     #     removed_samples = set(selector_items) - set(sample_ids)
#     #     if len(removed_samples) > 0:
#     #         for i, sample in enumerate(selector_items):
#     #             if sample in removed_samples:
#     #                 self.widgets.sample_selector.takeItem(i)
#     #     if len(new_samples) > 0:
#     #         for sample in sorted(new_samples):
#     #             item = QListWidgetItem(sample)
#     #             self.widgets.sample_selector.addItem(item)
#     #             self.widgets.sample_selector.setCurrentItem(item)
#     #             self.set_widget_text()
#
#     def get_selector_items(self):
#         items = []
#         rows = self.widgets.selector.count()
#         if rows > 0:
#             for i in range(rows):
#                 self.widgets.selector.setCurrentRow(i)
#                 items.append(self.widgets.selector.currentItem().text())
#         self.clear_sample_selection()
#         return items
#
#     def _write_samples(self, samples):
#         self.client.run(f"Exp.sample.set_samples({samples})")
#
#     def _remove_sample(self, sample_to_remove):
#         samples = self._get_samples()
#         updated_samples = {}
#         for i, sample in enumerate(samples):
#             if sample[SAMPLE_IDENTIFIER_KEY] != sample_to_remove:
#                 updated_samples[i] = sample
#         self._write_samples(updated_samples)
#
#     def _clear_data(self):
#         pass
#
#     def _get_sample_ids(self):
#         sample_ids = []
#         samples = self._get_samples()
#         for sample in samples:
#             sample_ids.append(sample[SAMPLE_IDENTIFIER_KEY])
#         return sample_ids
#
#     def _get_sample(self, sample_id):
#         samples = self._get_samples()
#         for sample in samples:
#             for key, val in sample.items():
#                 if key == SAMPLE_IDENTIFIER_KEY and val == sample_id:
#                     return sample
#
#     def _get_updated_sample(self, sample_identifier):
#         edited_annotations = self.save_edited_annotations()
#         new_annotations = self.save_new_annotations()
#         all_annotations = dict(**edited_annotations, **new_annotations)
#         all_annotations[SAMPLE_IDENTIFIER_KEY] = sample_identifier
#         return all_annotations
#
#     def cancel_add_clicked(self):
#         self.reset_new_sample_id()
#         self.reset_existing_annotation_values_to_edit()
#         self.reset_sample_id_error()
#         self.show_sample_view_mode()
#         self.show_empty_view()
#
#     def confirm_add_clicked(self):
#         new_sample = self.sample_annotations.id_row.val_edt.text()
#         self.selected_sample = new_sample
#         if self.check_unique_sample_id(new_sample):
#             self._add_sample_to_proposal(new_sample)
#             self.load_sample_selector_items()
#             self.set_id_value(new_sample)
#             self.reset_new_sample_id()
#             self.reset_existing_annotation_values()
#             self.update_sample_selection(self.selected_sample)
#             self.show_sample_view_mode()
#
#     def cancel_remove_clicked(self):
#         self.show_sample_view_mode()
#         self.remove_sample_dialog.close()
#
#     def confirm_remove_clicked(self):
#         selected_sample = self.sample_selector.currentItem().text()
#         self._remove_sample(selected_sample)
#         selected_row = self.sample_selector.currentRow()
#         self.sample_selector.takeItem(selected_row)
#         self.remove_sample_dialog.close()
#         samples_in_selector = self.get_selector_items()
#         if len(samples_in_selector) == 0:
#             self.selected_sample = None
#             self.show_empty_view()
#         else:
#             self.selected_sample = samples_in_selector[-1]
#             self.update_sample_selection(self.selected_sample)
#             self.show_sample_view_mode()
#
#     def add_annotation_clicked(self):
#         row_index = len(self.sample_annotations.new_annotation_rows) + 1
#         new_annotation_row = SampleInfoRow()
#         self.sample_annotations.new_annotation_rows.append(new_annotation_row)
#         new_annotation_row.add_and_align_left(
#             self.sample_annotations.new_annotations_layout, row_index
#         )
#         self.show_new_sample_annotations_edit()
#
#     def cancel_edit_clicked(self):
#         self.reset_existing_annotation_values_to_edit()
#         self.reset_new_annotation_values_to_edit()
#         self.discard_new_annotations()
#         self.show_sample_view_mode()
#
#     def confirm_edit_clicked(self):
#         selected_sample = self.sample_selector.currentItem().text()
#         if self.check_all_new_annotations_have_keys():
#             self._update_proposal(selected_sample)
#             time.sleep(0.1)
#             self.set_annotation_values(selected_sample)
#             self.reset_existing_annotation_values_to_edit()
#             self.reset_new_annotation_values_to_edit()
#             self.update_sample_selection(selected_sample)
#             self.show_sample_view_mode()
#
#     def get_index_to_select(self, sample_to_select):
#         items = self.get_selector_items()
#         return items.index(sample_to_select)
#
#     def update_sample_selection(self, sample_to_select=None):
#         if sample_to_select is not None:
#             select_index = self.get_index_to_select(sample_to_select)
#             self.sample_selector.setCurrentRow(select_index)
#         else:
#             self.sample_selector.clearSelection()
#
#     def copy_sample_info_to_widgets(self, sample):
#         self.enable_top_buttons()
#         # sample = self._get_sample()
#         # self.set_id_key()
#         # self.set_id_value(self.selected_sample)
#         # self.set_annotation_values(self.selected_sample)
#
#     def show_sample_view_mode(self):
#         self.show_sample_id()
#         self.show_sample_annotations()
#         self.hide_add_ctrl_buttons()
#         self.hide_edit_ctrl_buttons()
#         self.enable_top_buttons()
#         self.enable_sample_selector()
#
#     def show_edit_sample(self):
#         self.show_sample_id()
#         self.show_sample_annotations_edit()
#         self.show_new_sample_annotations_edit()
#         self.hide_add_ctrl_buttons()
#         self.show_edit_ctrl_buttons()
#         self.disable_top_buttons()
#         self.disable_sample_selector()
#
#     def show_add_sample(self):
#         self.show_empty_view()
#         self.set_id_key()
#         self.show_sample_id_edit()
#         self.show_add_ctrl_buttons()
#         self.disable_top_buttons()
#         self.disable_sample_selector()
#
#     def set_id_key(self):
#         self.sample_annotations.id_row.key_lab.setText(SAMPLE_IDENTIFIER_KEY)
#
#     def set_id_value(self, sample_identifier):
#         self.sample_annotations.id_row.val_lab.setText(str(sample_identifier))
#
#     def copy_existing_annotation_values_to_edit(self):
#         for annotation_row in self.sample_annotations.annotation_rows:
#             key = annotation_row.key_lab.text()
#             annotation_row.key_edt.setText(str(key))
#             value = annotation_row.val_lab.text()
#             annotation_row.val_edt.setText(str(value))
#
#     def reset_existing_annotation_values(self):
#         for annotation_row in self.sample_annotations.annotation_rows:
#             annotation_row.val_lab.setText("")
#
#     def reset_existing_annotation_values_to_edit(self):
#         for annotation_row in self.sample_annotations.annotation_rows:
#             annotation_row.val_edt.setText("")
#
#     def reset_new_annotation_values_to_edit(self):
#         for annotation_row in self.sample_annotations.new_annotation_rows:
#             annotation_row.key_edt.setText("")
#             annotation_row.val_edt.setText("")
#
#     def reset_new_sample_id(self):
#         self.sample_annotations.id_row.val_edt.setText("")
#
#     def save_edited_annotations(self):
#         annotations = {}
#         for annotation_row in self.sample_annotations.annotation_rows:
#             key = annotation_row.key_lab.text()
#             new_value = annotation_row.val_edt.text()
#             annotations[key] = new_value
#         return annotations
#
#     def save_new_annotations(self):
#         annotations = {}
#         if len(self.sample_annotations.new_annotation_rows) > 0:
#             for annotation_row in self.sample_annotations.new_annotation_rows:
#                 new_key = annotation_row.key_edt.text()
#                 new_value = annotation_row.val_edt.text()
#                 annotations[new_key] = new_value
#                 self.sample_annotations.add_annotation_row(new_key, new_value)
#                 annotation_row.remove(self.sample_annotations.new_annotations_layout)
#             self.sample_annotations.new_annotation_rows = []
#         return annotations
#
#     def check_all_new_annotations_have_keys(self):
#         checks_ok = True
#         for annotation_row in self.sample_annotations.new_annotation_rows:
#             new_key = annotation_row.key_edt.text()
#             if new_key == "":
#                 self.display_empty_key_error(annotation_row)
#                 checks_ok = False
#             else:
#                 self.reset_empty_key_error(annotation_row)
#         return checks_ok
#
#     def display_empty_key_error(self, annotation_row):
#         annotation_row.message.setText(
#             f"Please add a {SAMPLE_IDENTIFIER_KEY} for the annotation"
#         )
#
#     def reset_empty_key_error(self, annotation_row):
#         annotation_row.message.setText("")
#
#     def discard_new_annotations(self):
#         if len(self.sample_annotations.new_annotation_rows) > 0:
#             for annotation_row in self.sample_annotations.new_annotation_rows:
#                 annotation_row.remove(self.sample_annotations.new_annotations_layout)
#                 self.sample_annotations.new_annotation_rows = []
#
#     def check_unique_sample_id(self, sample_identifier):
#         if sample_identifier == "":
#             self.display_missing_id_error()
#         elif sample_identifier in self._get_sample_ids():
#             self.display_duplicate_id_error()
#         else:
#             self.reset_sample_id_error()
#             return True
#
#     def display_duplicate_id_error(self):
#         self.sample_annotations.id_row.message.setText("Sample already exist")
#
#     def display_missing_id_error(self):
#         self.sample_annotations.id_row.message.setText("Please enter a sample")
#
#     def reset_sample_id_error(self):
#         self.sample_annotations.id_row.message.setText("")
#
#     def show_sample_id(self):
#         self.sample_annotations.id_row.key_lab.show()
#         self.sample_annotations.id_row.val_lab.show()
#         self.sample_annotations.id_row.key_edt.hide()
#         self.sample_annotations.id_row.val_edt.hide()
#
#     def show_sample_id_edit(self):
#         self.sample_annotations.id_row.key_lab.show()
#         self.sample_annotations.id_row.val_lab.hide()
#         self.sample_annotations.id_row.key_edt.hide()
#         self.sample_annotations.id_row.val_edt.show()
#
#     def hide_sample_id(self):
#         self.sample_annotations.id_row.key_lab.hide()
#         self.sample_annotations.id_row.val_lab.hide()
#         self.sample_annotations.id_row.key_edt.hide()
#         self.sample_annotations.id_row.val_edt.hide()
#
#     def show_sample_annotations_edit(self):
#         self.copy_existing_annotation_values_to_edit()
#         for annotation_row in self.sample_annotations.annotation_rows:
#             annotation_row.key_lab.hide()
#             annotation_row.val_lab.hide()
#             annotation_row.key_edt.show()
#             annotation_row.val_edt.show()
#
#     def show_new_sample_annotations_edit(self):
#         for annotation_row in self.sample_annotations.new_annotation_rows:
#             annotation_row.key_lab.hide()
#             annotation_row.val_lab.hide()
#             annotation_row.key_edt.show()
#             annotation_row.val_edt.show()
#
#     def hide_sample_annotations(self):
#         for annotation_row in self.sample_annotations.annotation_rows:
#             annotation_row.key_lab.hide()
#             annotation_row.val_lab.hide()
#             annotation_row.key_edt.hide()
#             annotation_row.val_edt.hide()
#
#     def show_add_ctrl_buttons(self):
#         self.add_ctrl_buttons.btn_cancel.show()
#         self.add_ctrl_buttons.btn_add.show()
#
#     def hide_add_ctrl_buttons(self):
#         self.add_ctrl_buttons.btn_add.hide()
#         self.add_ctrl_buttons.btn_cancel.hide()
#
#     def show_edit_ctrl_buttons(self):
#         self.edt_ctrl_buttons.btn_save.show()
#         self.edt_ctrl_buttons.btn_cancel.show()
#         # self.edt_ctrl_buttons.btn_add_annotation.show()
#
#     def hide_edit_ctrl_buttons(self):
#         self.edt_ctrl_buttons.btn_save.hide()
#         self.edt_ctrl_buttons.btn_cancel.hide()
#         # self.edt_ctrl_buttons.btn_add_annotation.hide()
#
#     def enable_top_buttons(self):
#         self.top_buttons.btn_add.setEnabled(True)
#         self.top_buttons.btn_edit.setEnabled(True)
#         self.top_buttons.btn_remove.setEnabled(True)
#
#     def disable_top_buttons(self):
#         self.top_buttons.btn_add.setEnabled(False)
#         self.top_buttons.btn_edit.setEnabled(False)
#         self.top_buttons.btn_remove.setEnabled(False)
#
#     def disable_edit_and_remove(self):
#         self.top_buttons.btn_edit.setEnabled(False)
#         self.top_buttons.btn_remove.setEnabled(False)
#
#     def enable_sample_selector(self):
#         self.sample_selector.setEnabled(True)
#
#     def disable_sample_selector(self):
#         self.sample_selector.setEnabled(False)
#
#     def _update_proposal(self, sample_identifier):
#         if sample_identifier in self._get_sample_ids():
#             self._update_sample_in_proposal(sample_identifier)
#         else:
#             self._add_sample_to_proposal(sample_identifier)
#
#     def _add_sample_to_proposal(self, sample_identifier):
#         current_samples = self._get_samples()
#         new_sample = {SAMPLE_IDENTIFIER_KEY: sample_identifier}
#         samples = {}
#         if len(current_samples) > 0:
#             for index, sample in enumerate(current_samples):
#                 samples[index] = sample
#                 samples[index + 1] = new_sample
#         else:
#             samples[0] = new_sample
#         self._write_samples(samples)
#
#     def _update_sample_in_proposal(self, sample_identifier):
#         current_samples = self._get_samples()
#         updated_sample = self._get_updated_sample(sample_identifier)
#         samples = {}
#         for index, sample in enumerate(current_samples):
#             if sample[SAMPLE_IDENTIFIER_KEY] == sample_identifier:
#                 samples[index] = updated_sample
#             else:
#                 samples[index] = sample
#         self._write_samples(samples)
#
#
# class SampleInfoRow:
#     def __init__(self):
#         self.key_lab = QLabel()
#         self.key_edt = QLineEdit()
#         self.val_lab = QLabel()
#         self.val_edt = QLineEdit()
#         self.message = QLabel()

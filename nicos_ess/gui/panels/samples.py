import time

from nicos.guisupport.qt import (
    QLabel,
    QLineEdit,
    QListWidgetItem,
    Qt,
    QVBoxLayout,
)

from nicos_ess.gui.panels.panel import PanelBase
from nicos_ess.gui.widgets.sample_widgets import SamplePanelWidgets, RemoveSampleDialog

MANDATORY_PROPERTIES = ["name", "another_mandatory_key"]
SAMPLE_IDENTIFIER_KEY = MANDATORY_PROPERTIES[0]


class SamplePanel(PanelBase):
    panelName = "Sample info panel"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options
        # self._in_edit_mode = False
        self.to_monitor = ["sample/samples"]  # , "exp/propinfo"]
        self.mode = None
        self.sample_info_widgets = []
        self.previously_selected = None

        self.widgets = SamplePanelWidgets()
        self.remove_sample_dialog = RemoveSampleDialog()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.widgets.sample_panel_widget)
        self.setLayout(self.layout)

        self.initialise_connection_status_listeners()
        self.connect_signals()

        # self.set_initial_view()
        self.show_empty_view()

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        for monitor in self.to_monitor:
            self.client.register(self, monitor)

    def connect_signals(self):
        self.widgets.sample_selector.itemSelectionChanged.connect(
            self.selection_updated
        )
        self.widgets.btn_add.clicked.connect(self.add_sample_clicked)
        self.widgets.btn_edit.clicked.connect(self.edit_sample_clicked)
        self.widgets.btn_remove.clicked.connect(self.remove_sample_clicked)
        self.widgets.btn_cancel.clicked.connect(self.cancel_clicked)
        self.widgets.btn_save.clicked.connect(self.save_clicked)
        self.widgets.btn_add_prop.clicked.connect(self.add_property_clicked)
        self.remove_sample_dialog.buttonBox.accepted.connect(
            self.confirm_remove_clicked
        )
        self.remove_sample_dialog.buttonBox.rejected.connect(self.cancel_remove_clicked)

    def on_keyChange(self, key, value, time, expired):
        print("key change, key:", key)
        if key in self.to_monitor:
            self.load_sample_selector_items()

    def load_sample_selector_items(self):
        if self.mode is None:
            sample_ids = self._get_sample_ids()
            print(sample_ids)
            for sample_id in sample_ids:
                item = QListWidgetItem(sample_id)
                self.widgets.sample_selector.addItem(item)

    def selection_updated(self):
        """
        set sample selected
        set key labels
        set value labels
        -- and --
        show key labels
        show value labels
        """
        if self.mode == "add":
            pass
        else:
            selected_sample = self.get_current_selected()
            self.set_key_widget_text(selected_sample)
            self.set_val_widget_text(selected_sample)
            self.show_sample_view()

    def get_current_selected(self):
        selected_items = self.widgets.sample_selector.selectedItems()
        if len(selected_items) != 0:
            return selected_items[0].text()

    def toggle_lock_or_unlock_widgets(self):
        if self.mode in ["add", "edit", "customize"]:
            self.widgets.sample_selector.setEnabled(False)
            self.widgets.btn_add.setEnabled(False)
            self.widgets.btn_edit.setEnabled(False)
            self.widgets.btn_remove.setEnabled(False)
            self.widgets.btn_custom.setEnabled(False)
        else:
            selected_sample = self.get_current_selected()
            self.widgets.sample_selector.setEnabled(True)
            self.widgets.btn_add.setEnabled(True)
            self.widgets.btn_custom.setEnabled(True)
            if selected_sample:
                self.widgets.btn_edit.setEnabled(True)
                self.widgets.btn_remove.setEnabled(True)
            else:
                self.widgets.btn_edit.setEnabled(False)
                self.widgets.btn_remove.setEnabled(False)

    def show_cancel_save_buttons(self):
        self.widgets.btn_cancel.show()
        self.widgets.btn_save.show()

    def hide_cancel_save_buttons(self):
        self.widgets.btn_cancel.hide()
        self.widgets.btn_save.hide()

    def show_add_property_button(self):
        self.widgets.btn_add_prop.show()

    def hide_add_property_button(self):
        self.widgets.btn_add_prop.hide()

    def add_sample_clicked(self):
        """
        set mode to "add"
        set no sample selected
        set key labels (from existing samples or mandatory keys)
        set values to empty string
        -- and --
        show key labels
        show value fields
        show cancel save buttons
        lock panel widgets
        """
        self.mode = "add"
        self.previously_selected = self.get_current_selected()
        self.widgets.sample_selector.clearSelection()
        self.set_key_widget_text()
        self.reset_val_widget_text()
        self.toggle_lock_or_unlock_widgets()
        self.show_add_sample_view()

    def edit_sample_clicked(self):
        """
        set mode to "edit"
        set value fields
        -- and --
        show value label for sample id
        show value fields for rest
        show cancel save buttons
        lock panel widgets
        """
        self.mode = "edit"
        self.widgets.sample_selector.setEnabled(False)
        self.widgets.btn_add.setEnabled(False)
        self.widgets.btn_edit.setEnabled(False)
        self.widgets.btn_remove.setEnabled(False)
        self.widgets.btn_custom.setEnabled(False)
        self.show_edit_sample_view()

    def customize_clicked(self):
        """
        set mode to "customize"
        set no sample selected
        set key fields
        -- and --
        show key label for sample id
        show key fields
        show add property buttons
        show cancel save buttons
        lock panel widgets
        """
        self.mode = "customize"
        self.reset_val_widget_text()
        self.widgets.sample_selector.setEnabled(False)
        self.widgets.btn_add.setEnabled(False)
        self.widgets.btn_edit.setEnabled(False)
        self.widgets.btn_remove.setEnabled(False)
        self.widgets.btn_custom.setEnabled(False)
        self.show_customize_view()

    def remove_sample_clicked(self):
        self.show_remove_sample_dialog()

    def add_property_clicked(self):
        """
        add sample info row
        show key field
        """
        self.add_sample_info_row_to_layout()

    def cancel_clicked(self):
        """
        if self.mode == "add":
            no sample is selected
            set value fields to empty string
            hide keys and values
        if self.mode == "edit":
            set value fields to empty string
            show value labels
        if self.mode == "customize":
            no sample is selected
            set key fields to empty string
            hide keys and values
        unlock panel widgets
        """
        self.mode = "view"
        self.reset_val_widget_text()
        self.toggle_lock_or_unlock_widgets()
        if self.previously_selected is not None:
            item = self.widgets.sample_selector.findItems(
                self.previously_selected, Qt.MatchExactly
            )
            self.widgets.sample_selector.setCurrentItem(item[0])
            self.previously_selected = None
        else:
            self.reset_key_widget_text()
        self.hide_cancel_save_buttons()
        self.hide_add_property_button()
        self.show_sample_view()

    def save_clicked(self):
        """
        if self.mode == "add":
            set sample_selected
            create sample from value fields
            set value fields to empty string
            show keys labels
            show value labels
            update proposal
            -> triggers update_sample_selector_items()
            select sample_selected
            -> triggers selection_updated()
        if self.mode == "edit":
            create sample from value fields
            set value fields to empty string
            show key labels
            show value labels
            update proposal
            -> triggers update_sample_selector_items()
            select sample_selected
            -> triggers selection_updated()
        if self.mode == "customize":
            no sample is selected
            save update keys to all samples
            set key fields to empty string
            hide keys and values
            update proposal
        unlock panel widgets
        """
        self.widgets.sample_selector.setEnabled(True)
        self.widgets.btn_add.setEnabled(True)
        self.widgets.btn_edit.setEnabled(True)
        self.widgets.btn_remove.setEnabled(True)
        self.widgets.btn_custom.setEnabled(True)
        self.widgets.btn_add_prop.hide()
        self.widgets.btn_cancel.hide()
        self.widgets.btn_save.hide()
        if self.mode == "add":
            self.execute_add_sample()
        elif self.mode == "edit":
            self.execute_edit_sample()
        #     time.sleep(1)
        # self.update_sample_view()
        self.show_sample_view()

    def execute_add_sample(self):
        current_samples = self._get_samples()
        new_sample = self.create_new_sample()
        updated_samples = {}
        if len(current_samples) > 0:
            for i, cur_sample in enumerate(current_samples):
                updated_samples[i] = cur_sample
                updated_samples[i + 1] = new_sample
        else:
            updated_samples[0] = new_sample
        self.update_proposal(updated_samples)

    def execute_edit_sample(self):
        current_samples = self._get_samples()
        edited_sample = self.create_edited_sample()
        edited_id = edited_sample[SAMPLE_IDENTIFIER_KEY]
        updated_samples = {}
        for i, cur_sample in enumerate(current_samples):
            if cur_sample[SAMPLE_IDENTIFIER_KEY] == edited_id:
                updated_samples[i] = edited_sample
            else:
                updated_samples[i] = cur_sample
        self.update_proposal(updated_samples)

    def update_proposal(self, updated_samples):
        self.client.run(f"Exp.sample.set_samples({updated_samples})")

    def set_initial_view(self):
        for i, sample_prop in enumerate(MANDATORY_PROPERTIES):
            self.add_sample_info_row_to_layout()
            sample_info_row = self.sample_info_widgets[i]
            sample_info_row.key_lab.setText(str(sample_prop))

    def create_saved_sample(self):
        new_sample = {}
        for sample_info_row in self.sample_info_widgets:
            key = sample_info_row.key_lab.text()
            val = sample_info_row.val_edt.text()
            new_sample.update({key: val})
        return new_sample

    def create_edited_sample(self):
        edited_sample = {}
        for sample_info_row in self.sample_info_widgets:
            key = sample_info_row.key_lab.text()
            if key == SAMPLE_IDENTIFIER_KEY:
                val = sample_info_row.val_lab.text()
            else:
                val = sample_info_row.val_edt.text()
            edited_sample.update({key: val})
        return edited_sample

    def show_empty_view(self):
        self.widgets.btn_edit.setEnabled(False)
        self.widgets.btn_remove.setEnabled(False)
        self.widgets.btn_add_prop.hide()
        self.widgets.btn_cancel.hide()
        self.widgets.btn_save.hide()
        self.show_empty_sample_widgets()

    def show_sample_view(self):
        self.toggle_lock_or_unlock_widgets()
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.key_lab.show()
            sample_info_row.key_edt.hide()
            sample_info_row.val_lab.show()
            sample_info_row.val_edt.hide()

    def show_add_sample_view(self):
        self.widgets.btn_save.setText("Save sample")
        self.show_cancel_save_buttons()
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.key_lab.show()
            sample_info_row.key_edt.hide()
            sample_info_row.val_lab.hide()
            sample_info_row.val_edt.show()

    def show_edit_sample_view(self):
        self.widgets.btn_save.setText("Save changes")
        self.widgets.btn_add_prop.hide()
        self.widgets.btn_cancel.show()
        self.widgets.btn_save.show()
        self.show_edit_val_sample_widgets()

    def show_customize_view(self):
        self.widgets.btn_save.setText("Save changes")
        self.widgets.btn_add_prop.show()
        self.widgets.btn_cancel.show()
        self.widgets.btn_save.show()
        self.show_custom_key_sample_widgets()

    def set_key_widget_text(self, sample_id=None):
        if sample_id is not None:
            sample = self._get_sample(sample_id)
            keys = sample.keys()
        else:
            keys = MANDATORY_PROPERTIES
        for i, key in enumerate(keys):
            if i >= len(self.sample_info_widgets):
                self.add_sample_info_row_to_layout()
            sample_info_row = self.sample_info_widgets[i]
            sample_info_row.key_lab.setText(str(key))
            sample_info_row.key_edt.setText(str(key))

    def set_val_widget_text(self, sample_id):
        sample = self._get_sample(sample_id)
        for i, val in enumerate(sample.values()):
            sample_info_row = self.sample_info_widgets[i]
            sample_info_row.val_lab.setText(str(val))
            sample_info_row.val_edt.setText(str(val))

    def reset_key_widget_text(self):
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.key_lab.setText("")
            sample_info_row.key_edt.setText("")

    def reset_val_widget_text(self):
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.val_lab.setText("")
            sample_info_row.val_edt.setText("")

    def show_empty_sample_widgets(self):
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.key_lab.show()
            sample_info_row.key_edt.hide()
            sample_info_row.val_lab.hide()
            sample_info_row.val_edt.hide()

    def show_view_sample_widgets(self):
        for sample_info_row in self.sample_info_widgets:
            sample_info_row.key_lab.show()
            sample_info_row.key_edt.hide()
            sample_info_row.val_lab.show()
            sample_info_row.val_edt.hide()

    def show_custom_key_sample_widgets(self):
        for sample_info_row in self.sample_info_widgets:
            if sample_info_row.key_lab.text() in MANDATORY_PROPERTIES:
                sample_info_row.key_lab.show()
                sample_info_row.key_edt.hide()
                sample_info_row.val_lab.hide()
                sample_info_row.val_edt.hide()
            else:
                sample_info_row.key_lab.hide()
                sample_info_row.key_edt.show()
                sample_info_row.val_lab.hide()
                sample_info_row.val_edt.hide()

    def show_remove_sample_dialog(self):
        selected_sample = self.widgets.sample_selector.currentItem().text()
        label_text = f"Remove sample: '{selected_sample}'"
        self.remove_sample_dialog.message.setText(label_text)
        self.remove_sample_dialog.exec()

    def add_sample_info_row_to_layout(self):
        row_i = len(self.sample_info_widgets) + 1
        row = SampleInfoRow()
        self.sample_info_widgets.append(row)
        self.widgets.sample_info_grid_layout.addWidget(row.key_lab, row_i, 0)
        self.widgets.sample_info_grid_layout.addWidget(row.key_edt, row_i, 0)
        self.widgets.sample_info_grid_layout.addWidget(row.val_lab, row_i, 1)
        self.widgets.sample_info_grid_layout.addWidget(row.val_edt, row_i, 1)
        self.widgets.sample_info_grid_layout.addWidget(row.message, row_i, 2)

    def on_client_connected(self):
        self.setViewOnly(self.client.viewonly)

    # def on_client_disconnected(self):
    #     if not self._in_edit_mode:
    #         self._clear_data()

    # def update_sample_selector_items(self):
    #     sample_ids = self._get_sample_ids()
    #     print(sample_ids)
    #     if self.mode == "add":
    #
    #     selector_items = self.get_selector_items()
    #     new_samples = set(sample_ids) - set(selector_items)
    #     removed_samples = set(selector_items) - set(sample_ids)
    #     if len(removed_samples) > 0:
    #         for i, sample in enumerate(selector_items):
    #             if sample in removed_samples:
    #                 self.widgets.sample_selector.takeItem(i)
    #     if len(new_samples) > 0:
    #         for sample in sorted(new_samples):
    #             item = QListWidgetItem(sample)
    #             self.widgets.sample_selector.addItem(item)
    #             self.widgets.sample_selector.setCurrentItem(item)
    #             self.set_widget_text()

    def get_selector_items(self):
        items = []
        rows = self.widgets.sample_selector.count()
        if rows > 0:
            for i in range(rows):
                self.widgets.sample_selector.setCurrentRow(i)
                items.append(self.widgets.sample_selector.currentItem().text())
        self.widgets.sample_selector.clearSelection()
        return items

    def _get_samples(self):
        return self.client.eval("session.experiment.get_samples()", {})

    def _write_samples(self, samples):
        self.client.run(f"Exp.sample.set_samples({samples})")

    def _remove_sample(self, sample_to_remove):
        samples = self._get_samples()
        updated_samples = {}
        for i, sample in enumerate(samples):
            if sample[SAMPLE_IDENTIFIER_KEY] != sample_to_remove:
                updated_samples[i] = sample
        self._write_samples(updated_samples)

    def _clear_data(self):
        pass

    def _get_sample_ids(self):
        sample_ids = []
        samples = self._get_samples()
        for sample in samples:
            sample_ids.append(sample[SAMPLE_IDENTIFIER_KEY])
        return sample_ids

    def _get_sample(self, sample_id):
        samples = self._get_samples()
        for sample in samples:
            for key, val in sample.items():
                if key == SAMPLE_IDENTIFIER_KEY and val == sample_id:
                    return sample

    def _get_updated_sample(self, sample_identifier):
        edited_annotations = self.save_edited_annotations()
        new_annotations = self.save_new_annotations()
        all_annotations = dict(**edited_annotations, **new_annotations)
        all_annotations[SAMPLE_IDENTIFIER_KEY] = sample_identifier
        return all_annotations

    def cancel_add_clicked(self):
        self.reset_new_sample_id()
        self.reset_existing_annotation_values_to_edit()
        self.reset_sample_id_error()
        self.show_sample_view_mode()
        self.show_empty_view()

    def confirm_add_clicked(self):
        new_sample = self.sample_annotations.id_row.val_edt.text()
        self.selected_sample = new_sample
        if self.check_unique_sample_id(new_sample):
            self._add_sample_to_proposal(new_sample)
            self.load_sample_selector_items()
            self.set_id_value(new_sample)
            self.reset_new_sample_id()
            self.reset_existing_annotation_values()
            self.update_sample_selection(self.selected_sample)
            self.show_sample_view_mode()

    def cancel_remove_clicked(self):
        self.show_sample_view_mode()
        self.remove_sample_dialog.close()

    def confirm_remove_clicked(self):
        selected_sample = self.sample_selector.currentItem().text()
        self._remove_sample(selected_sample)
        selected_row = self.sample_selector.currentRow()
        self.sample_selector.takeItem(selected_row)
        self.remove_sample_dialog.close()
        samples_in_selector = self.get_selector_items()
        if len(samples_in_selector) == 0:
            self.selected_sample = None
            self.show_empty_view()
        else:
            self.selected_sample = samples_in_selector[-1]
            self.update_sample_selection(self.selected_sample)
            self.show_sample_view_mode()

    def add_annotation_clicked(self):
        row_index = len(self.sample_annotations.new_annotation_rows) + 1
        new_annotation_row = SampleInfoRow()
        self.sample_annotations.new_annotation_rows.append(new_annotation_row)
        new_annotation_row.add_and_align_left(
            self.sample_annotations.new_annotations_layout, row_index
        )
        self.show_new_sample_annotations_edit()

    def cancel_edit_clicked(self):
        self.reset_existing_annotation_values_to_edit()
        self.reset_new_annotation_values_to_edit()
        self.discard_new_annotations()
        self.show_sample_view_mode()

    def confirm_edit_clicked(self):
        selected_sample = self.sample_selector.currentItem().text()
        if self.check_all_new_annotations_have_keys():
            self._update_proposal(selected_sample)
            time.sleep(0.1)
            self.set_annotation_values(selected_sample)
            self.reset_existing_annotation_values_to_edit()
            self.reset_new_annotation_values_to_edit()
            self.update_sample_selection(selected_sample)
            self.show_sample_view_mode()

    def get_index_to_select(self, sample_to_select):
        items = self.get_selector_items()
        return items.index(sample_to_select)

    def update_sample_selection(self, sample_to_select=None):
        if sample_to_select is not None:
            select_index = self.get_index_to_select(sample_to_select)
            self.sample_selector.setCurrentRow(select_index)
        else:
            self.sample_selector.clearSelection()

    def copy_sample_info_to_widgets(self, sample):
        self.enable_top_buttons()
        # sample = self._get_sample()
        # self.set_id_key()
        # self.set_id_value(self.selected_sample)
        # self.set_annotation_values(self.selected_sample)

    def show_sample_view_mode(self):
        self.show_sample_id()
        self.show_sample_annotations()
        self.hide_add_ctrl_buttons()
        self.hide_edit_ctrl_buttons()
        self.enable_top_buttons()
        self.enable_sample_selector()

    def show_edit_sample(self):
        self.show_sample_id()
        self.show_sample_annotations_edit()
        self.show_new_sample_annotations_edit()
        self.hide_add_ctrl_buttons()
        self.show_edit_ctrl_buttons()
        self.disable_top_buttons()
        self.disable_sample_selector()

    def show_add_sample(self):
        self.show_empty_view()
        self.set_id_key()
        self.show_sample_id_edit()
        self.show_add_ctrl_buttons()
        self.disable_top_buttons()
        self.disable_sample_selector()

    def set_id_key(self):
        self.sample_annotations.id_row.key_lab.setText(SAMPLE_IDENTIFIER_KEY)

    def set_id_value(self, sample_identifier):
        self.sample_annotations.id_row.val_lab.setText(str(sample_identifier))

    def copy_existing_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            key = annotation_row.key_lab.text()
            annotation_row.key_edt.setText(str(key))
            value = annotation_row.val_lab.text()
            annotation_row.val_edt.setText(str(value))

    def reset_existing_annotation_values(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.val_lab.setText("")

    def reset_existing_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.val_edt.setText("")

    def reset_new_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.new_annotation_rows:
            annotation_row.key_edt.setText("")
            annotation_row.val_edt.setText("")

    def reset_new_sample_id(self):
        self.sample_annotations.id_row.val_edt.setText("")

    def save_edited_annotations(self):
        annotations = {}
        for annotation_row in self.sample_annotations.annotation_rows:
            key = annotation_row.key_lab.text()
            new_value = annotation_row.val_edt.text()
            annotations[key] = new_value
        return annotations

    def save_new_annotations(self):
        annotations = {}
        if len(self.sample_annotations.new_annotation_rows) > 0:
            for annotation_row in self.sample_annotations.new_annotation_rows:
                new_key = annotation_row.key_edt.text()
                new_value = annotation_row.val_edt.text()
                annotations[new_key] = new_value
                self.sample_annotations.add_annotation_row(new_key, new_value)
                annotation_row.remove(self.sample_annotations.new_annotations_layout)
            self.sample_annotations.new_annotation_rows = []
        return annotations

    def check_all_new_annotations_have_keys(self):
        checks_ok = True
        for annotation_row in self.sample_annotations.new_annotation_rows:
            new_key = annotation_row.key_edt.text()
            if new_key == "":
                self.display_empty_key_error(annotation_row)
                checks_ok = False
            else:
                self.reset_empty_key_error(annotation_row)
        return checks_ok

    def display_empty_key_error(self, annotation_row):
        annotation_row.message.setText(
            f"Please add a {SAMPLE_IDENTIFIER_KEY} for the annotation"
        )

    def reset_empty_key_error(self, annotation_row):
        annotation_row.message.setText("")

    def discard_new_annotations(self):
        if len(self.sample_annotations.new_annotation_rows) > 0:
            for annotation_row in self.sample_annotations.new_annotation_rows:
                annotation_row.remove(self.sample_annotations.new_annotations_layout)
                self.sample_annotations.new_annotation_rows = []

    def check_unique_sample_id(self, sample_identifier):
        if sample_identifier == "":
            self.display_missing_id_error()
        elif sample_identifier in self._get_sample_ids():
            self.display_duplicate_id_error()
        else:
            self.reset_sample_id_error()
            return True

    def display_duplicate_id_error(self):
        self.sample_annotations.id_row.message.setText("Sample already exist")

    def display_missing_id_error(self):
        self.sample_annotations.id_row.message.setText("Please enter a sample")

    def reset_sample_id_error(self):
        self.sample_annotations.id_row.message.setText("")

    def show_sample_id(self):
        self.sample_annotations.id_row.key_lab.show()
        self.sample_annotations.id_row.val_lab.show()
        self.sample_annotations.id_row.key_edt.hide()
        self.sample_annotations.id_row.val_edt.hide()

    def show_sample_id_edit(self):
        self.sample_annotations.id_row.key_lab.show()
        self.sample_annotations.id_row.val_lab.hide()
        self.sample_annotations.id_row.key_edt.hide()
        self.sample_annotations.id_row.val_edt.show()

    def hide_sample_id(self):
        self.sample_annotations.id_row.key_lab.hide()
        self.sample_annotations.id_row.val_lab.hide()
        self.sample_annotations.id_row.key_edt.hide()
        self.sample_annotations.id_row.val_edt.hide()

    def show_sample_annotations_edit(self):
        self.copy_existing_annotation_values_to_edit()
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_lab.hide()
            annotation_row.val_lab.hide()
            annotation_row.key_edt.show()
            annotation_row.val_edt.show()

    def show_new_sample_annotations_edit(self):
        for annotation_row in self.sample_annotations.new_annotation_rows:
            annotation_row.key_lab.hide()
            annotation_row.val_lab.hide()
            annotation_row.key_edt.show()
            annotation_row.val_edt.show()

    def hide_sample_annotations(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_lab.hide()
            annotation_row.val_lab.hide()
            annotation_row.key_edt.hide()
            annotation_row.val_edt.hide()

    def show_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_cancel.show()
        self.add_ctrl_buttons.btn_add.show()

    def hide_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_add.hide()
        self.add_ctrl_buttons.btn_cancel.hide()

    def show_edit_ctrl_buttons(self):
        self.edt_ctrl_buttons.btn_save.show()
        self.edt_ctrl_buttons.btn_cancel.show()
        # self.edt_ctrl_buttons.btn_add_annotation.show()

    def hide_edit_ctrl_buttons(self):
        self.edt_ctrl_buttons.btn_save.hide()
        self.edt_ctrl_buttons.btn_cancel.hide()
        # self.edt_ctrl_buttons.btn_add_annotation.hide()

    def enable_top_buttons(self):
        self.top_buttons.btn_add.setEnabled(True)
        self.top_buttons.btn_edit.setEnabled(True)
        self.top_buttons.btn_remove.setEnabled(True)

    def disable_top_buttons(self):
        self.top_buttons.btn_add.setEnabled(False)
        self.top_buttons.btn_edit.setEnabled(False)
        self.top_buttons.btn_remove.setEnabled(False)

    def disable_edit_and_remove(self):
        self.top_buttons.btn_edit.setEnabled(False)
        self.top_buttons.btn_remove.setEnabled(False)

    def enable_sample_selector(self):
        self.sample_selector.setEnabled(True)

    def disable_sample_selector(self):
        self.sample_selector.setEnabled(False)

    def _update_proposal(self, sample_identifier):
        if sample_identifier in self._get_sample_ids():
            self._update_sample_in_proposal(sample_identifier)
        else:
            self._add_sample_to_proposal(sample_identifier)

    def _add_sample_to_proposal(self, sample_identifier):
        current_samples = self._get_samples()
        new_sample = {SAMPLE_IDENTIFIER_KEY: sample_identifier}
        samples = {}
        if len(current_samples) > 0:
            for index, sample in enumerate(current_samples):
                samples[index] = sample
                samples[index + 1] = new_sample
        else:
            samples[0] = new_sample
        self._write_samples(samples)

    def _update_sample_in_proposal(self, sample_identifier):
        current_samples = self._get_samples()
        updated_sample = self._get_updated_sample(sample_identifier)
        samples = {}
        for index, sample in enumerate(current_samples):
            if sample[SAMPLE_IDENTIFIER_KEY] == sample_identifier:
                samples[index] = updated_sample
            else:
                samples[index] = sample
        self._write_samples(samples)


class SampleInfoRow:
    def __init__(self):
        self.key_lab = QLabel()
        self.key_edt = QLineEdit()
        self.val_lab = QLabel()
        self.val_edt = QLineEdit()
        self.message = QLabel()

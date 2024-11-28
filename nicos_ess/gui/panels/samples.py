from PyQt5.QtWidgets import QListWidgetItem

from nicos.guisupport.qt import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    # QAction,
    # QCursor,
    # QHeaderView,
    # QItemDelegate,
    # QKeySequence,
    # QMenu,
    # QShortcut,
    # Qt,
    # QTableView,
    # QTableWidgetItem,
    # pyqtSlot,
)

from nicos_ess.gui.panels.panel import PanelBase

SAMPLE_IDENTIFIER_KEY = "name"


class SamplePanel(PanelBase):
    panelName = "Sample info panel"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options
        self._in_edit_mode = False
        self.to_monitor = ["sample/samples", "exp/propinfo"]

        self.top_buttons = self.construct_top_menu()
        self.add_ctrl_buttons = self.construct_add_ctrl_buttons()
        self.edit_ctrl_buttons = self.construct_edit_ctrl_buttons()
        self.sample_selector = self.construct_sample_selector()
        self.sample_annotations = self.construct_sample_annotations()
        self.sample_annotation_outer_layout_widget = (
            self.construct_sample_annotation_outer_layout_widget()
        )
        self.panel_splitter = self.construct_splitter()
        self.remove_sample_dialog = self.construct_remove_sample_dialog()

        layout = QVBoxLayout()
        layout.addLayout(self.top_buttons.layout)
        layout.addWidget(self.panel_splitter)
        self.setLayout(layout)

        self.initialise_connection_status_listeners()

    def construct_top_menu(self):
        top_buttons = TopButtonLayout()
        top_buttons.btn_add.clicked.connect(self.add_sample_clicked)
        # top_buttons.btn_edit.clicked.connect(self.edit_sample_clicked)
        top_buttons.btn_remove.clicked.connect(self.remove_sample_clicked)
        top_buttons.btn_edit.setEnabled(False)
        top_buttons.btn_remove.setEnabled(False)
        return top_buttons

    def construct_add_ctrl_buttons(self):
        add_ctrl_buttons = AddControlButtonsLayout()
        add_ctrl_buttons.widget = QWidget()
        add_ctrl_buttons.widget.setLayout(add_ctrl_buttons.layout)
        add_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_add_clicked)
        add_ctrl_buttons.btn_add.clicked.connect(self.confirm_add_clicked)
        add_ctrl_buttons.btn_cancel.hide()
        add_ctrl_buttons.btn_add.hide()
        return add_ctrl_buttons

    def construct_edit_ctrl_buttons(self):
        edit_ctrl_buttons = EditControlButtonsLayout()
        edit_ctrl_buttons.widget = QWidget()
        edit_ctrl_buttons.widget.setLayout(edit_ctrl_buttons.layout)
        # edit_ctrl_buttons.btn_add_annotation.clicked.connect(
        #     self.add_annotation_clicked
        # )
        # edit_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_edit_clicked)
        # edit_ctrl_buttons.btn_save.clicked.connect(self.confirm_edit_clicked)
        edit_ctrl_buttons.btn_add_annotation.hide()
        edit_ctrl_buttons.btn_cancel.hide()
        edit_ctrl_buttons.btn_save.hide()
        return edit_ctrl_buttons

    def construct_sample_selector(self):
        sample_selector_widget = QListWidget()
        sample_selector_widget.itemClicked.connect(self.selection_updated)
        return sample_selector_widget

    def construct_sample_annotations(self):
        sample_annotations = SampleAnnotationWidgetLayout()
        sample_annotations.id_row.edit_key_widget.hide()
        sample_annotations.id_row.edit_value_widget.hide()
        return sample_annotations

    def construct_sample_annotation_outer_layout_widget(self):
        sample_annotation_outer_layout = QVBoxLayout()
        sample_annotation_outer_layout.addLayout(self.sample_annotations.layout)
        sample_annotation_outer_layout.addWidget(self.add_ctrl_buttons.widget)
        sample_annotation_outer_layout.addWidget(self.edit_ctrl_buttons.widget)
        sample_annotation_outer_layout.addStretch()
        sample_annotation_outer_layout_widget = QWidget()
        sample_annotation_outer_layout_widget.setLayout(sample_annotation_outer_layout)
        return sample_annotation_outer_layout_widget

    def construct_splitter(self):
        panel_splitter = QSplitter()
        panel_splitter.addWidget(self.sample_selector)
        panel_splitter.addWidget(self.sample_annotation_outer_layout_widget)
        return panel_splitter

    def construct_remove_sample_dialog(self):
        dialog = RemoveSampleDialog()
        dialog.buttonBox.accepted.connect(self.confirm_remove_clicked)
        dialog.buttonBox.rejected.connect(self.cancel_remove_clicked)
        return dialog

    def on_client_connected(self):
        self.setViewOnly(self.client.viewonly)

    # def on_client_disconnected(self):
    #     if not self._in_edit_mode:
    #         self._clear_data()

    def initialise_connection_status_listeners(self):
        PanelBase.initialise_connection_status_listeners(self)
        self.client.register(self, "exp/propinfo")
        # for monitor in self.to_monitor:
        #     self.client.register(self, monitor)

    def on_keyChange(self, key, value, time, expired):
        print("key change, key:", key)
        # if key in self.to_monitor:
        if key == "exp/propinfo":
            self.update_sample_selector_items()

    ###########################################################

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

    def _get_sample_identifiers(self):
        sample_identifiers = []
        samples = self._get_samples()
        for sample in samples:
            for key, value in sample.items():
                if key == SAMPLE_IDENTIFIER_KEY:
                    sample_identifiers.append(value)
        return sample_identifiers

    ###########################################################

    def selection_updated(self):
        self.enable_top_buttons()

    def add_sample_clicked(self):
        self.show_add_sample()

    def cancel_add_clicked(self):
        self.reset_new_sample_id()
        self.reset_existing_annotation_values_to_edit()
        self.show_sample_view_mode()
        self.show_empty_view()

    def confirm_add_clicked(self):
        new_sample = self.sample_annotations.id_row.edit_value_widget.text()
        if self.check_unique_sample_id(new_sample):
            self._update_sample_in_proposal(new_sample)
            self.update_sample_selector_items(new_sample)
            # self.sample_selector.setCurrentItem(new_widget_item)
            self.set_id_value(new_sample)
            # self.check_for_existing_annotation_keys()
            self.reset_new_sample_id()
            self.reset_existing_annotation_values()
            self.show_sample_view_mode()

    def remove_sample_clicked(self):
        self.show_remove_sample_dialog()

    def cancel_remove_clicked(self):
        self.show_sample_view_mode()
        self.remove_sample_dialog.close()

    def confirm_remove_clicked(self):
        selected_sample = self.sample_selector.currentItem().text()
        self._remove_sample(selected_sample)
        selected_row = self.sample_selector.currentRow()
        self.sample_selector.takeItem(selected_row)
        self.remove_sample_dialog.close()
        self.show_empty_view()

    def update_sample_selector_items(self, new_sample=None):
        if new_sample:
            item = QListWidgetItem(new_sample)
            self.sample_selector.addItem(item)
            self.sample_selector.setCurrentItem(item)
        else:
            pass
        #     sample_identifiers = self._get_sample_identifiers()
        #     selector_items = self.items_in_selector()
        #     if len(sample_identifiers) > len(selector_items):
        #         for index in range(len(selector_items), len(sample_identifiers)):
        #             self.sample_selector.insertItem(index, sample_identifiers[index])

    def items_in_selector(self):
        items = []
        rows = self.sample_selector.count()
        print(rows)
        if rows > 0:
            for i in range(rows):
                self.sample_selector.setCurrentRow(i)
                items.append(self.sample_selector.currentItem().text())
        self.sample_selector.clearSelection()
        return items

    #
    # def edit_sample_clicked(self):
    #     self.show_sample_edit_mode()
    #

    #

    #
    # def add_annotation_clicked(self):
    #     row_index = len(self.sample_annotations.new_annotation_rows) + 1
    #     new_annotation_row = AnnotationRow()
    #     self.sample_annotations.new_annotation_rows.append(new_annotation_row)
    #     new_annotation_row.add_and_align_left(
    #         self.sample_annotations.new_annotations_layout, row_index
    #     )
    #     self.show_new_sample_annotations_edit()
    #
    # def confirm_edit_clicked(self):
    #     selected_sample = self.sample_selector.currentItem().text()
    #     if self.check_all_new_annotations_have_keys():
    #         self._update_sample_in_proposal(selected_sample)
    #         self.set_annotation_values(selected_sample)
    #         self.reset_existing_annotation_values_to_edit()
    #         self.reset_new_annotation_values_to_edit()
    #         self.show_sample_view_mode()
    #
    # def cancel_edit_clicked(self):
    #     self.reset_existing_annotation_values_to_edit()
    #     self.reset_new_annotation_values_to_edit()
    #     self.discard_new_annotations()
    #     self.show_sample_view_mode()
    #

    #
    #
    #
    #
    #
    #

    #

    #
    def show_empty_view(self):
        self.hide_sample_id()
        self.hide_sample_annotations()
        self.hide_add_ctrl_buttons()
        self.hide_edit_ctrl_buttons()
        self.sample_selector.clearSelection()
        self.disable_edit_and_remove()

    def show_sample_view_mode(self):
        self.show_sample_id()
        self.show_sample_annotations()
        self.hide_add_ctrl_buttons()
        self.hide_edit_ctrl_buttons()
        self.enable_top_buttons()
        self.enable_sample_selector()

    #
    # def show_sample_edit_mode(self):
    #     self.show_sample_id()
    #     self.show_sample_annotations_edit()
    #     self.show_new_sample_annotations_edit()
    #     self.hide_add_ctrl_buttons()
    #     self.show_edit_ctrl_buttons()
    #     self.disable_top_buttons()
    #     self.disable_sample_selector()
    #

    def show_add_sample(self):
        self.show_empty_view()
        self.set_id_key()
        self.show_sample_id_edit()
        self.show_add_ctrl_buttons()
        self.disable_top_buttons()
        self.disable_sample_selector()

    def show_remove_sample_dialog(self):
        selected_sample = self.sample_selector.currentItem().text()
        label_text = f"Remove sample: '{selected_sample}'"
        self.remove_sample_dialog.message.setText(label_text)
        self.remove_sample_dialog.exec()

    #
    # def display_sample(self, sample_identifier):
    #     self.set_id_key()
    #     self.set_id_value(sample_identifier)
    #     self.set_annotation_values(sample_identifier)
    #     self.show_sample_view_mode()
    #
    def set_id_key(self):
        self.sample_annotations.id_row.key_widget.setText(SAMPLE_IDENTIFIER_KEY)

    #
    def set_id_value(self, sample_identifier):
        self.sample_annotations.id_row.value_widget.setText(str(sample_identifier))

    #
    # def set_annotation_keys(self, sample_identifier):
    #     sample = self._get_sample(sample_identifier)
    #     for i, key in enumerate(sample.keys()):
    #         if i < len(self.sample_annotations.annotation_rows):
    #             annotation_row = self.sample_annotations.annotation_rows[i]
    #             annotation_row.key_widget.setText(str(key))
    #         else:
    #             self.sample_annotations.add_annotation_row(key, "")
    #
    # def set_annotation_values(self, sample_identifier):
    #     sample = self._get_sample(sample_identifier)
    #     printed_keys = []
    #     if len(self.sample_annotations.annotation_rows) > 0:
    #         for annotation_row in self.sample_annotations.annotation_rows:
    #             key = annotation_row.key_widget.text()
    #             if key in sample.keys():
    #                 value = sample[key]
    #                 annotation_row.value_widget.setText(str(value))
    #             else:
    #                 annotation_row.value_widget.setText("")
    #             printed_keys.append(key)
    #     for key, value in sample.items():
    #         if key not in printed_keys:
    #             self.sample_annotations.add_annotation_row(key, value)
    #
    # def copy_existing_annotation_values_to_edit(self):
    #     for annotation_row in self.sample_annotations.annotation_rows:
    #         value = annotation_row.value_widget.text()
    #         annotation_row.edit_value_widget.setText(str(value))

    def reset_existing_annotation_values(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.value_widget.setText("")

    def reset_existing_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.edit_value_widget.setText("")

    #
    # def reset_new_annotation_values_to_edit(self):
    #     for annotation_row in self.sample_annotations.new_annotation_rows:
    #         annotation_row.edit_key_widget.setText("")
    #         annotation_row.edit_value_widget.setText("")
    #
    def reset_new_sample_id(self):
        self.sample_annotations.id_row.edit_value_widget.setText("")

    #
    # def save_edited_annotations(self):
    #     annotations = {}
    #     for annotation_row in self.sample_annotations.annotation_rows:
    #         key = annotation_row.key_widget.text()
    #         new_value = annotation_row.edit_value_widget.text()
    #         annotations[key] = new_value
    #     return annotations
    #
    # def save_new_annotations(self):
    #     annotations = {}
    #     if len(self.sample_annotations.new_annotation_rows) > 0:
    #         for annotation_row in self.sample_annotations.new_annotation_rows:
    #             new_key = annotation_row.edit_key_widget.text()
    #             new_value = annotation_row.edit_value_widget.text()
    #             annotations[new_key] = new_value
    #             self.sample_annotations.add_annotation_row(new_key, new_value)
    #             annotation_row.remove(self.sample_annotations.new_annotations_layout)
    #         self.sample_annotations.new_annotation_rows = []
    #     return annotations
    #
    # def check_all_new_annotations_have_keys(self):
    #     checks_ok = True
    #     for annotation_row in self.sample_annotations.new_annotation_rows:
    #         new_key = annotation_row.edit_key_widget.text()
    #         if new_key == "":
    #             self.display_empty_key_error(annotation_row)
    #             checks_ok = False
    #         else:
    #             self.reset_empty_key_error(annotation_row)
    #     return checks_ok
    #
    # def display_empty_key_error(self, annotation_row):
    #     annotation_row.info_message.setText(
    #         f"Please add a {SAMPLE_IDENTIFIER_KEY} for the annotation"
    #     )
    #
    # def reset_empty_key_error(self, annotation_row):
    #     annotation_row.info_message.setText("")
    #
    # def discard_new_annotations(self):
    #     if len(self.sample_annotations.new_annotation_rows) > 0:
    #         for annotation_row in self.sample_annotations.new_annotation_rows:
    #             annotation_row.remove(self.sample_annotations.new_annotations_layout)
    #             self.sample_annotations.new_annotation_rows = []

    def check_unique_sample_id(self, sample_identifier):
        if sample_identifier == "":
            self.display_missing_id_error()
        elif sample_identifier in self._get_sample_identifiers():
            self.display_duplicate_id_error()
        else:
            self.reset_sample_id_error()
            return True

    def display_duplicate_id_error(self):
        self.sample_annotations.id_row.info_message.setText("Sample already exist")

    def display_missing_id_error(self):
        self.sample_annotations.id_row.info_message.setText("Please enter a sample")

    def reset_sample_id_error(self):
        self.sample_annotations.id_row.info_message.setText("")
        self.sample_annotations.id_row.info_message.setText("")

    def check_for_existing_annotation_keys(self):
        if self.sample_selector.count() > 1:
            existing_sample_id = self.sample_selector.item(0).text()
            self.set_annotation_keys(existing_sample_id)

    #
    def show_sample_id(self):
        self.sample_annotations.id_row.key_widget.show()
        self.sample_annotations.id_row.value_widget.show()
        self.sample_annotations.id_row.edit_key_widget.hide()
        self.sample_annotations.id_row.edit_value_widget.hide()

    def show_sample_id_edit(self):
        self.sample_annotations.id_row.key_widget.show()
        self.sample_annotations.id_row.value_widget.hide()
        self.sample_annotations.id_row.edit_key_widget.hide()
        self.sample_annotations.id_row.edit_value_widget.show()

    def hide_sample_id(self):
        self.sample_annotations.id_row.key_widget.hide()
        self.sample_annotations.id_row.value_widget.hide()
        self.sample_annotations.id_row.edit_key_widget.hide()
        self.sample_annotations.id_row.edit_value_widget.hide()

    def show_sample_annotations(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_widget.show()
            annotation_row.value_widget.show()
            annotation_row.edit_key_widget.hide()
            annotation_row.edit_value_widget.hide()

    #
    # def show_sample_annotations_edit(self):
    #     self.copy_existing_annotation_values_to_edit()
    #     for annotation_row in self.sample_annotations.annotation_rows:
    #         annotation_row.key_widget.show()
    #         annotation_row.value_widget.hide()
    #         annotation_row.edit_key_widget.hide()
    #         annotation_row.edit_value_widget.show()
    #
    # def show_new_sample_annotations_edit(self):
    #     for annotation_row in self.sample_annotations.new_annotation_rows:
    #         annotation_row.key_widget.hide()
    #         annotation_row.value_widget.hide()
    #         annotation_row.edit_key_widget.show()
    #         annotation_row.edit_value_widget.show()
    #
    def hide_sample_annotations(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_widget.hide()
            annotation_row.value_widget.hide()
            annotation_row.edit_key_widget.hide()
            annotation_row.edit_value_widget.hide()

    #
    def show_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_cancel.show()
        self.add_ctrl_buttons.btn_add.show()

    #
    def hide_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_add.hide()
        self.add_ctrl_buttons.btn_cancel.hide()

    #
    # def show_edit_ctrl_buttons(self):
    #     self.edit_ctrl_buttons.btn_save.show()
    #     self.edit_ctrl_buttons.btn_cancel.show()
    #     self.edit_ctrl_buttons.btn_add_annotation.show()
    #
    def hide_edit_ctrl_buttons(self):
        self.edit_ctrl_buttons.btn_save.hide()
        self.edit_ctrl_buttons.btn_cancel.hide()
        self.edit_ctrl_buttons.btn_add_annotation.hide()

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

    #
    # def _get_sample(self, sample_identifier):
    #     samples = self._get_samples()
    #     for sample in samples:
    #         for key, val in sample.items():
    #             if key == SAMPLE_IDENTIFIER_KEY and val == sample_identifier:
    #                 return sample
    #
    # def _get_updated_sample(self, sample_identifier):
    #     edited_annotations = self.save_edited_annotations()
    #     new_annotations = self.save_new_annotations()
    #     all_annotations = dict(**edited_annotations, **new_annotations)
    #     all_annotations[SAMPLE_IDENTIFIER_KEY] = sample_identifier
    #     return all_annotations

    def _update_sample_in_proposal(self, sample_identifier):
        current_samples = self._get_samples()
        new_sample = {SAMPLE_IDENTIFIER_KEY: sample_identifier}
        samples = {}
        if len(current_samples) > 0:
            for index, sample in enumerate(current_samples):
                if not sample.get(SAMPLE_IDENTIFIER_KEY, ""):
                    sample[SAMPLE_IDENTIFIER_KEY] = f"sample {index + 1}"
                samples[index] = sample
                samples[index + 1] = new_sample
        else:
            samples[0] = new_sample
        self._write_samples(samples)

    #
    #
    #
    #     samples = self._get_samples()
    #     update_index = None
    #     for i, sample in enumerate(samples):
    #         for key, value in sample.items():
    #             if key == SAMPLE_IDENTIFIER_KEY and value == sample_identifier:
    #                 update_index = i
    #     if update_index:
    #         samples[update_index] = self._get_updated_sample(sample_identifier)
    #         self._write_samples(samples)
    #

    #

    #


##################################################################################3


class AnnotationRow:
    def __init__(self, key="", value=""):
        self.key_widget = QLabel(key)
        self.edit_key_widget = QLineEdit()
        self.value_widget = QLabel(str(value))
        self.edit_value_widget = QLineEdit()
        self.info_message = QLabel()

    def get_widgets(self):
        return [
            self.key_widget,
            self.edit_key_widget,
            self.value_widget,
            self.edit_value_widget,
            self.info_message,
        ]

    def add_and_align_left(self, layout, row):
        widgets = self.get_widgets()
        for column_index, widget in enumerate(widgets):
            layout.addWidget(
                widget, row, column_index, alignment=Qt.AlignmentFlag.AlignLeft
            )

    def remove(self, layout):
        widgets = self.get_widgets()
        for widget in widgets:
            layout.removeWidget(widget)


class AddControlButtonsLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_add = QPushButton("Add")
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_add, self.layout)

    def add_and_align_left(self, button, layout):
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)


class EditControlButtonsLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.btn_add_annotation = QPushButton("Add field")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.add_and_align_left(self.btn_add_annotation, self.layout)
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_save, self.layout)

    def add_and_align_left(self, button, layout):
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)


class RemoveSampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remove sample")
        buttons = (
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        layout = QVBoxLayout()
        self.message = QLabel()
        layout.addWidget(self.message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class SampleAnnotationWidgetLayout(QWidget):
    ID_ROW = 0

    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.id_layout = QGridLayout()
        self.annotations_layout = QGridLayout()
        self.new_annotations_layout = QGridLayout()
        self.id_row = AnnotationRow()
        self.id_row.add_and_align_left(self.id_layout, self.ID_ROW)
        self.annotation_rows = []
        self.new_annotation_rows = []
        self.layout.addLayout(self.id_layout)
        self.layout.addLayout(self.annotations_layout)
        self.layout.addLayout(self.new_annotations_layout)

    def add_annotation_row(self, key="", value=""):
        current_rows = len(self.annotation_rows)
        i = 0 if current_rows == 0 else current_rows + 1
        annotation_row = AnnotationRow(key, value)
        self.annotation_rows.append(annotation_row)
        annotation_row.add_and_align_left(self.annotations_layout, row=i)

    def remove_annotation_row(self, annotation_row, i):
        annotation_row.remove(self.new_annotations_layout)
        del self.new_annotation_rows[i]


class TopButtonLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edit)
        self.layout.addWidget(self.btn_remove)
        self.layout.addStretch()

import sys

from collections import OrderedDict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class Sample:
    def __init__(self, sample_id):
        self.sample_id = sample_id
        self.annotations = OrderedDict()

    def __repr__(self):
        info = self.sample_id
        for key, val in self.annotations.items():
            info += f"\n{key}: {val}"
        return info

    def set_annotation(self, key, value):
        self.annotations[key] = value


class Proposal:
    def __init__(self, proposal_id):
        self.proposal_id = proposal_id
        self.samples = {}

    def add_sample(self, sample_id):
        new_sample = Sample(sample_id)
        self.samples[sample_id] = new_sample


def get_a_test_proposal():
    a_test_proposal = Proposal(proposal_id="123")

    a_test_proposal.add_sample("Sample1")
    a_test_proposal.samples["Sample1"].set_annotation("state", "solid")
    a_test_proposal.samples["Sample1"].set_annotation("annot_string", "InfoA")
    a_test_proposal.samples["Sample1"].set_annotation("annot_int", 1)
    a_test_proposal.samples["Sample1"].set_annotation("annot_float", 0.5)

    a_test_proposal.add_sample("Sample2")
    a_test_proposal.samples["Sample2"].set_annotation("state", "liquid")
    a_test_proposal.samples["Sample2"].set_annotation("annot_string", "InfoB")
    a_test_proposal.samples["Sample2"].set_annotation("annot_int", 2)
    a_test_proposal.samples["Sample2"].set_annotation("annot_float", 0.4)

    a_test_proposal.add_sample("Sample3")
    a_test_proposal.samples["Sample3"].set_annotation("state", "powder")
    a_test_proposal.samples["Sample3"].set_annotation("annot_string", "InfoC")
    a_test_proposal.samples["Sample3"].set_annotation("annot_int", 3)
    a_test_proposal.samples["Sample3"].set_annotation("annot_float", 0.3)

    a_test_proposal.add_sample("Sample4")
    a_test_proposal.samples["Sample4"].set_annotation("state", "crystal")
    a_test_proposal.samples["Sample4"].set_annotation("annot_string", "InfoD")
    a_test_proposal.samples["Sample4"].set_annotation("annot_int", 4)
    a_test_proposal.samples["Sample4"].set_annotation("annot_float", 0.2)

    return a_test_proposal


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)
        self.setWindowTitle("Sample panel")
        self.setGeometry(800, 800, 1200, 800)

        self.layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.sample_panel = SamplePanel()
        self.layout.addLayout(self.sample_panel.main_layout)


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
        column = 0
        widgets = self.get_widgets()
        for widget in widgets:
            layout.addWidget(
                widget, row, column, alignment=Qt.AlignmentFlag.AlignLeft
            )
            column += 1

    def remove(self, layout):
        widgets = self.get_widgets()
        for widget in widgets:
            layout.removeWidget(widget)


class TopButtonLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edit)
        self.layout.addWidget(self.btn_remove)
        self.layout.addStretch()


class SampleAnnotationWidgetLayout(QWidget):
    ID_ROW = 0

    def __init__(self):
        super().__init__()
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
        if current_rows == 0:
            i = 0
        else:
            i = current_rows + 1
        annotation_row = AnnotationRow(key, value)
        self.annotation_rows.append(annotation_row)
        annotation_row.add_and_align_left(self.annotations_layout, row=i)

    def remove_annotation_row(self, annotation_row, i):
        annotation_row.remove(self.new_annotations_layout)
        del self.new_annotation_rows[i]


class EditControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
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


class AddControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_add = QPushButton("Add")
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_add, self.layout)

    def add_and_align_left(self, button, layout):
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)


class RemoveSampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remove sample")
        buttons = (
            QDialogButtonBox.StandardButton.Yes
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        layout = QVBoxLayout()
        self.message = QLabel()
        layout.addWidget(self.message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class SamplePanel(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.top_buttons = self.construct_top_menu()
        self.sample_selector = self.construct_sample_selector()
        self.edit_ctrl_buttons = self.construct_edit_ctrl_buttons()
        self.add_ctrl_buttons = self.construct_add_ctrl_buttons()
        self.sample_annotations = self.construct_sample_annotations()
        self.sample_annotation_outer_layoutwidget = (
            self.construct_sample_annotation_outer_layoutwidget()
        )
        self.panel_splitter = self.construct_splitter()
        self.main_layout = self.construct_main_layout()
        self.remove_sample_dialog = self.construct_remove_sample_dialog()

        self.proposal = self.load_proposal()

        self.show_empty_view()

    def construct_top_menu(self):
        top_buttons = TopButtonLayout()
        top_buttons.btn_add.clicked.connect(self.add_sample_clicked)
        top_buttons.btn_edit.clicked.connect(self.edit_sample_clicked)
        top_buttons.btn_remove.clicked.connect(self.remove_sample_clicked)
        return top_buttons

    def construct_sample_selector(self):
        sample_selector_widget = QListWidget()
        sample_selector_widget.itemClicked.connect(
            self.sample_selection_updated
        )
        return sample_selector_widget

    def construct_edit_ctrl_buttons(self):
        edit_ctrl_buttons = EditControlButtonsLayout()
        edit_ctrl_buttons.widget = QWidget()
        edit_ctrl_buttons.widget.setLayout(edit_ctrl_buttons.layout)
        edit_ctrl_buttons.btn_add_annotation.clicked.connect(
            self.add_annotation_clicked
        )
        edit_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_edit_clicked)
        edit_ctrl_buttons.btn_save.clicked.connect(self.confirm_edit_clicked)
        return edit_ctrl_buttons

    def construct_add_ctrl_buttons(self):
        add_ctrl_buttons = AddControlButtonsLayout()
        add_ctrl_buttons.widget = QWidget()
        add_ctrl_buttons.widget.setLayout(add_ctrl_buttons.layout)
        add_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_add_clicked)
        add_ctrl_buttons.btn_add.clicked.connect(self.confirm_add_clicked)
        return add_ctrl_buttons

    def construct_sample_annotations(self):
        sample_annotations = SampleAnnotationWidgetLayout()
        return sample_annotations

    def construct_sample_annotation_outer_layoutwidget(self):
        sample_annotation_outer_layout = QVBoxLayout()
        sample_annotation_outer_layout.addLayout(self.sample_annotations.layout)
        sample_annotation_outer_layout.addWidget(self.add_ctrl_buttons.widget)
        sample_annotation_outer_layout.addWidget(self.edit_ctrl_buttons.widget)
        sample_annotation_outer_layout.addStretch()
        sample_annotation_outer_layoutwidget = QWidget()
        sample_annotation_outer_layoutwidget.setLayout(
            sample_annotation_outer_layout
        )
        return sample_annotation_outer_layoutwidget

    def construct_splitter(self):
        panel_splitter = QSplitter()
        panel_splitter.addWidget(self.sample_selector)
        panel_splitter.addWidget(self.sample_annotation_outer_layoutwidget)
        return panel_splitter

    def construct_main_layout(self):
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.top_buttons.layout)
        main_layout.addWidget(self.panel_splitter)
        return main_layout

    def construct_remove_sample_dialog(self):
        dialog = RemoveSampleDialog()
        dialog.buttonBox.accepted.connect(self.confirm_remove_clicked)
        dialog.buttonBox.rejected.connect(self.cancel_remove_clicked)
        return dialog

    def load_proposal(self):
        proposal = get_a_test_proposal()
        self.add_samples_to_selector(proposal)
        return proposal

    def add_samples_to_selector(self, proposal):
        self.sample_selector.addItems(proposal.samples.keys())

    def sample_selection_updated(self, item):
        sample_id = item.text()
        self.display_sample(sample_id)

    def edit_sample_clicked(self):
        self.show_sample_edit_mode()

    def add_sample_clicked(self):
        self.show_add_sample()

    def remove_sample_clicked(self):
        self.show_remove_sample_dialog()

    def add_annotation_clicked(self):
        row_index = len(self.sample_annotations.new_annotation_rows) + 1
        new_annotation_row = AnnotationRow()
        self.sample_annotations.new_annotation_rows.append(new_annotation_row)
        new_annotation_row.add_and_align_left(
            self.sample_annotations.new_annotations_layout, row_index
        )
        self.show_new_sample_annotations_edit()

    def confirm_edit_clicked(self):
        sample_id = self.sample_selector.currentItem().text()
        sample = self.proposal.samples[sample_id]
        self.save_edited_annotations(sample)
        self.save_new_annotations(sample)
        self.set_annotation_values(sample_id)
        self.reset_existing_annotation_values_to_edit()
        self.reset_new_annotation_values_to_edit()
        self.show_sample_view_mode()

    def cancel_edit_clicked(self):
        self.reset_existing_annotation_values_to_edit()
        self.reset_new_annotation_values_to_edit()
        self.discard_new_annotations()
        self.show_sample_view_mode()

    def confirm_add_clicked(self):
        new_sample_id = self.sample_annotations.id_row.edit_value_widget.text()
        if self.check_unique_sample_id(new_sample_id):
            self.proposal.add_sample(new_sample_id)
            new_item = QListWidgetItem(new_sample_id)
            self.sample_selector.addItem(new_item)
            self.sample_selector.setCurrentItem(new_item)
            self.set_id_value(new_sample_id)
            self.check_for_existing_annotation_keys()
            self.reset_new_sample_id()
            self.reset_existing_annotation_values()
            self.show_sample_edit_mode()

    def cancel_add_clicked(self):
        self.reset_new_sample_id()
        self.reset_existing_annotation_values_to_edit()
        self.show_sample_view_mode()
        self.show_empty_view()

    def confirm_remove_clicked(self):
        sample_id = self.sample_selector.currentItem().text()
        del self.proposal.samples[sample_id]
        selected_row = self.sample_selector.currentRow()
        self.sample_selector.takeItem(selected_row)
        self.remove_sample_dialog.close()
        self.show_empty_view()

    def cancel_remove_clicked(self):
        self.show_sample_view_mode()
        self.remove_sample_dialog.close()

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

    def show_sample_edit_mode(self):
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

    def show_remove_sample_dialog(self):
        sample_id = self.sample_selector.currentItem().text()
        self.remove_sample_dialog.message.setText(
            f"Remove sample: '{sample_id}'"
        )
        self.remove_sample_dialog.exec()

    def display_sample(self, sample_id):
        self.set_id_key()
        self.set_id_value(sample_id)
        self.set_annotation_values(sample_id)
        self.show_sample_view_mode()

    def set_id_key(self):
        self.sample_annotations.id_row.key_widget.setText("Sample ID")

    def set_id_value(self, sample_id):
        self.sample_annotations.id_row.value_widget.setText(str(sample_id))

    def set_annotation_keys(self, sample_id):
        sample = self.proposal.samples[sample_id]
        for i, key in enumerate(sample.annotations.keys()):
            if i < len(self.sample_annotations.annotation_rows):
                annotation_row = self.sample_annotations.annotation_rows[i]
                annotation_row.key_widget.setText(str(key))
            else:
                self.sample_annotations.add_annotation_row(key, "")

    def set_annotation_values(self, sample_id):
        sample = self.proposal.samples[sample_id]
        printed_keys = []
        if len(self.sample_annotations.annotation_rows) > 0:
            for annotation_row in self.sample_annotations.annotation_rows:
                key = annotation_row.key_widget.text()
                if key in sample.annotations.keys():
                    value = sample.annotations[key]
                    annotation_row.value_widget.setText(str(value))
                else:
                    annotation_row.value_widget.setText("")
                printed_keys.append(key)
        for key, value in sample.annotations.items():
            if key not in printed_keys:
                self.sample_annotations.add_annotation_row(key, value)

    def copy_existing_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            value = annotation_row.value_widget.text()
            annotation_row.edit_value_widget.setText(str(value))

    def reset_existing_annotation_values(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.value_widget.setText("")

    def reset_existing_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.edit_value_widget.setText("")

    def reset_new_annotation_values_to_edit(self):
        for annotation_row in self.sample_annotations.new_annotation_rows:
            annotation_row.edit_key_widget.setText("")
            annotation_row.edit_value_widget.setText("")

    def reset_new_sample_id(self):
        self.sample_annotations.id_row.edit_value_widget.setText("")

    def save_edited_annotations(self, sample):
        for annotation_row in self.sample_annotations.annotation_rows:
            key = annotation_row.key_widget.text()
            new_value = annotation_row.edit_value_widget.text()
            sample.set_annotation(key, new_value)

    def save_new_annotations(self, sample):
        if len(self.sample_annotations.new_annotation_rows) > 0:
            for i, annotation_row in enumerate(
                self.sample_annotations.new_annotation_rows
            ):
                new_key = annotation_row.edit_key_widget.text()
                new_value = annotation_row.edit_value_widget.text()
                sample.set_annotation(new_key, new_value)
                self.sample_annotations.add_annotation_row(new_key, new_value)
                annotation_row.remove(
                    self.sample_annotations.new_annotations_layout
                )
                del self.sample_annotations.new_annotation_rows[i]

    def discard_new_annotations(self):
        if len(self.sample_annotations.new_annotation_rows) > 0:
            for annotation_row in self.sample_annotations.new_annotation_rows:
                annotation_row.remove(
                    self.sample_annotations.new_annotations_layout
                )
                self.sample_annotations.new_annotation_rows = []

    def check_unique_sample_id(self, sample_id):
        if sample_id == "":
            self.display_missing_id_error()
        elif sample_id in self.proposal.samples.keys():
            self.display_duplicate_id_error()
            return False
        else:
            self.reset_sample_id_error()
            return True

    def display_duplicate_id_error(self):
        self.sample_annotations.id_row.info_message.setText(
            "Sample ID already exist"
        )

    def display_missing_id_error(self):
        self.sample_annotations.id_row.info_message.setText(
            "Please enter a sample ID"
        )

    def reset_sample_id_error(self):
        self.sample_annotations.id_row.info_message.setText("")
        self.sample_annotations.id_row.info_message.setText("")

    def check_for_existing_annotation_keys(self):
        if self.sample_selector.count() > 1:
            existing_sample_id = self.sample_selector.item(0).text()
            self.set_annotation_keys(existing_sample_id)

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

    def show_sample_annotations_edit(self):
        self.copy_existing_annotation_values_to_edit()
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_widget.show()
            annotation_row.value_widget.hide()
            annotation_row.edit_key_widget.hide()
            annotation_row.edit_value_widget.show()

    def show_new_sample_annotations_edit(self):
        for annotation_row in self.sample_annotations.new_annotation_rows:
            annotation_row.key_widget.hide()
            annotation_row.value_widget.hide()
            annotation_row.edit_key_widget.show()
            annotation_row.edit_value_widget.show()

    def hide_sample_annotations(self):
        for annotation_row in self.sample_annotations.annotation_rows:
            annotation_row.key_widget.hide()
            annotation_row.value_widget.hide()
            annotation_row.edit_key_widget.hide()
            annotation_row.edit_value_widget.hide()

    def show_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_add.show()
        self.add_ctrl_buttons.btn_cancel.show()

    def hide_add_ctrl_buttons(self):
        self.add_ctrl_buttons.btn_add.hide()
        self.add_ctrl_buttons.btn_cancel.hide()

    def show_edit_ctrl_buttons(self):
        self.edit_ctrl_buttons.btn_save.show()
        self.edit_ctrl_buttons.btn_cancel.show()
        self.edit_ctrl_buttons.btn_add_annotation.show()

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


if __name__ == "__main__":
    SamplePanelApp = QApplication([])
    SamplePanelWindow = MainWindow()
    SamplePanelWindow.show()

    sys.exit(SamplePanelApp.exec())

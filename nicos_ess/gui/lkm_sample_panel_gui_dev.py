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

    def add_annotation(self, key, value):
        self.annotations[key] = value


class Proposal:
    def __init__(self, proposal_id):
        self.proposal_id = proposal_id
        self.samples = {}
        self.sample_annotation_keys = []

    def add_sample(self, sample_id):
        new_sample = Sample(sample_id)
        self.samples[sample_id] = new_sample

    def sample_updated(self, sample):
        for key in sample.annotations.keys():
            if key not in self.sample_annotation_keys:
                self.sample_annotation_keys.append(key)


def get_a_test_proposal():
    a_test_proposal = Proposal(proposal_id="123")

    a_test_proposal.add_sample("Sample1")
    a_test_proposal.samples["Sample1"].add_annotation("state", "solid")
    a_test_proposal.samples["Sample1"].add_annotation("annot_string", "InfoA")
    a_test_proposal.samples["Sample1"].add_annotation("annot_int", 1)
    a_test_proposal.samples["Sample1"].add_annotation("annot_float", 0.5)
    a_test_proposal.sample_updated(a_test_proposal.samples["Sample1"])

    a_test_proposal.add_sample("Sample2")
    a_test_proposal.samples["Sample2"].add_annotation("state", "liquid")
    a_test_proposal.samples["Sample2"].add_annotation("annot_string", "InfoB")
    a_test_proposal.samples["Sample2"].add_annotation("annot_int", 2)
    a_test_proposal.samples["Sample2"].add_annotation("annot_float", 0.4)
    a_test_proposal.sample_updated(a_test_proposal.samples["Sample2"])

    a_test_proposal.add_sample("Sample3")
    a_test_proposal.samples["Sample3"].add_annotation("state", "powder")
    a_test_proposal.samples["Sample3"].add_annotation("annot_string", "InfoC")
    a_test_proposal.samples["Sample3"].add_annotation("annot_int", 3)
    a_test_proposal.samples["Sample3"].add_annotation("annot_float", 0.3)
    a_test_proposal.sample_updated(a_test_proposal.samples["Sample3"])

    a_test_proposal.add_sample("Sample4")
    a_test_proposal.samples["Sample4"].add_annotation("state", "crystal")
    a_test_proposal.samples["Sample4"].add_annotation("annot_string", "InfoD")
    a_test_proposal.samples["Sample4"].add_annotation("annot_int", 4)
    a_test_proposal.samples["Sample4"].add_annotation("annot_float", 0.2)
    a_test_proposal.sample_updated(a_test_proposal.samples["Sample4"])

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
        self.layout.addLayout(self.sample_panel.sample_main_layout)


class AnnotationWidgetGroup:
    def __init__(self):
        self.key_wid = QLabel()
        self.key_wid_editable = QLineEdit()
        self.val_wid = QLabel()
        self.edt_wid = QLineEdit()
        self.info_message = QLabel()

    def get_widgets(self):
        return [
            self.key_wid,
            self.key_wid_editable,
            self.val_wid,
            self.edt_wid,
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
        self.btn_edt = QPushButton("Edit sample")
        self.btn_rem = QPushButton("Remove sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edt)
        self.layout.addWidget(self.btn_rem)
        self.layout.addStretch()


class SampleInfoWidgetLayout(QWidget):
    ID_ROW = 0

    def __init__(self):
        super().__init__()
        self.grid_layouts = QVBoxLayout()
        self.id_layout = QGridLayout()
        self.info_layout = QGridLayout()
        self.new_fields_layout = QGridLayout()
        self.id_widgets = AnnotationWidgetGroup()
        self.id_widgets.add_and_align_left(self.id_layout, self.ID_ROW)
        self.widgets_list = []
        self.widgets_in_edit = []
        self.grid_layouts.addLayout(self.id_layout)
        self.grid_layouts.addLayout(self.info_layout)
        self.grid_layouts.addLayout(self.new_fields_layout)


    def add_widget_row(self):
        current_rows = len(self.widgets_list)
        if current_rows == 0:
            i = 0
        else:
            i = current_rows + 1
        widget_grp = AnnotationWidgetGroup()
        self.widgets_list.append(widget_grp)
        widget_grp.add_and_align_left(self.info_layout, row=i)

    def remove_widget_row(self, widget_grp, i):
        widget_grp.remove(self.new_fields_layout)
        del self.widgets_in_edit[i]


class EditControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add_info = QPushButton("Add field")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.add_and_align_left(self.btn_add_info, self.layout)
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_save, self.layout)

    def add_and_align_left(self, widget, layout):
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignLeft)


class AddControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_add = QPushButton("Add")
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_add, self.layout)

    def add_and_align_left(self, widget, layout):
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignLeft)


class RemoveSampleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Remove sample")
        buttons = (
            QDialogButtonBox.StandardButton.Yes
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(buttons)
        layout = QVBoxLayout()
        message = QLabel("Remove sample?")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class SamplePanel(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.top_buttons = self.construct_top_menu()
        self.sample_selector_widget = self.construct_sample_selector_widget()
        self.edit_ctrl_buttons = self.construct_edit_ctrl_buttons()
        self.add_ctrl_buttons = self.construct_add_ctrl_buttons()
        self.sample_info = SampleInfoWidgetLayout()
        self.sample_info_widget = self.construct_sample_info_panel()
        self.panel_splitter = self.construct_splitter()
        self.sample_main_layout = self.construct_main_layout()
        self.confirm_remove_dialog = self.construct_remove_sample_dialog()

        self.proposal = self.load_proposal()

        self.start_view()

    #        self.sample_selector_widget.addItems(self.proposal.samples.keys())

    def construct_top_menu(self):
        top_buttons = TopButtonLayout()
        top_buttons.btn_add.clicked.connect(self.add_sample_view)
        top_buttons.btn_edt.clicked.connect(self.edit_sample_view)
        top_buttons.btn_rem.clicked.connect(self.remove_sample_dialog)
        return top_buttons

    def construct_sample_selector_widget(self):
        sample_selector_widget = QListWidget()
        sample_selector_widget.itemClicked.connect(self.sample_view)
        return sample_selector_widget

    def construct_edit_ctrl_buttons(self):
        edit_ctrl_buttons = EditControlButtonsLayout()
        edit_ctrl_buttons.widget = QWidget()
        edit_ctrl_buttons.widget.setLayout(edit_ctrl_buttons.layout)
        edit_ctrl_buttons.btn_add_info.clicked.connect(self.add_info_field)
        edit_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_edit_view)
        edit_ctrl_buttons.btn_save.clicked.connect(self.edit_sample)
        return edit_ctrl_buttons

    def construct_add_ctrl_buttons(self):
        add_ctrl_buttons = AddControlButtonsLayout()
        add_ctrl_buttons.widget = QWidget()
        add_ctrl_buttons.widget.setLayout(add_ctrl_buttons.layout)
        add_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_add_view)
        add_ctrl_buttons.btn_add.clicked.connect(self.add_sample)
        return add_ctrl_buttons

    def construct_sample_info_panel(self):
        sample_info_panel_layout = QVBoxLayout()
        sample_info_panel_layout.addLayout(self.sample_info.grid_layouts)
        sample_info_panel_layout.addWidget(self.add_ctrl_buttons.widget)
        sample_info_panel_layout.addWidget(self.edit_ctrl_buttons.widget)
        sample_info_panel_layout.addStretch()
        sample_info_panel_widget = QWidget()
        sample_info_panel_widget.setLayout(sample_info_panel_layout)
        return sample_info_panel_widget

    def construct_splitter(self):
        panel_splitter = QSplitter()
        panel_splitter.addWidget(self.sample_selector_widget)
        panel_splitter.addWidget(self.sample_info_widget)
        return panel_splitter

    def construct_main_layout(self):
        sample_main_layout = QVBoxLayout()
        sample_main_layout.addLayout(self.top_buttons.layout)
        sample_main_layout.addWidget(self.panel_splitter)
        return sample_main_layout

    def construct_remove_sample_dialog(self):
        dialog = RemoveSampleDialog()
        dialog.buttonBox.accepted.connect(self.remove_sample)
        dialog.buttonBox.rejected.connect(self.sample_view)
        return dialog

    def load_proposal(self):
        proposal = get_a_test_proposal()
        self.update_sample_list(proposal)
        self.update_widget_list(proposal)
        return proposal

    def update_sample_list(self, proposal):
        self.sample_selector_widget.addItems(proposal.samples.keys())

    def update_widget_list(self, proposal):
        if len(proposal.sample_annotation_keys) > 0:
            for _ in proposal.sample_annotation_keys:
                self.sample_info.add_widget_row()

    def start_view(self):
        self.top_buttons.btn_add.setEnabled(True)
        self.top_buttons.btn_edt.setEnabled(False)
        self.top_buttons.btn_rem.setEnabled(False)
        self.hide_all_keys_and_values()
        self.edit_ctrl_buttons.widget.hide()
        self.add_ctrl_buttons.widget.hide()
        self.hide_sample_id_error()
        self.sample_selector_widget.clearSelection()

    def set_key_val_id(self, sample_id):
        self.sample_info.id_widgets.key_wid.setText("Sample ID")
        self.sample_info.id_widgets.val_wid.setText(sample_id)

    def set_key_edit_val_id(self):
        self.sample_info.id_widgets.key_wid.setText("Sample ID")
        self.sample_info.id_widgets.edt_wid.setText("")

    def set_key_val(self, sample_id):
        if len(self.proposal.sample_annotation_keys) > 0:
            for i, key in enumerate(self.proposal.sample_annotation_keys):
                widget_grp = self.sample_info.widgets_list[i]
                widget_grp.key_wid.setText(str(key))
                if key in self.proposal.samples[sample_id].annotations.keys():
                    val = self.proposal.samples[sample_id].annotations[key]
                    widget_grp.val_wid.setText(str(val))
                else:
                    widget_grp.val_wid.setText("")

    def set_key_edit_val(self, sample_id):
        if len(self.proposal.sample_annotation_keys) > 0:
            for i, key in enumerate(self.proposal.sample_annotation_keys):
                widget_grp = self.sample_info.widgets_list[i]
                widget_grp.key_wid.setText(str(key))
                if key in self.proposal.samples[sample_id].annotations.keys():
                    val = self.proposal.samples[sample_id].annotations[key]
                    widget_grp.edt_wid.setText(str(val))
                else:
                    widget_grp.edt_wid.setText("")

    def display_duplicate_id_error(self):
        self.sample_info.id_widgets.info_message.setText(
            "Sample ID already exist"
        )

    def display_missing_id_error(self):
        self.sample_info.id_widgets.info_message.setText(
            "Please enter a sample ID"
        )

    def hide_sample_id_error(self):
        self.sample_info.id_widgets.info_message.setText("")
        self.sample_info.id_widgets.info_message.setText("")

    def hide_all_keys_and_values(self):
        self.sample_info.id_widgets.key_wid.hide()
        self.sample_info.id_widgets.key_wid_editable.hide()
        self.sample_info.id_widgets.val_wid.hide()
        self.sample_info.id_widgets.edt_wid.hide()
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.key_wid.hide()
            widget_grp.key_wid_editable.hide()
            widget_grp.val_wid.hide()
            widget_grp.edt_wid.hide()

    def display_edit_ctrl_buttons(self):
        self.edit_ctrl_buttons.widget.show()
        self.add_ctrl_buttons.widget.hide()

    def display_add_ctrl_buttons(self):
        self.edit_ctrl_buttons.widget.hide()
        self.add_ctrl_buttons.widget.show()

    def hide_ctrl_buttons(self):
        self.edit_ctrl_buttons.widget.hide()
        self.add_ctrl_buttons.widget.hide()

    def display_id_key(self):
        self.sample_info.id_widgets.key_wid.show()

    def display_id_value(self):
        self.sample_info.id_widgets.val_wid.hide()

    def display_id_edit_value(self):
        self.sample_info.id_widgets.edt_wid.show()

    def hide_id_edit_value(self):
        self.sample_info.id_widgets.edt_wid.hide()

    def display_keys(self):
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.key_wid.show()
            widget_grp.key_wid_editable.hide()
            widget_grp.val_wid.hide()
            widget_grp.edt_wid.hide()

    def display_values(self):
        self.sample_info.id_widgets.val_wid.show()
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.val_wid.show()
            widget_grp.edt_wid.hide()

    def display_edit_values(self):
        self.sample_info.id_widgets.val_wid.show()
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.val_wid.hide()
            widget_grp.edt_wid.show()

    def sample_view(self, item=None):
        if item:
            sample_id = item.text()
        else:
            sample_id = self.sample_selector_widget.currentItem().text()
        self.set_key_val_id(sample_id)
        self.set_key_val(sample_id)
        self.display_id_key()
        self.display_id_value()
        self.display_keys()
        self.display_values()
        self.top_buttons.btn_add.setEnabled(True)
        self.top_buttons.btn_edt.setEnabled(True)
        self.top_buttons.btn_rem.setEnabled(True)
        self.sample_selector_widget.setEnabled(True)
        self.hide_ctrl_buttons()
        self.confirm_remove_dialog.close()

    def edit_sample_view(self):
        sample_id = self.sample_selector_widget.currentItem().text()
        self.set_key_val_id(sample_id)
        self.set_key_edit_val(sample_id)
        self.display_id_key()
        self.display_id_value()
        self.hide_id_edit_value()
        self.display_keys()
        self.display_edit_values()
        self.display_edit_ctrl_buttons()
        self.sample_selector_widget.setEnabled(False)

    def add_sample_view(self):
        self.hide_all_keys_and_values()
        self.set_key_edit_val_id()
        self.display_id_key()
        self.display_id_edit_value()
        self.display_add_ctrl_buttons()
        self.top_buttons.btn_add.setEnabled(False)
        self.sample_selector_widget.clearSelection()
        self.sample_selector_widget.setEnabled(False)

    def remove_sample_dialog(self):
        self.confirm_remove_dialog.exec()

    def cancel_add_view(self):
        self.sample_selector_widget.setEnabled(True)
        self.start_view()

    def cancel_edit_view(self):
        self.sample_selector_widget.setEnabled(True)
        while len(self.sample_info.widgets_in_edit) > 0:
            for row_index, widget_grp in enumerate(self.sample_info.widgets_in_edit):
                self.sample_info.remove_widget_row(widget_grp, row_index)
        self.sample_view()

    def check_unique_sample_id(self, sample_id):
        if sample_id == "":
            self.display_missing_id_error()
        elif sample_id in self.proposal.samples.keys():
            self.display_duplicate_id_error()
            return False
        else:
            self.hide_sample_id_error()
            return True

    def add_sample(self):
        new_sample_id = self.sample_info.id_widgets.edt_wid.text()
        if self.check_unique_sample_id(new_sample_id):
            self.proposal.add_sample(new_sample_id)
            new_item = QListWidgetItem(new_sample_id)
            self.sample_selector_widget.addItem(new_item)
            self.sample_selector_widget.setCurrentItem(new_item)
            self.set_key_val_id(new_sample_id)
            self.edit_sample_view()

    def update_existing(self, sample):
        for widget_grp in self.sample_info.widgets_list:
            key = widget_grp.key_wid.text()
            val = widget_grp.edt_wid.text()
            if key in sample.annotations.keys():
                sample.annotations[key] = val
            else:
                sample.add_annotation(key, val)
                self.proposal.sample_updated(sample)

    def update_new(self, sample):
        for widget_grp in self.sample_info.widgets_in_edit:
            key = widget_grp.key_wid_editable.text()
            val = widget_grp.edt_wid.text()
            if key in sample.annotations.keys():
                self.display_existing_annotation_error(widget_grp)
            else:
                sample.add_annotation(key, val)
                self.sample_info.widgets_list.append(widget_grp)
                self.sample_info.widgets_in_edit.pop(widget_grp)
                self.proposal.sample_updated(sample)

    def display_existing_annotation_error(self, widget_grp):
        widget_grp.info_message.setText("Annotation already exist")

    def edit_sample(self):
        sample_id = self.sample_selector_widget.currentItem().text()
        sample = self.proposal.samples[sample_id]
        for widget_grp in self.sample_info.widgets_list:

        self.top_buttons.btn_add.setEnabled(True)
        self.sample_view()

    def remove_sample(self):
        sample_id = self.sample_selector_widget.currentItem().text()
        del self.proposal.samples[sample_id]
        selected_row = self.sample_selector_widget.currentRow()
        self.sample_selector_widget.takeItem(selected_row)
        self.confirm_remove_dialog.close()
        self.start_view()

    def add_info_field(self):
        row_index = len(self.sample_info.widgets_in_edit) + 1
        new_widget_grp = AnnotationWidgetGroup()
        self.sample_info.widgets_in_edit.append(new_widget_grp)
        new_widget_grp.add_and_align_left(self.sample_info.new_fields_layout, row_index)
        new_widget_grp.key_wid.hide()
        new_widget_grp.val_wid.hide()



#         self.display_keys()
#         self.display_edit_values()
#         self.display_edit_ctrl_buttons()


if __name__ == "__main__":
    SamplePanelApp = QApplication([])
    SamplePanelWindow = MainWindow()
    SamplePanelWindow.show()

    sys.exit(SamplePanelApp.exec())

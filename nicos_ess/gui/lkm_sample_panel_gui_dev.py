import sys

from collections import OrderedDict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


# KEY_COLUMN = 0
# VAL_COLUMN = 1
# EDT_COLUMN = 2


class Sample:
    def __init__(self, sample_id, annotations):
        """
        @params
        annotations (OrderedDict)
        """
        self.sample_id = sample_id
        self.annotations = annotations


class Proposal:
    def __init__(self, proposal_id):
        self.proposal_id = proposal_id
        self.samples = {}
        self.sample_annotation_keys = []

    def add_sample(self, sample_id, annotations):
        new_sample = Sample(sample_id, annotations)
        annotation_keys = new_sample.annotations.keys()
        self.samples[sample_id] = new_sample
        self.add_annotation_keys(annotation_keys)

    def add_annotation_keys(self, keys):
        for key in keys:
            if key not in self.sample_annotation_keys:
                self.sample_annotation_keys.append(key)


def get_a_test_proposal():
    a_test_proposal = Proposal(proposal_id="123")
    a_test_proposal.add_sample(
        "Sample1",
        OrderedDict(
            {"annot_string": "InfoA", "annot_int": 1, "annot_float": 0.5}
        ),
    )
    a_test_proposal.add_sample(
        "Sample2",
        OrderedDict(
            {"annot_string": "InfoB", "annot_int": 2, "annot_float": 0.4}
        ),
    )
    a_test_proposal.add_sample(
        "Sample3",
        OrderedDict(
            {"annot_string": "InfoC", "annot_int": 3, "annot_float": 0.3}
        ),
    )
    a_test_proposal.add_sample(
        "Sample4",
        OrderedDict(
            {"annot_string": "InfoD", "annot_int": 4, "annot_float": 0.2}
        ),
    )
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
    def __init__(self, key_wid="", val_wid=""):
        self.key_wid = QLabel(key_wid)
        self.key_wid_editable = QLineEdit()
        self.val_wid = QLabel(val_wid)
        self.edt_wid = QLineEdit()

    def get_widgets(self):
        return [self.key_wid, self.key_wid_editable, self.val_wid, self.edt_wid]

    def add_and_align_left(self, layout, row):
        column = 0
        widgets = self.get_widgets()
        for widget in widgets:
            layout.addWidget(
                widget, row, column, alignment=Qt.AlignmentFlag.AlignLeft
            )
            column += 1


class TopButtonLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edt = QPushButton("Edit sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edt)
        self.layout.addStretch()


class SampleInfoLayout(QWidget):
    ID_ROW = 0

    def __init__(self, N):
        super().__init__()
        self.N = N
        self.widget = QWidget()
        self.grid_layouts = QVBoxLayout()
        self.id_layout = QGridLayout()
        self.info_layout = QGridLayout()
        self.id_widgets = AnnotationWidgetGroup("Sample ID")
        self.id_widgets.add_and_align_left(self.id_layout, self.ID_ROW)
        self.widgets_list = self.get_N_widget_rows()
        self.widgets_in_edit = []
        self.grid_layouts.addLayout(self.id_layout)
        self.grid_layouts.addLayout(self.info_layout)

    def get_N_widget_rows(self):
        widgets_list = []
        for i in range(self.N):
            widget_grp = AnnotationWidgetGroup()
            widgets_list.append(widget_grp)
            widget_grp.add_and_align_left(self.info_layout, row=i)
        return widgets_list


class ControlButtonsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.widget = QWidget()
        self.btn_add_info = QPushButton("Add field")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.add_and_align_left(self.btn_add_info, self.layout)
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_save, self.layout)
        self.widget.setLayout(self.layout)

    def add_and_align_left(self, widget, layout):
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignLeft)


class SamplePanel(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.proposal = get_a_test_proposal()

        self.top_buttons = TopButtonLayout()
        self.top_buttons.btn_add.clicked.connect(self.add_sample)
        self.top_buttons.btn_edt.clicked.connect(self.edit_sample)

        self.sample_selector_widget = QListWidget()
        self.sample_selector_widget.itemClicked.connect(
            self.display_sample_info
        )
        self.sample_info = SampleInfoLayout(
            len(self.proposal.sample_annotation_keys)
        )

        self.ctrl_buttons = ControlButtonsWidget()
        self.ctrl_buttons.btn_add_info.clicked.connect(self.add_info_field)
        self.ctrl_buttons.btn_cancel.clicked.connect(self.cancel_add_or_edit)
        self.ctrl_buttons.btn_save.clicked.connect(self.save_add_or_edit)

        self.sample_info_outer_layout = QVBoxLayout()
        self.sample_info_outer_layout.addLayout(self.sample_info.grid_layouts)
        self.sample_info_outer_layout.addWidget(self.ctrl_buttons.widget)
        self.sample_info_outer_layout.addStretch()
        self.sample_info_widget = QWidget()
        self.sample_info_widget.setLayout(self.sample_info_outer_layout)

        self.panel_splitter = QSplitter()
        self.panel_splitter.addWidget(self.sample_selector_widget)
        self.panel_splitter.addWidget(self.sample_info_widget)

        self.sample_main_widget = QWidget()
        self.sample_main_layout = QVBoxLayout()
        self.sample_main_layout.addLayout(self.top_buttons.layout)
        self.sample_main_layout.addWidget(self.panel_splitter)

        self.sample_selector_widget.addItems(self.proposal.samples.keys())
        for i, annotation in enumerate(self.proposal.sample_annotation_keys):
            widget_grp = self.sample_info.widgets_list[i]
            widget_grp.key_wid.setText(annotation)

        # show relevant widgets

        self.mode_reset()

    def mode_reset(self):
        self.mode_view()
        self.sample_selector_widget.clearSelection()
        self.top_buttons.btn_edt.setEnabled(False)
        self.sample_info.id_widgets.val_wid.setText("")
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.key_wid_editable.setText("")
            widget_grp.val_wid.setText("")
            widget_grp.edt_wid.setText("")

    def mode_view(self):
        self.top_buttons.btn_add.setEnabled(True)
        self.top_buttons.btn_edt.setEnabled(True)
        self.sample_selector_widget.setEnabled(True)
        self.sample_info.id_widgets.key_wid.show()
        self.sample_info.id_widgets.key_wid_editable.hide()
        self.sample_info.id_widgets.val_wid.show()
        self.sample_info.id_widgets.edt_wid.hide()
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.key_wid.show()
            widget_grp.key_wid_editable.hide()
            widget_grp.val_wid.show()
            widget_grp.edt_wid.hide()
        self.ctrl_buttons.widget.hide()

    def mode_edit(self):
        self.top_buttons.btn_add.setEnabled(True)
        self.top_buttons.btn_edt.setEnabled(True)
        self.sample_selector_widget.setEnabled(False)
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.val_wid.hide()
            widget_grp.edt_wid.show()
        self.ctrl_buttons.widget.show()

    def display_sample_info(self, item):
        self.mode_view()
        sample_id = item.text()
        self.sample_info.id_widgets.val_wid.setText(sample_id)
        sample = self.proposal.samples[sample_id]
        for row_index, (key, val) in enumerate(sample.annotations.items()):
            self.sample_info.widgets_list[row_index].key_wid.setText(key)
            self.sample_info.widgets_list[row_index].val_wid.setText(str(val))

    def add_sample(self):
        self.mode_edit()
        self.sample_selector_widget.clearSelection()
        self.sample_info.id_widgets.val_wid.hide()
        self.sample_info.id_widgets.edt_wid.show()
        for widget_grp in self.sample_info.widgets_list:
            widget_grp.edt_wid.setText("")

    def get_current_value(self, row_index):
        return self.sample_info.widgets_list[row_index].val_wid.text()

    def edit_sample(self):
        self.mode_edit()
        self.sample_info.id_widgets.val_wid.show()
        self.sample_info.id_widgets.edt_wid.hide()
        for row_index, widget_grp in enumerate(self.sample_info.widgets_list):
            self.sample_info.widgets_list[row_index].edt_wid.setText(
                self.get_current_value(row_index)
            )

    def get_next_row_index(self):
        n_saved = len(self.sample_info.widgets_list)
        n_in_edit = len(self.sample_info.widgets_in_edit)
        return n_saved + n_in_edit + 1

    def add_info_field(self):
        row_index = self.get_next_row_index()
        new_widget_grp = AnnotationWidgetGroup()
        new_widget_grp.add_and_align_left(self.sample_info.info_layout, row_index)
        new_widget_grp.key_wid.hide()
        new_widget_grp.val_wid.hide()
        self.sample_info.widgets_in_edit.append(new_widget_grp)

    def cancel_add_or_edit(self):
        for widget_grp in self.sample_info_widgets_in_edit:
            self.sample_info_widgets_layout.removeWidget(widget_grp.key_wid)
            self.sample_info_widgets_layout.removeWidget(
                widget_grp.key_wid_editable
            )
            self.sample_info_widgets_layout.removeWidget(widget_grp.val_wid)
            self.sample_info_widgets_layout.removeWidget(widget_grp.edt_wid)
        self.sample_info_widgets_in_edit = []
        self.mode_start()

    def save_add_or_edit(self):
        for widget_grp in self.sample_info_widgets_in_edit:
            self.sample_info_widgets_list.append(widget_grp)
            current_key = widget_grp.key_wid_editable.text()
            widget_grp.key_wid.setText(current_key)
            current_val = widget_grp.edt_wid.text()
            widget_grp.val_wid.setText(current_val)
        self.sample_info_widgets_in_edit = []
        self.mode_view()

        # if add, create sample, add sample to proposal, add annotation keys to proposal
        # if edit, edit sample in proposal
        # question: if a field is added to a sample, should existing samples get a
        # default/NA value?


if __name__ == "__main__":
    SamplePanelApp = QApplication([])
    SamplePanelWindow = MainWindow()
    SamplePanelWindow.show()

    sys.exit(SamplePanelApp.exec())

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


KEY_COLUMN = 0
VAL_COLUMN = 1
EDT_COLUMN = 2


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


class TopButtonLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edt = QPushButton("Edit sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edt)
        self.layout.addStretch()


class SampleInfoLayout(QWidget, N):
    ID_ROW = 0
    def __init__(self):
        super().__init__()
        self.widget = QWidget()
        self.layout = QVBoxLayout()
        self.btn_layout = QHBoxLayout()
        self.id_layout = QGridLayout()
        self.id_widgets = AnnotationWidgetGroup("Sample ID")
        self.add_and_align_left(
            self.id_widgets.get_widgets(),
            self.id_layout,
            self.ID_ROW
        )

    def add_and_align_left(self, widgets, layout, row):
        column = 0
        for widget in widgets:
            layout.addWidget(widget, row, column, alignment=Qt.AlignmentFlag.AlignLeft)
            column += 1


class SamplePanel(QWidget):
    def __init__(self):
        super().__init__(parent=None)

        self.proposal = get_a_test_proposal()

        self.sample_main_layout = QVBoxLayout()

        self.top_buttons = TopButtonLayout()
        self.top_buttons.btn_add.clicked.connect(self.add_sample)
        self.top_buttons.btn_edt.clicked.connect(self.edit_sample)

        self.panel_splitter = QSplitter()

        self.sample_selector_widget = QListWidget()
        self.sample_selector_widget.addItems(self.proposal.samples.keys())
        self.sample_selector_widget.itemClicked.connect(
            self.display_sample_info
        )





        add_wid_left_align(
            self.sample_id_widgets.key_wid, self.sample_id_widgets_layout
        )
        add_wid_left_align(
            self.sample_id_widgets.val_wid, self.sample_id_widgets_layout
        )
        add_wid_left_align(
            self.sample_id_widgets.edt_wid, self.sample_id_widgets_layout
        )

        # annotation rows for all other annotations
        self.sample_info_widgets_layout = QGridLayout()
        self.sample_info_widgets_list = []
        self.sample_info_widgets_in_edit = []
        for row_index, annotation in enumerate(
            self.proposal.sample_annotation_keys
        ):
            widget_grp = AnnotationWidgetGroup(annotation)
            self.sample_info_widgets_list.append(widget_grp)
            add_wid_grid_left_align(
                widget_grp.key_wid,
                self.sample_info_widgets_layout,
                row_index,
                KEY_COLUMN,
            )
            add_wid_grid_left_align(
                widget_grp.val_wid,
                self.sample_info_widgets_layout,
                row_index,
                VAL_COLUMN,
            )
            add_wid_grid_left_align(
                widget_grp.edt_wid,
                self.sample_info_widgets_layout,
                row_index,
                EDT_COLUMN,
            )

        # control buttons for add and editing samples
        self.sample_info_button_row_layout = QHBoxLayout()
        self.sample_info_button_row_widget = QWidget()
        self.button_add_info_field = QPushButton("Add field")
        self.button_cancel = QPushButton("Cancel")
        self.button_save = QPushButton("Save")
        self.button_add_info_field.clicked.connect(self.add_info_field)
        self.button_cancel.clicked.connect(self.cancel_add_or_edit)
        self.button_save.clicked.connect(self.save_add_or_edit)
        add_wid_left_align(
            self.button_add_info_field, self.sample_info_button_row_layout
        )
        self.sample_info_button_row_layout.addStretch()
        add_wid_left_align(
            self.button_cancel, self.sample_info_button_row_layout
        )
        add_wid_left_align(self.button_save, self.sample_info_button_row_layout)
        self.sample_info_button_row_widget.setLayout(
            self.sample_info_button_row_layout
        )
        self.sample_info_button_row_widget.hide()

        # combine widgets and layouts
        self.sample_info_main_layout.addLayout(self.sample_id_widgets_layout)
        self.sample_info_main_layout.addLayout(self.sample_info_widgets_layout)
        self.sample_info_main_layout.addWidget(
            self.sample_info_button_row_widget
        )
        self.sample_info_main_layout.addStretch()
        self.sample_info_main_widget.setLayout(self.sample_info_main_layout)

        self.panel_splitter.addWidget(self.sample_selector_widget)
        self.panel_splitter.addWidget(self.sample_info_main_widget)

        self.sample_main_layout.addLayout(self.top_button_row_layout)
        self.sample_main_layout.addWidget(self.panel_splitter)

        # show relevant widgets
        self.mode_start()

    def mode_start(self):
        self.mode_view()
        self.sample_selector_widget.clearSelection()
        self.button_edit_sample.setEnabled(False)
        self.sample_id_widgets.val_wid.setText("")
        for widget_grp in self.sample_info_widgets_list:
            widget_grp.val_wid.setText("")
            widget_grp.edt_wid.setText("")

    def mode_view(self):
        self.button_add_sample.setEnabled(True)
        self.button_edit_sample.setEnabled(True)
        self.sample_selector_widget.setEnabled(True)
        self.sample_id_widgets.key_wid.show()
        self.sample_id_widgets.val_wid.show()
        self.sample_id_widgets.edt_wid.hide()
        for widget_grp in self.sample_info_widgets_list:
            widget_grp.key_wid.show()
            widget_grp.key_wid_editable.hide()
            widget_grp.val_wid.show()
            widget_grp.edt_wid.hide()
        self.sample_info_button_row_widget.hide()

    def mode_edit(self):
        self.button_add_sample.setEnabled(False)
        self.button_edit_sample.setEnabled(False)
        self.sample_selector_widget.setEnabled(False)
        for widget_grp in self.sample_info_widgets_list:
            widget_grp.val_wid.hide()
            widget_grp.edt_wid.show()
        self.sample_info_button_row_widget.show()

    def display_sample_info(self, item):
        self.mode_view()
        sample_id = item.text()
        self.sample_id_widgets.val_wid.setText(sample_id)
        sample = self.proposal.samples[sample_id]
        for row_index, (key, val) in enumerate(sample.annotations.items()):
            self.sample_info_widgets_list[row_index].key_wid.setText(key)
            self.sample_info_widgets_list[row_index].val_wid.setText(str(val))

    def add_sample(self):
        self.mode_edit()
        self.sample_selector_widget.clearSelection()
        for widget_grp in self.sample_info_widgets_list:
            widget_grp.edt_wid.setText("")
        self.sample_id_widgets.val_wid.hide()
        self.sample_id_widgets.edt_wid.show()

    def edit_sample(self):
        self.mode_edit()
        self.sample_id_widgets.val_wid.show()
        self.sample_id_widgets.edt_wid.hide()
        for row_index, widget_grp in enumerate(self.sample_info_widgets_list):
            current_val = self.sample_info_widgets_list[
                row_index
            ].val_wid.text()
            self.sample_info_widgets_list[row_index].edt_wid.setText(
                current_val
            )

    def get_next_row_index(self):
        n_saved = len(self.sample_info_widgets_list)
        n_in_edit = len(self.sample_info_widgets_in_edit)
        return n_saved + n_in_edit + 1

    def add_info_field(self):
        row_index = self.get_next_row_index()
        new_widget_grp = AnnotationWidgetGroup()
        new_widget_grp.key_wid.hide()
        new_widget_grp.val_wid.hide()
        self.sample_info_widgets_in_edit.append(new_widget_grp)
        add_wid_grid_left_align(
            new_widget_grp.key_wid,
            self.sample_info_widgets_layout,
            row_index,
            KEY_COLUMN,
        )
        add_wid_grid_left_align(
            new_widget_grp.key_wid_editable,
            self.sample_info_widgets_layout,
            row_index,
            KEY_COLUMN,
        )
        add_wid_grid_left_align(
            new_widget_grp.val_wid,
            self.sample_info_widgets_layout,
            row_index,
            VAL_COLUMN,
        )
        add_wid_grid_left_align(
            new_widget_grp.edt_wid,
            self.sample_info_widgets_layout,
            row_index,
            EDT_COLUMN,
        )

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

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


class Sample:
    def __init__(self, sample_id, annotations):
        self.sample_id = sample_id
        self.annotations = annotations  # ordered dict

    def add_sample_annotation(self, key, value):
        self.annotations[key] = value

    def get_sample_annotation(self, annotation):
        return self.annotations[annotation]


class Proposal:
    def __init__(self, proposal_id):
        self.proposal_id = proposal_id
        self.samples = {}
        self.sample_annotation_keys = []

    def add_sample(self, sample_id, annotations):
        new_sample = Sample(sample_id, annotations)
        self.samples[sample_id] = new_sample
        self.add_annotation_keys(new_sample.annotations.keys())

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


class SamplePanel(QWidget):  # QWidget
    def __init__(self):
        super().__init__(parent=None)

        self.proposal = get_a_test_proposal()

        # sample main layout
        self.sample_main_layout = QVBoxLayout()

        # top buttons
        self.top_button_row_layout = QHBoxLayout()
        self.button_add_sample = QPushButton("Add sample")
        self.button_edit_sample = QPushButton("Edit sample")
        self.button_add_sample.clicked.connect(self.add_sample)
        self.button_edit_sample.clicked.connect(self.edit_sample)
        self.top_button_row_layout.addWidget(self.button_add_sample)
        self.top_button_row_layout.addWidget(self.button_edit_sample)
        self.top_button_row_layout.addStretch()

        # splitter for sample list and sample info panels
        self.panel_splitter = QSplitter()

        # left panel, sample list
        self.sample_selector_widget = QListWidget()

        # right panel, sample info
        self.sample_info_main_widget = QWidget()
        self.sample_info_main_layout = QVBoxLayout()

        # annotation row for sample id
        self.sample_id_widgets_layout = QHBoxLayout()
        self.sample_id_widgets_list = [
            QLabel("Sample ID"),
            QLabel(),
            QLineEdit(),
        ]
        for i, widget in enumerate(self.sample_id_widgets_list):
            self.sample_id_widgets_layout.addWidget(
                widget, alignment=Qt.AlignmentFlag.AlignLeft
            )

        # annotation rows for all other annotations
        self.sample_info_widgets_layout = QGridLayout()
        self.sample_info_widgets_list = []
        for i, annotation in enumerate(self.proposal.sample_annotation_keys):
            row = [QLabel(annotation), QLabel(), QLineEdit()]
            self.sample_info_widgets_list.append(row)
            for j, widget in enumerate(row):
                self.sample_info_widgets_layout.addWidget(
                    widget, i, j, alignment=Qt.AlignmentFlag.AlignLeft
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
        self.sample_info_button_row_layout.addWidget(
            self.button_add_info_field, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.sample_info_button_row_layout.addStretch()
        self.sample_info_button_row_layout.addWidget(
            self.button_cancel, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.sample_info_button_row_layout.addWidget(
            self.button_save, alignment=Qt.AlignmentFlag.AlignRight
        )
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

        # populate sample list
        self.sample_selector_widget.addItems(self.proposal.samples.keys())
        self.sample_selector_widget.itemClicked.connect(
            self.display_sample_info
        )

        self.status_view()

    def status_view(self):
        #  add button enabled
        self.button_add_sample.setEnabled(True)
        #  edit button disabled
        self.button_edit_sample.setDisabled(True)
        #  sample selector enabled / none selected
        self.sample_selector_widget.setEnabled(True)
        self.sample_selector_widget.clearSelection()
        #  sample ID view mode
        self.sample_id_widgets_list[0].show()
        self.sample_id_widgets_list[1].show()
        self.sample_id_widgets_list[2].hide()
        #  sample info view mode
        for i, row in enumerate(self.sample_info_widgets_list):
            for j, widget in enumerate(row):
                if j == 2:
                    widget.hide()
                else:
                    widget.show()
        #  add field, cancel, save button hidden
        self.sample_info_button_row_widget.hide()

    def left_panel_disabled(self):
        self.button_add_sample.setDisabled(True)
        self.button_edit_sample.setDisabled(True)
        self.sample_selector_widget.setDisabled(True)

    def display_sample_info(self, item):
        if item is not None:
            # status
            #  add button enabled
            #  edit button enabled
            #  sample selector enabled
            #  sample ID view mode
            #  sample info view mode
            #  add field button hidden
            #  cancel, save button hidden
            sample_id = item.text()
            self.sample_id_widgets_list[1].setText(sample_id)
            sample = self.proposal.samples[sample_id]
            for i, (key, val) in enumerate(sample.annotations.items()):
                self.sample_info_widgets_list[i][0].setText(key)
                self.sample_info_widgets_list[i][1].setText(str(val))
            self.button_edit_sample.setEnabled(True)
        else:
            # triggered from cancel button
            self.sample_id_widgets_list[1].setText("")
            for i in range(len(self.sample_info_widgets_list)):
                self.sample_info_widgets_list[i][1].setText("")

    def add_sample(self):
        # status
        #  add button disabled
        #  edit button disabled
        #  sample selector disabled
        #  sample ID edit mode
        #  sample info edit mode
        #  add field button shown
        #  cancel, save button shown
        self.sample_id_widgets_list[1].hide()
        self.sample_id_widgets_list[2].show()
        for i, key in enumerate(self.proposal.sample_annotation_keys):
            self.sample_info_widgets_list[i][0].setText(key)
            self.sample_info_widgets_list[i][1].hide()
            self.sample_info_widgets_list[i][2].show()
        self.sample_info_button_row_widget.show()
        self.left_panel_disabled()

    def edit_sample(self):
        # status
        #  add button disabled
        #  edit button disabled
        #  sample selector disabled
        #  sample ID view mode
        #  sample info edit mode
        #  add field button shown
        #  cancel, save button shown
        sample_id = self.sample_selector_widget.currentItem().text()
        sample = self.proposal.samples[sample_id]
        for i, (key, val) in enumerate(sample.annotations.items()):
            self.sample_info_widgets_list[i][1].hide()
            self.sample_info_widgets_list[i][2].show()
            self.sample_info_widgets_list[i][2].setText(str(val))
        self.sample_info_button_row_widget.show()
        self.left_panel_disabled()

    def add_info_field(self):
        # go to start status
        n_rows = len(self.sample_info_widgets_list)
        new_widgets = [QLineEdit(), QLabel(), QLineEdit()]
        self.sample_info_widgets_list.append(new_widgets)
        for j, widget in enumerate(new_widgets):
            self.sample_info_widgets_layout.addWidget(
                widget, n_rows + 1, j, alignment=Qt.AlignmentFlag.AlignLeft
            )
            if j == 1:
                widget.hide()

    def cancel_add_or_edit(self):
        self.sample_id_widgets_list[2].setText("")
        remove_empty_fields = []
        for i, row in enumerate(self.sample_info_widgets_list):
            for j, widget in enumerate(row):
                if j == 0:
                    if widget.text() == "":
                        remove_empty_fields.append(i)
                if j == 2:
                    widget.setText("")
        if len(remove_empty_fields) > 0:
            for index in remove_empty_fields:
                print(index)
                print(len(self.sample_info_widgets_list))
                del self.sample_info_widgets_list[index]
                print(len(self.sample_info_widgets_list))
        self.status_view()
        self.display_sample_info(None)

    def save_add_or_edit(self):
        # go to start status
        print("not implemented")
        self.status_view()


if __name__ == "__main__":
    SamplePanelApp = QApplication([])
    SamplePanelWindow = MainWindow()
    SamplePanelWindow.show()

    sys.exit(SamplePanelApp.exec())

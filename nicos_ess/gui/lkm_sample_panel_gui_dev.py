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
    def __init__(self, sample_id, annotation_string):
        self.sample_id = sample_id
        self.annotations = OrderedDict()
        self.annotations["annotation_string"] = annotation_string  # None
        self.annotations["annotation_int"] = 2  # None
        self.annotations["annotation_float"] = 0.5  # None

    def add_sample_annotation(self, key, value):
        self.annotations[key] = value

    def get_sample_annotation(self, annotation):
        return self.annotations[annotation]


class Proposal:
    def __init__(self, proposal_id):
        self.proposal_id = proposal_id
        self.samples = {}
        self.sample_annotation_keys = []

    def add_sample(self, sample_id, annotation_string):
        new_sample = Sample(sample_id, annotation_string)
        self.samples[sample_id] = new_sample
        self.add_annotation_keys(new_sample.annotations.keys())

    def add_annotation_keys(self, keys):
        for key in keys:
            if key not in self.sample_annotation_keys:
                self.sample_annotation_keys.append(key)


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

        self.proposal = Proposal(proposal_id="123")
        self.proposal.add_sample("Sample1", "InfoA")
        self.proposal.add_sample("Sample2", "InfoB")
        self.proposal.add_sample("Sample3", "InfoC")
        self.proposal.add_sample("Sample4", "InfoD")

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
        self.sample_id_row_layout = QHBoxLayout()
        self.sample_id_key_label = QLabel("Sample ID")
        self.sample_id_value_label = QLabel()
        self.sample_id_edit_field = QLineEdit()
        self.sample_id_edit_field.hide()
        self.sample_id_row_layout.addWidget(self.sample_id_key_label)
        self.sample_id_row_layout.addWidget(self.sample_id_value_label)

        # annotation rows for all other annotations
        self.sample_info_widgets_layout = QGridLayout()
        self.sample_info_widgets_list = []
        for i, annotation in enumerate(self.proposal.sample_annotation_keys):
            row = [QLabel(annotation), QLabel("placeholder"), QLineEdit("placeholder")]
            self.sample_info_widgets_list.append(row)
            for j, widget in enumerate(row):
                self.sample_info_widgets_layout.addWidget(widget, i, j)
                if j == 2:
                    # hide the widgets for editing
                    widget.hide()

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
        self.sample_info_button_row_widget.setLayout(self.sample_info_button_row_layout)
        self.sample_info_button_row_widget.hide()

        # combine widgets and layouts
        self.sample_info_main_layout.addLayout(self.sample_id_row_layout)
        self.sample_info_main_layout.addLayout(self.sample_info_widgets_layout)
        self.sample_info_main_layout.addWidget(self.sample_info_button_row_widget)
        self.sample_info_main_layout.addStretch()
        self.sample_info_main_widget.setLayout(self.sample_info_main_layout)

        self.panel_splitter.addWidget(self.sample_selector_widget)
        self.panel_splitter.addWidget(self.sample_info_main_widget)

        self.sample_main_layout.addLayout(self.top_button_row_layout)
        self.sample_main_layout.addWidget(self.panel_splitter)

        #
        # # populate sample list
        # self.sample_selector.addItems(self.proposal.samples.keys())
        # self.sample_selector.itemClicked.connect(self.display_sample_info)
        #
        # # buttons for save and cancel adding and editing

    def display_sample_info(self, item):
        sample = self.proposal.samples[item.text()]
        for i, (key, val) in enumerate(sample.annotations.items()):
            self.sample_field_widgets[i][0].setText(key)
            self.sample_field_widgets[i][1].setText(str(val))

    def add_sample(self):
        for i, key in enumerate(self.proposal.sample_annotation_keys):
            self.sample_field_widgets[i][0].setText(key)
            self.sample_field_widgets[i][1].hide()
            self.sample_field_widgets[i][2].show()
        self.sample_selector.setDisabled(True)
        self.sample_info_button_layout = QHBoxLayout()
        self.sample_info_button_layout.addWidget(
            self.button_new_field, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self.sample_info_button_layout.addWidget(
            self.button_cancel, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.sample_info_button_layout.addWidget(
            self.button_save, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.sample_field_layout.addLayout(self.sample_info_button_layout)

    def edit_sample(self):
        for i, widget_row in enumerate(self.sample_info_widgets_list):
            for j, widget in enumerate(widget_row):
                if j == 1:
                    widget.hide()
                if j == 2:
                    # hide the widgets for editing
                    widget.show()
        self.sample_info_button_row_widget.show()

    def add_info_field(self):
        print("not implemented")

    def cancel_add_or_edit(self):
        for i, widget_row in enumerate(self.sample_info_widgets_list):
            for j, widget in enumerate(widget_row):
                if j == 1:
                    widget.show()
                if j == 2:
                    # hide the widgets for editing
                    widget.hide()
        self.sample_info_button_row_widget.hide()

    def save_add_or_edit(self):
        print("not implemented")


if __name__ == "__main__":
    SamplePanelApp = QApplication([])
    SamplePanelWindow = MainWindow()
    SamplePanelWindow.show()

    sys.exit(SamplePanelApp.exec())

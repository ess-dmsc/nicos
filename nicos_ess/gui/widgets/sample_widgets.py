from nicos.guisupport.qt import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtWidgets import QAbstractItemView


class SamplePanelWidgets(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.add_row_btn = None
        self.delete_row_btn = None
        self.add_dialog = None
        self.remove_dialog = None

        self.top_add_remove_btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_remove = QPushButton("Remove sample")
        self.top_add_remove_btn_layout.addWidget(self.btn_add)
        self.top_add_remove_btn_layout.addWidget(self.btn_remove)
        self.top_add_remove_btn_layout.addStretch()

        self.side_edit_btn_layout = QVBoxLayout()
        self.btn_edit = QPushButton("Edit sample")
        self.btn_custom = QPushButton("Customise properties")
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_TEST_PRINT = QPushButton("TESTING: Print samples")

        self.side_edit_btn_layout.addWidget(self.btn_edit)
        self.side_edit_btn_layout.addWidget(self.btn_custom)
        self.side_edit_btn_layout.addWidget(self.btn_save)
        self.side_edit_btn_layout.addWidget(self.btn_cancel)
        self.side_edit_btn_layout.addWidget(self.btn_TEST_PRINT)
        self.side_edit_btn_layout.addStretch()

        self.selector = QListWidget()

        self.PROPERTY_COL_INDEX = 0
        self.VALUE_COL_INDEX = 1
        self.info_table = QTableWidget()
        self.info_table.setColumnCount(2)
        property_item = QTableWidgetItem("Sample property")
        value_item = QTableWidgetItem("Value")
        self.info_table.setHorizontalHeaderItem(self.PROPERTY_COL_INDEX, property_item)
        self.info_table.setHorizontalHeaderItem(self.VALUE_COL_INDEX, value_item)
        self.info_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.horizontal_layout = QHBoxLayout()
        self.horizontal_layout.addWidget(self.selector)
        self.horizontal_layout.addWidget(self.info_table)
        self.horizontal_layout.addLayout(self.side_edit_btn_layout)

        self.sample_panel_widget = QWidget()
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.top_add_remove_btn_layout)
        self.layout.addLayout(self.horizontal_layout)
        self.sample_panel_widget.setLayout(self.layout)

    def create_add_row_button(self, signal=None):
        self.add_row_btn = QPushButton("Add row")
        self.add_row_btn.clicked.connect(signal)

    def create_delete_row_button(self, signal=None):
        self.delete_row_btn = QPushButton("Delete row")
        self.delete_row_btn.clicked.connect(signal)


class AddSampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add sample")
        btns = (
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(btns)
        self.dialog_layout = QVBoxLayout()
        self.input_layout = QHBoxLayout()

        self.info = QLabel("Add sample:")
        self.sample_id = QLineEdit()
        self.message = QLabel()

        self.input_layout.addWidget(self.info)
        self.input_layout.addWidget(self.sample_id)

        self.dialog_layout.addLayout(self.input_layout)
        self.dialog_layout.addWidget(self.message)
        self.dialog_layout.addWidget(self.button_box)
        self.setLayout(self.dialog_layout)


class RemoveSampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remove sample")
        btns = (
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(btns)
        self.dialog_layout = QVBoxLayout()
        self.message = QLabel()
        self.dialog_layout.addWidget(self.message)
        self.dialog_layout.addWidget(self.button_box)
        self.setLayout(self.dialog_layout)

from nicos.guisupport.qt import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SamplePanelWidgets(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.spacer_height = QLabel()
        self.spacer_width_wide = QLabel()
        self.spacer_width_wide.setFixedSize(200, 10)
        self.spacer_width_narrow = QLabel()
        self.spacer_width_narrow.setFixedSize(40, 10)

        self.top_btns_layout_left = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.top_btns_layout_left.addWidget(self.btn_add)
        self.top_btns_layout_left.addWidget(self.btn_edit)
        self.top_btns_layout_left.addWidget(self.btn_remove)
        self.top_btns_layout_left.addStretch()

        self.top_btns_right = QWidget()
        self.top_btns_layout_right = QHBoxLayout()
        self.btn_custom = QPushButton("Customize properties")
        self.top_btns_layout_right.addWidget(self.btn_custom)
        self.top_btns_layout_right.addStretch()

        self.save_btns = QWidget()
        self.save_btns_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.save_btns_layout.addWidget(self.btn_cancel)
        self.save_btns_layout.addWidget(self.btn_save)
        self.save_btns_layout.addStretch()
        self.save_btns.setLayout(self.save_btns_layout)

        self.save_btns_grid_layout = QGridLayout()
        self.save_btns_grid_layout.addWidget(self.spacer_height, 0, 0)
        self.save_btns_grid_layout.addWidget(self.spacer_height, 1, 0)
        self.save_btns_grid_layout.addWidget(self.save_btns, 2, 0)
        self.save_btns_grid_layout.setColumnStretch(
            self.save_btns_grid_layout.columnCount(), 1
        )

        self.add_prop_grid_layout = QGridLayout()
        self.btn_add_prop = QPushButton("Add sample property")
        self.spacer_height = QLabel()
        self.add_prop_grid_layout.addWidget(self.spacer_height, 0, 0)
        self.add_prop_grid_layout.addWidget(self.btn_add_prop, 1, 0)
        self.add_prop_grid_layout.setColumnStretch(
            self.add_prop_grid_layout.columnCount(), 1
        )

        self.sample_selector = QListWidget()

        self.sample_info_grid_layout = QGridLayout()
        self.header_key = QLabel("Property")
        self.header_val = QLabel("Value")
        self.header_key.setStyleSheet("font-weight:bold;")
        self.header_val.setStyleSheet("font-weight:bold;")
        self.sample_info_grid_layout.addWidget(self.header_key, 0, 0)
        self.sample_info_grid_layout.addWidget(self.header_val, 0, 1)
        self.sample_info_grid_layout.addWidget(self.spacer_width_wide, 1, 0)
        self.sample_info_grid_layout.setColumnStretch(
            self.sample_info_grid_layout.columnCount(), 1
        )

        self.left_layout = QVBoxLayout()
        self.left_layout.addLayout(self.top_btns_layout_left)
        self.left_layout.addWidget(self.spacer_height)
        self.left_layout.addWidget(self.sample_selector)

        self.right_layout = QVBoxLayout()
        self.right_layout.addLayout(self.top_btns_layout_right)
        self.right_layout.addWidget(self.spacer_height)
        self.right_layout.addLayout(self.sample_info_grid_layout)
        self.right_layout.addLayout(self.add_prop_grid_layout)
        self.right_layout.addLayout(self.save_btns_grid_layout)
        self.right_layout.addStretch()

        self.sample_panel_widget = QWidget()
        self.layout = QHBoxLayout()
        self.layout.addLayout(self.left_layout)
        self.layout.addWidget(self.spacer_width_narrow)
        self.layout.addLayout(self.right_layout)
        self.layout.addStretch()
        self.sample_panel_widget.setLayout(self.layout)


class RemoveSampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remove sample")
        btns = (
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(btns)
        self.layout = QVBoxLayout()
        self.message = QLabel()
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

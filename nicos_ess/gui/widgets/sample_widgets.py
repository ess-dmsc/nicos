from nicos.guisupport.qt import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class SamplePanelWidgets(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.spacer_height = QLabel()
        self.spacer_width = QLabel()
        self.spacer_width.setFixedSize(150, 10)

        self.top_btns = QWidget()
        self.top_btns_layout_row_first = QHBoxLayout()
        self.top_btns_layout_row_second = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.btn_custom = QPushButton("Customize Properties")
        self.top_btns_layout_row_first.addWidget(self.btn_add)
        self.top_btns_layout_row_first.addWidget(self.btn_edit)
        self.top_btns_layout_row_first.addWidget(self.btn_remove)
        self.top_btns_layout_row_first.addStretch()
        self.top_btns_layout_row_second.addWidget(self.btn_custom)
        self.top_btns_layout_row_second.addStretch()
        self.top_btns_layout = QVBoxLayout()
        self.top_btns_layout.addLayout(self.top_btns_layout_row_first)
        self.top_btns_layout.addLayout(self.top_btns_layout_row_second)
        self.top_btns.setLayout(self.top_btns_layout)

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
        self.btn_add.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer_height = QLabel()
        self.add_prop_grid_layout.addWidget(self.spacer_height, 0, 0)
        self.add_prop_grid_layout.addWidget(self.btn_add_prop, 1, 0)
        self.add_prop_grid_layout.setColumnStretch(
            self.add_prop_grid_layout.columnCount(), 1
        )

        self.sample_selector = QListWidget()

        self.sample_info = QWidget()
        self.sample_info_layout = QVBoxLayout()

        self.sample_info_grid_layout = QGridLayout()
        self.header_key = QLabel("Property")
        self.header_val = QLabel("Value")
        self.spacer_width = QLabel()
        self.spacer_width.setFixedSize(150, 10)
        self.header_key.setStyleSheet("font-weight:bold;")
        self.header_val.setStyleSheet("font-weight:bold;")
        self.sample_info_grid_layout.addWidget(self.header_key, 0, 0)
        self.sample_info_grid_layout.addWidget(self.header_val, 0, 1)
        self.sample_info_grid_layout.addWidget(self.spacer_width, 1, 0)
        self.sample_info_grid_layout.setColumnStretch(
            self.sample_info_grid_layout.columnCount(), 1
        )

        self.sample_info_layout.addLayout(self.sample_info_grid_layout)
        self.sample_info_layout.addLayout(self.add_prop_grid_layout)
        self.sample_info_layout.addLayout(self.save_btns_grid_layout)
        self.sample_info_layout.addStretch()
        self.sample_info.setLayout(self.sample_info_layout)

        self.panel_splitter = QSplitter()
        self.panel_splitter.addWidget(self.sample_selector)
        self.panel_splitter.addWidget(self.sample_info)
        self.panel_splitter.setStretchFactor(0, 1)
        self.panel_splitter.setStretchFactor(1, 12)


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

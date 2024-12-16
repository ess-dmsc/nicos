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

        self.top_btns = QWidget()
        self.top_btns_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.top_btns_layout.addWidget(self.btn_add)
        self.top_btns_layout.addWidget(self.btn_edit)
        self.top_btns_layout.addWidget(self.btn_remove)
        self.top_btns_layout.addStretch()
        self.top_btns.setLayout(self.top_btns_layout)

        self.save_btns_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.save_btns_layout.addWidget(self.btn_cancel)
        self.save_btns_layout.addWidget(self.btn_save)
        self.save_btns_layout.addStretch()

        self.add_prop_layout = QGridLayout()
        self.btn_add_prop = QPushButton("Add sample property")
        self.btn_add.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer_label = QLabel()
        self.add_prop_layout.addWidget(self.spacer_label, 0, 0)
        self.add_prop_layout.addWidget(self.btn_add_prop, 1, 0)
        self.add_prop_layout.addWidget(self.spacer_label, 2, 0)
        self.add_prop_layout.addWidget(self.spacer_label, 3, 0)
        self.add_prop_layout.addWidget(self.spacer_label, 4, 0)
        self.add_prop_layout.setColumnStretch(self.add_prop_layout.columnCount(), 1)

        self.sample_selector = QListWidget()

        self.sample_info = QWidget()
        self.sample_info_layout = QVBoxLayout()

        self.sample_info_grid_layout = QGridLayout()
        self.header_key = QLabel("Property")
        self.header_val = QLabel("Value")
        self.header_key.setStyleSheet("font-weight:bold;")
        self.header_val.setStyleSheet("font-weight:bold;")
        self.sample_info_grid_layout.addWidget(self.header_key, 0, 0)
        self.sample_info_grid_layout.addWidget(self.header_val, 0, 1)
        self.sample_info_grid_layout.setColumnStretch(
            self.sample_info_grid_layout.columnCount(), 1
        )

        self.sample_info_layout.addLayout(self.sample_info_grid_layout)
        self.sample_info_layout.addLayout(self.add_prop_layout)
        self.sample_info_layout.addLayout(self.save_btns_layout)
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

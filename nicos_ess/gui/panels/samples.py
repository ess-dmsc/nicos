from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTimer,
    QTreeWidget,
    QVBoxLayout,
)


class SamplePanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self._build_ui()

    def _build_ui(self):
        self._create_widgets()
        self._set_layout()
        self._format_layout()

    def _create_widgets(self):
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Samples")
        self.btn_new = QPushButton("New")
        self.btn_remove = QPushButton("Remove")
        self.btn_duplicate = QPushButton("Duplicate")

        self.table = QTableWidget()
        self.table.setRowCount(100)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Label", "Value"])
        self.btn_edit = QPushButton("Edit")
        self.btn_save = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")

    def _set_layout(self):
        tree_btn_layout = QHBoxLayout()
        tree_btn_layout.addWidget(self.btn_new)
        tree_btn_layout.addWidget(self.btn_duplicate)
        tree_btn_layout.addWidget(self.btn_remove)
        tree_btn_layout.addStretch()
        tree_layout = QVBoxLayout()
        tree_layout.addWidget(self.tree)
        tree_layout.addLayout(tree_btn_layout)

        table_btn_layout = QHBoxLayout()
        table_btn_layout.addWidget(self.btn_edit)
        table_btn_layout.addWidget(self.btn_save)
        table_btn_layout.addWidget(self.btn_cancel)
        table_btn_layout.addStretch()
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addLayout(table_btn_layout)

        self.layout = QHBoxLayout()
        self.layout.addLayout(tree_layout)
        self.layout.addLayout(table_layout)
        self.setLayout(self.layout)

    def _format_layout(self):
        def _initial_label_column_width():
            self.table.setColumnWidth(0, 200)

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        QTimer.singleShot(0, _initial_label_column_width)

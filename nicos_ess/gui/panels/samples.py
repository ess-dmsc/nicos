from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
    # QAction,
    # QCursor,
    # QHeaderView,
    # QItemDelegate,
    # QKeySequence,
    # QMenu,
    # QShortcut,
    # Qt,
    # QTableView,
    # QTableWidgetItem,
    # pyqtSlot,
)

from nicos_ess.gui.panels.panel import PanelBase


class SamplePanel(PanelBase):
    panelName = "Sample info panel"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        self.parent = parent
        self.options = options

        self.top_buttons = self.construct_top_menu()
        self.add_ctrl_buttons = self.construct_add_ctrl_buttons()
        self.edit_ctrl_buttons = self.construct_edit_ctrl_buttons()
        self.sample_selector = self.construct_sample_selector()

        self.a_button = QPushButton("Click me")
        self.a_button.clicked.connect(self.button_clicked)
        self.a_label = QLabel("")

        layout = QVBoxLayout()
        layout.addLayout(self.top_buttons.layout)
        layout.addWidget(self.add_ctrl_buttons.widget)
        layout.addWidget(self.edit_ctrl_buttons.widget)
        layout.addWidget(self.a_button)
        layout.addWidget(self.a_button)

        self.setLayout(layout)

        print("working?")

    def construct_top_menu(self):
        top_buttons = TopButtonLayout()
        # top_buttons.btn_add.clicked.connect(self.add_sample_clicked)
        # top_buttons.btn_edit.clicked.connect(self.edit_sample_clicked)
        # top_buttons.btn_remove.clicked.connect(self.remove_sample_clicked)
        return top_buttons

    def construct_add_ctrl_buttons(self):
        add_ctrl_buttons = AddControlButtonsLayout()
        add_ctrl_buttons.widget = QWidget()
        add_ctrl_buttons.widget.setLayout(add_ctrl_buttons.layout)
        # add_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_add_clicked)
        # add_ctrl_buttons.btn_add.clicked.connect(self.confirm_add_clicked)
        return add_ctrl_buttons

    def construct_edit_ctrl_buttons(self):
        edit_ctrl_buttons = EditControlButtonsLayout()
        edit_ctrl_buttons.widget = QWidget()
        edit_ctrl_buttons.widget.setLayout(edit_ctrl_buttons.layout)
        # edit_ctrl_buttons.btn_add_annotation.clicked.connect(
        #     self.add_annotation_clicked
        # )
        # edit_ctrl_buttons.btn_cancel.clicked.connect(self.cancel_edit_clicked)
        # edit_ctrl_buttons.btn_save.clicked.connect(self.confirm_edit_clicked)
        return edit_ctrl_buttons

    def construct_sample_selector(self):
        sample_selector_widget = QListWidget()
        # sample_selector_widget.itemClicked.connect(self.sample_selection_updated)
        return sample_selector_widget

    def button_clicked(self):
        self.a_label.setText("Hello!")


class AddControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_add = QPushButton("Add")
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_add, self.layout)

    def add_and_align_left(self, button, layout):
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)


class EditControlButtonsLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add_annotation = QPushButton("Add field")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.add_and_align_left(self.btn_add_annotation, self.layout)
        self.layout.addStretch()
        self.add_and_align_left(self.btn_cancel, self.layout)
        self.add_and_align_left(self.btn_save, self.layout)

    def add_and_align_left(self, button, layout):
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)


class TopButtonLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edit)
        self.layout.addWidget(self.btn_remove)
        self.layout.addStretch()
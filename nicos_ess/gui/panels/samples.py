from nicos.guisupport.qt import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
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
        self.sample_annotations = self.construct_sample_annotations()
        self.sample_annotation_outer_layoutwidget = (
            self.construct_sample_annotation_outer_layoutwidget()
        )
        self.panel_splitter = self.construct_splitter()

        self.a_button = QPushButton("Click me")
        self.a_button.clicked.connect(self.button_clicked)
        self.a_label = QLabel("")

        layout = QVBoxLayout()
        layout.addLayout(self.top_buttons.layout)
        layout.addWidget(self.panel_splitter)
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

    def construct_sample_annotations(self):
        sample_annotations = SampleAnnotationWidgetLayout()
        return sample_annotations

    def construct_sample_annotation_outer_layoutwidget(self):
        sample_annotation_outer_layout = QVBoxLayout()
        sample_annotation_outer_layout.addLayout(self.sample_annotations.layout)
        sample_annotation_outer_layout.addWidget(self.add_ctrl_buttons.widget)
        sample_annotation_outer_layout.addWidget(self.edit_ctrl_buttons.widget)
        sample_annotation_outer_layout.addStretch()
        sample_annotation_outer_layoutwidget = QWidget()
        sample_annotation_outer_layoutwidget.setLayout(sample_annotation_outer_layout)
        return sample_annotation_outer_layoutwidget

    def construct_splitter(self):
        panel_splitter = QSplitter()
        panel_splitter.addWidget(self.sample_selector)
        panel_splitter.addWidget(self.sample_annotation_outer_layoutwidget)
        return panel_splitter

    def button_clicked(self):
        self.a_label.setText("Hello!")


class AnnotationRow:
    def __init__(self, key="", value=""):
        self.key_widget = QLabel(key)
        self.edit_key_widget = QLineEdit()
        self.value_widget = QLabel(str(value))
        self.edit_value_widget = QLineEdit()
        self.info_message = QLabel()

    def get_widgets(self):
        return [
            self.key_widget,
            self.edit_key_widget,
            self.value_widget,
            self.edit_value_widget,
            self.info_message,
        ]

    def add_and_align_left(self, layout, row):
        widgets = self.get_widgets()
        for column_index, widget in enumerate(widgets):
            layout.addWidget(
                widget, row, column_index, alignment=Qt.AlignmentFlag.AlignLeft
            )

    def remove(self, layout):
        widgets = self.get_widgets()
        for widget in widgets:
            layout.removeWidget(widget)


class AddControlButtonsLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
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
        QWidget.__init__(self)
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


class SampleAnnotationWidgetLayout(QWidget):
    ID_ROW = 0

    def __init__(self):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.id_layout = QGridLayout()
        self.annotations_layout = QGridLayout()
        self.new_annotations_layout = QGridLayout()
        self.id_row = AnnotationRow()
        self.id_row.add_and_align_left(self.id_layout, self.ID_ROW)
        self.annotation_rows = []
        self.new_annotation_rows = []
        self.layout.addLayout(self.id_layout)
        self.layout.addLayout(self.annotations_layout)
        self.layout.addLayout(self.new_annotations_layout)

    def add_annotation_row(self, key="", value=""):
        current_rows = len(self.annotation_rows)
        i = 0 if current_rows == 0 else current_rows + 1
        annotation_row = AnnotationRow(key, value)
        self.annotation_rows.append(annotation_row)
        annotation_row.add_and_align_left(self.annotations_layout, row=i)

    def remove_annotation_row(self, annotation_row, i):
        annotation_row.remove(self.new_annotations_layout)
        del self.new_annotation_rows[i]


class TopButtonLayout(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()
        self.btn_add = QPushButton("Add sample")
        self.btn_edit = QPushButton("Edit sample")
        self.btn_remove = QPushButton("Remove sample")
        self.layout.addWidget(self.btn_add)
        self.layout.addWidget(self.btn_edit)
        self.layout.addWidget(self.btn_remove)
        self.layout.addStretch()

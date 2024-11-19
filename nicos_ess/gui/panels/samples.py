from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
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

        self.a_button = QPushButton("Click me")
        self.a_button.clicked.connect(self.button_clicked)
        self.a_label = QLabel("")

        layout = QHBoxLayout()
        layout.addWidget(self.a_button)
        layout.addWidget(self.a_label)

        self.setLayout(layout)

        print("working?")

    def button_clicked(self):
        self.a_label.setText("Hello!")

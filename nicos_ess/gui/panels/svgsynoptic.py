"""
A NICOS Panel for the SVG synoptic.
"""
import json
import os

from nicos.clients.gui.panels import Panel
from nicos.core import status
from nicos.guisupport.qt import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QFrame,
    QComboBox,
    QGraphicsItem,
    QStyleOptionGraphicsItem,
    QGraphicsTextItem,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QCursor,
    QFont,
    QFontMetrics,
    QPainterPath,
    QPolygonF,
    Qt,
    QRectF,
    QPointF,
    QLineF,
    pyqtSignal,
    QFileDialog,
    QMessageBox,
    QBuffer,
    QIODevice,
    QPixmap,
)

from nicos_ess.gui.panels.devices import DevicesPanel

from nicossynoptic.nicossynopticwidget import NicosSynopticWidget


class SynopticPanel(Panel):
    """
    That's the NICOS Panel
    """
    panelName = "Synoptic"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self.synoptic_widget = NicosSynopticWidget()

        # We need to give the absolute path to the HTML file
        # because our webview is setup to load assets from the
        # svgsynoptic library's path, not from the module's path.
        #path = os.path.dirname(__file__)
        path = "/Users/vincenthardion/projects/nicos-svgsynoptic/examples/nicos_example/"
        self.synoptic_widget.setConfig(os.path.join(path, "models.json"))
        self.synoptic_widget.setModel(os.path.join(path, "example.html"))

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

    def build_ui(self):
        self.main_layout.addWidget(self.synoptic_widget)

    def setup_connections(self, client):
        self.client.setup.connect(self.on_client_connected)
        self.synoptic_widget.initialise_client(client)

    def closeEvent(self, event):
        return QMainWindow.closeEvent(self, event)

    def on_client_connected(self):
        panels = self.mainwindow.panels
        for panel in panels:
            if isinstance(panel, DevicesPanel):
                self.synoptic_widget.device_panel = panel

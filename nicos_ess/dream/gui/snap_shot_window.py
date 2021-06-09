import numpy as np

from nicos.guisupport.qt import QHBoxLayout, QMainWindow, QPushButton, \
    QVBoxLayout, QWidget, pyqtSlot

from nicos_mlz.toftof.gui.resolutionpanel import PlotWidget as BasePlotWidget


class PlotWidget(BasePlotWidget):
    def setData(self, x1, y1, x2=None, y2=None):
        for curve, (x, y) in zip(self.plot._curves, ((x1, y1), (x2, y2))):
            if y is not None:
                curve.x = np.array(x)
                curve.y = np.array(y)

        self.plot.reset()
        self.plot.update()


class ComparisonPlot(PlotWidget):
    def __init__(self, parent):
        PlotWidget.__init__(self, "Comparison Plot", "x", "y", 2, parent=parent)
        self.plot._curves[0].legend = "Live"
        self.plot._curves[1].legend = "Background"


class SnapShotWindow(QMainWindow):
    """SnapShotWindow class"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Snapshot")

        if parent is not None:
            parent.registerWindow(self)

        self._central_widget = QWidget()
        self._test = QWidget()
        self.background_data = None

        self._plot = ComparisonPlot(parent=self._test)

        self.updateBackgroundButton = QPushButton("Update Background")
        self.updateBackgroundButton.clicked.connect(
            self.on_updateBackgroundButton_clicked
        )

        self.resetBackgroundButton = QPushButton("Reset Background")
        self.resetBackgroundButton.clicked.connect(
            self.on_resetBackgroundButton_clicked
        )

        self.setupUi()
        self.setCentralWidget(self._central_widget)
        self.setFixedSize(660, 500)
        self.show()

    def setupUi(self):
        layout = QVBoxLayout()

        layout.addWidget(self._test)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.updateBackgroundButton)
        buttons_layout.addWidget(self.resetBackgroundButton)

        layout.addLayout(buttons_layout)
        self._central_widget.setLayout(layout)

    def setData(self, labels, data):
        if self.background_data is None and not labels and data is None:
            return

        if self.background_data is None and data is not None:
            self.background_data = np.zeros_like(data)

        labels_data = None
        if labels:
            labels_data = labels["x"]
        elif data is not None:
            labels_data = np.arange(data.shape[0])

        labels_background = None
        if self.background_data is not None:
            labels_background = np.arange(self.background_data.shape[0])

        self._plot.setData(
            labels_data,
            data,
            x2=labels_background,  # Treat labels properly
            y2=self.background_data,
        )

    @pyqtSlot()
    def on_updateBackgroundButton_clicked(self):
        self.parent().update_background_data.emit()

    @pyqtSlot()
    def on_resetBackgroundButton_clicked(self):
        self.background_data = None

    def closeEvent(self, QCloseEvent):
        if self.parent() is not None:
            self.parent().unregisterWindow(self)
        super().closeEvent(QCloseEvent)

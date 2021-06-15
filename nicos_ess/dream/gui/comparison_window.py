from nicos.guisupport.livewidget import IntegralLiveWidget, LiveWidget
import numpy as np

from nicos.guisupport.plots import MaskedPlotCurve
from nicos.guisupport.qt import QHBoxLayout, QMainWindow, QPushButton, \
    QVBoxLayout, QWidget, pyqtSlot, QLabel, Qt, QSizePolicy

from nicos_mlz.toftof.gui.resolutionpanel import COLOR_GREEN, PlotWidget


class PlotWidget1D(PlotWidget):

    def setData(self, x1, y1, x2=None, y2=None, difference=False):
        for curve, (x, y) in zip(self.plot._curves[:-1], ((x1, y1), (x2, y2))):
            if y is not None:
                curve.x = np.array(x)
                curve.y = np.array(y)
        if difference:
            self.plot._curves[-1].x = np.array(x1)
            self.plot._curves[-1].y = np.array(y1) - np.array(y2)

        self.plot.reset()
        self.plot.update()

    def reset_background(self):
        for curve in self.plot._curves[1:]:
            curve.x = np.array([0])
            curve.y = np.array([0])


class ComparisonPlot1D(PlotWidget1D):
    def __init__(self, title, x_label, y_label, n_curves, parent=None):
        PlotWidget.__init__(self, title, x_label, y_label, n_curves, parent=parent)
        curve = MaskedPlotCurve(
            [0], [1], linewidth=2, legend='Difference', linecolor=COLOR_GREEN)
        self.plot.axes.addCurves(curve)
        self.plot._curves.append(curve)
        self.plot._curves[0].legend = "Live"
        self.plot._curves[1].legend = "Background"


class ComparisonPlot2D(QWidget):
    def __init__(self, title, parent=None):
        QWidget.__init__(self, parent)
        parent.setLayout(QVBoxLayout())
        self.plot = IntegralLiveWidget(self)
        titleLabel = QLabel(title)
        titleLabel.setAlignment(Qt.AlignCenter)
        titleLabel.setStyleSheet('QLabel {font-weight: 600}')
        parent.layout().insertWidget(0, titleLabel)
        self.plot.setSizePolicy(QSizePolicy.MinimumExpanding,
                                QSizePolicy.MinimumExpanding)
        parent.layout().insertWidget(1, self.plot)

    def setData(self, array):
        self.plot.setData([array])


class ComparisonWindow(QMainWindow):
    """SnapShotWindow class"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Snapshot")

        if parent is not None:
            parent.registerWindow(self)

        self.background_data = None
        self._central_widget = QWidget()

        self._test1 = QWidget()
        self._plot_1d = ComparisonPlot1D(
            "1D comparison plot", "x", "y", 2, parent=self._test1)
        self._test2 = QWidget()
        self._plot_2d = ComparisonPlot2D(
            "2D comparison plot ", parent=self._test2)

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
        self.show()

    def setupUi(self):
        plot_layout = QHBoxLayout()
        plot_layout.addWidget(self._test1)
        plot_layout.addWidget(self._test2)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.updateBackgroundButton)
        buttons_layout.addWidget(self.resetBackgroundButton)

        layout = QVBoxLayout()
        layout.addLayout(plot_layout)
        layout.addLayout(buttons_layout)
        self._central_widget.setLayout(layout)

    def setData(self, live_data_blob, background_data_blob=None):
        if not live_data_blob and not background_data_blob:
            return
        if background_data_blob:
            self.background_data = background_data_blob

        x1, y1, x2, y2 = None, None, None, None
        if live_data_blob:
            x1, y1 = self._extract_data(live_data_blob)

        if self.background_data:
            x2, y2 = self._extract_data(self.background_data)

        self._plot_1d.setData(x1, y1, x2, y2, difference=np.array_equal(x1, x2))
        self._plot_2d.setData(np.random.rand(512, 512))

    def _extract_data(self, blob):
        labels, data = blob
        return labels["x"] if labels else np.arange(data.shape[0]), data

    @pyqtSlot()
    def on_updateBackgroundButton_clicked(self):
        self.parent().update_background_data.emit()

    @pyqtSlot()
    def on_resetBackgroundButton_clicked(self):
        self.background_data = ({}, np.array([0]))
        self._plot.reset_background()

    def closeEvent(self, QCloseEvent):
        if self.parent() is not None:
            self.parent().unregisterWindow(self)
        super().closeEvent(QCloseEvent)

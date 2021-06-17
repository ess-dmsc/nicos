#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Ebad Kamil <ebad.kamil@ess.eu>
#
# *****************************************************************************

import numpy as np

from nicos.guisupport.livewidget import IntegralLiveWidget
from nicos.guisupport.plots import MaskedPlotCurve
from nicos.guisupport.qt import QHBoxLayout, QLabel, QMainWindow, \
    QPushButton, QSizePolicy, Qt, QVBoxLayout, QWidget, pyqtSlot

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
        else:
            self.plot._curves[-1].x = np.array([0])
            self.plot._curves[-1].y = np.array([0])
        self._plot_reset()

    def reset_background(self):
        for curve in self.plot._curves[1:]:
            curve.x = np.array([0])
            curve.y = np.array([0])
        self._plot_reset()

    def _plot_reset(self):
        self.plot.reset()
        self.plot.update()


class ComparisonPlot1D(PlotWidget1D):
    def __init__(self, title, x_label, y_label, n_curves, parent=None):
        PlotWidget.__init__(self, title, x_label, y_label, n_curves, parent=parent)
        curve = MaskedPlotCurve(
            [0], [1], linewidth=2, legend="Difference", linecolor=COLOR_GREEN
        )
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
        titleLabel.setStyleSheet("QLabel {font-weight: 600}")
        parent.layout().insertWidget(0, titleLabel)
        self.plot.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        parent.layout().insertWidget(1, self.plot)

    def setData(self, array, labels=None):
        self.plot.setData([array], labels=labels)


class ComparisonWindow(QMainWindow):
    """ComparisonWindow class"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Comparison")

        if parent is not None:
            parent.registerWindow(self)

        self.background_data_1d = None
        self.background_data_2d = None

        self._central_widget = QWidget()

        self._test1 = QWidget()
        self._plot_1d = ComparisonPlot1D(
            "1D comparison plot", "x", "y", 2, parent=self._test1
        )
        self._test2 = QWidget()
        self._plot_2d = ComparisonPlot2D("2D comparison plot ", parent=self._test2)

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

    def _update_1d_plot(self, data_blob=None):
        if not data_blob and not self.background_data_1d:
            return

        def _extract_data(blob):
            labels, data = blob
            return labels["x"] if labels else np.arange(data.shape[0]), data

        x1, y1, x2, y2 = None, None, None, None
        if data_blob:
            x1, y1 = _extract_data(data_blob)

        if self.background_data_1d:
            x2, y2 = _extract_data(self.background_data_1d)

        self._plot_1d.setData(x1, y1, x2, y2, difference=np.array_equal(x1, x2))

    def _update_2d_plot(self, data_blob=None):
        if not data_blob and not self.background_data_2d:
            return

        if not data_blob and self.background_data_2d:
            self._plot_2d.setData(
                self.background_data_2d[1], labels=self.background_data_2d[0]
            )

        if data_blob:
            if (
                self.background_data_2d
                and data_blob[1].shape == self.background_data_2d[1].shape
            ):
                self._plot_2d.setData(
                    data_blob[1] - self.background_data_2d[1], labels=data_blob[0]
                )
            else:
                self._plot_2d.setData(data_blob[1], labels=data_blob[0])

    def setData(self, blob):
        _, data = blob
        if data.ndim == 1:
            self._update_1d_plot(blob)
        elif data.ndim == 2:
            self._update_2d_plot(blob)

    def set_background_data(self, blob):
        _, data = blob
        if data.ndim == 1:
            self.background_data_1d = blob
        elif data.ndim == 2:
            self.background_data_2d = blob

    @pyqtSlot()
    def on_updateBackgroundButton_clicked(self):
        self.parent().update_background_data.emit()
        self._update_1d_plot()
        self._update_2d_plot()

    @pyqtSlot()
    def on_resetBackgroundButton_clicked(self):
        self.background_data_1d = None
        self.background_data_2d = None
        self._plot_1d.reset_background()

    def closeEvent(self, QCloseEvent):
        if self.parent() is not None:
            self.parent().unregisterWindow(self)
        super().closeEvent(QCloseEvent)

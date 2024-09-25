from datetime import datetime
import time

import pyqtgraph as pg
from pyqtgraph import mkPen

from nicos.guisupport.qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QSpinBox,
    QTimer,
    QToolTip,
)

import numpy as np


pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(datetime.fromtimestamp(value)) for value in values]


class HistogramDataViewer(QWidget):
    """
    A widget to display histogram data.
    It uses pyqtgraph to display a stepped colored histogram plot.
    """

    def __init__(self, parent=None):
        super(HistogramDataViewer, self).__init__(parent)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        hbox = QHBoxLayout()

        self.log_mode_checkbox = QCheckBox("Logarithmic mode")
        self.log_mode_checkbox.setChecked(False)
        self.log_mode_checkbox.stateChanged.connect(self.toggle_log_mode)
        # hbox.addWidget(self.log_mode_checkbox)  # Dont use yet

        self.mean_label = QLabel("Mean: 0 nm")
        self.mean_label.setStyleSheet("color: blue")
        hbox.addWidget(self.mean_label)

        self.stddev_label = QLabel("Std. Dev: 0 nm")
        self.stddev_label.setStyleSheet("color: red")
        hbox.addWidget(self.stddev_label)

        self.fwhm_label = QLabel("FWHM: 0 nm")
        hbox.addWidget(self.fwhm_label)

        layout.addLayout(hbox)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)

        self.plot_widget.setLabel("left", "Counts")
        self.plot_widget.setLabel("bottom", "Value")

        self.bar_graph_item = None
        self.mean_line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen("b", width=2))
        self.std_left_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen((255, 0, 0, 150), width=2)
        )
        self.std_right_line = pg.InfiniteLine(
            pos=0, angle=90, pen=pg.mkPen((255, 0, 0, 150), width=2)
        )

        self.plot_widget.addItem(self.mean_line)
        self.plot_widget.addItem(self.std_left_line)
        self.plot_widget.addItem(self.std_right_line)

        layout.addWidget(self.plot_widget)

        self.setLayout(layout)

    def set_data(self, x, y, brushes):
        if self.log_mode_checkbox.isChecked():
            y = np.clip(y, 1e-10, None)

        if self.bar_graph_item is not None:
            self.plot_widget.removeItem(self.bar_graph_item)

        self.bar_graph_item = pg.BarGraphItem(
            x=x, height=y, width=x[1] - x[0], brushes=brushes
        )

        self.plot_widget.addItem(self.bar_graph_item)

    def toggle_log_mode(self):
        if self.log_mode_checkbox.isChecked():
            self.plot_widget.setLogMode(y=True)
        else:
            self.plot_widget.setLogMode(y=False)

    def _calc_fwhm(self, bin_edges, hist):
        half_max = max(hist) / 2
        max_idx = np.argmax(hist)

        left_indices = np.where(hist[:max_idx] < half_max)[0]
        if len(left_indices) > 0:
            left_idx = left_indices[-1]
        else:
            left_idx = 0

        right_indices = np.where(hist[max_idx:] < half_max)[0]
        if len(right_indices) > 0:
            right_idx = right_indices[0] + max_idx
        else:
            right_idx = len(hist) - 1

        fwhm = bin_edges[right_idx] - bin_edges[left_idx]
        return fwhm, left_idx, right_idx

    def receive_data(self, x, y, mean, stddev, fwhm, left_bin_edge, right_bin_edge):
        self.mean = mean
        self.stddev = stddev
        self.fwhm = fwhm
        self.mean_label.setText(f"Mean: {self.mean:.2f} nm")
        self.stddev_label.setText(f"Std. Dev: {self.stddev:.2f} nm")
        self.fwhm_label.setText(f"FWHM: {self.fwhm:.2f} nm")
        self.mean_line.setValue(self.mean)
        self.std_left_line.setValue(self.mean - self.stddev)
        self.std_right_line.setValue(self.mean + self.stddev)

        brushes = []
        for bin_center in x:
            if left_bin_edge <= bin_center <= right_bin_edge:
                brushes.append((28, 166, 223, 200))
            else:
                brushes.append((140, 140, 140, 200))

        self.set_data(x=x, y=y, brushes=brushes)

    def clear(self):
        if self.bar_graph_item is not None:
            self.plot_widget.removeItem(self.bar_graph_item)
        self.mean_label.setText("Mean: 0 nm")
        self.stddev_label.setText("Std. Dev: 0 nm")
        self.fwhm_label.setText("FWHM: 0 nm")


class TrendViewer(QWidget):
    """
    A widget to display trends of data, such as the mean, std, and fwhm of a histogram.
    There is a left y-axis for the mean and a right y-axis for the std and fwhm.
    """

    def __init__(self, parent=None):
        super(TrendViewer, self).__init__(parent)

        self.init_ui()
        self.setup_connections()

        self.mean_data = []
        self.std_data = []
        self.fwhm_data = []
        self.timestamps = []

        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(int(1000 / 20))

    def init_ui(self):
        layout = QVBoxLayout()

        controls_layout = QHBoxLayout()
        self.time_window_label = QLabel("Time Window (s):")
        self.time_window_spinbox = QSpinBox()
        self.time_window_spinbox.setRange(1, 3600)
        self.time_window_spinbox.setValue(60)
        controls_layout.addWidget(self.time_window_label)
        controls_layout.addWidget(self.time_window_spinbox)

        self.pause_cb = QCheckBox("Pause Plot")
        self.pause_cb.setChecked(False)
        controls_layout.addWidget(self.pause_cb)

        layout.addLayout(controls_layout)

        self.left_view = pg.ViewBox()
        self.plot_widget = pg.PlotWidget(
            viewBox=self.left_view,
            axisItems={"bottom": TimeAxisItem(orientation="bottom")},
        )
        self.plot_widget.showGrid(x=True, y=True)
        legend = self.plot_widget.addLegend(
            brush=pg.mkBrush(color=(200, 200, 200, 100))
        )

        self.plot_widget.setLabel("bottom", "Time")

        self.plot_widget.setLabel("left", "Mean")

        self.plot_widget.showAxis("right")
        self.plot_widget.setLabel("right", "Std Dev / FWHM")
        self.plot_widget.getAxis("right").setPen(mkPen("r"))

        self.plot_widget.getAxis("right").setGrid(False)

        self.right_view = pg.ViewBox()
        self.right_view.setXLink(self.plot_widget)

        self.plot_widget.scene().addItem(self.right_view)
        self.plot_widget.getAxis("right").linkToView(self.right_view)
        self.right_view.setYRange(0, 100)

        self.mean_curve = self.plot_widget.plot(pen=mkPen("b", width=1), name="Mean")
        self.std_curve = pg.PlotCurveItem(
            pen=mkPen((255, 0, 120), width=1), name="Std Dev"
        )
        self.fwhm_curve = pg.PlotCurveItem(pen=mkPen("g", width=1), name="FWHM")

        self.right_view.addItem(self.std_curve)
        self.right_view.addItem(self.fwhm_curve)

        legend.addItem(self.std_curve, "Std Dev")
        legend.addItem(self.fwhm_curve, "FWHM")

        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self.time_window_spinbox.valueChanged.connect(self.update_plot)

    def setup_connections(self):
        self.plot_widget.getViewBox().sigRangeChanged.connect(
            self.on_view_range_changed
        )
        self.right_view.sigRangeChanged.connect(self.on_view_range_changed)
        self.plot_widget.getViewBox().sigResized.connect(self.update_views)
        self.move_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved
        )

    def mouseMoved(self, evt):
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mousePoint.x()
            y = mousePoint.y()

            if self.timestamps:
                idx = np.searchsorted(self.timestamps, x)
                if idx > 0 and (
                    idx == len(self.timestamps)
                    or abs(x - self.timestamps[idx - 1]) < abs(x - self.timestamps[idx])
                ):
                    idx -= 1

                timestamp = self.timestamps[idx]
                mean_value = self.mean_data[idx]
                std_value = self.std_data[idx]
                fwhm_value = self.fwhm_data[idx]

                time_string = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                tooltip_text = f"Time: {time_string}\n"
                tooltip_text += f"Mean: {mean_value:.2f}\n"
                tooltip_text += f"Std Dev: {std_value:.2f}\n"
                tooltip_text += f"FWHM: {fwhm_value:.2f}"

                local_point = pos
                global_point = self.plot_widget.mapToGlobal(local_point.toPoint())

                QToolTip.showText(global_point, tooltip_text)
                self.vLine.setPos(timestamp)
                self.hLine.setPos(y)
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()

    def update_views(self):
        """Update the right view to match the main plot"""
        self.right_view.setGeometry(self.plot_widget.getViewBox().sceneBoundingRect())
        self.right_view.linkedViewChanged(
            self.plot_widget.getViewBox(), self.right_view.XAxis
        )

    def update_plot(self):
        """Update the plot based on the current time window and in-memory data"""
        if self.pause_cb.isChecked():
            return

        current_time = time.time()
        time_window = self.time_window_spinbox.value()
        cutoff_time = current_time - time_window

        idx_start = 0
        while (
            idx_start < len(self.timestamps)
            and self.timestamps[idx_start] < cutoff_time
        ):
            idx_start += 1

        timestamps = self.timestamps[idx_start:]
        mean_data = self.mean_data[idx_start:]
        std_data = self.std_data[idx_start:]
        fwhm_data = self.fwhm_data[idx_start:]

        self.mean_curve.setData(timestamps, mean_data)
        self.std_curve.setData(timestamps, std_data)
        self.fwhm_curve.setData(timestamps, fwhm_data)

        self.plot_widget.setXRange(cutoff_time, current_time)

        self.align_right_axis()

    def on_view_range_changed(self):
        """Slot to handle the view range changing"""
        self.align_right_axis()

    def align_right_axis(self):
        """Align the ticks of the right y-axis with those of the left y-axis"""
        left_axis = self.plot_widget.getAxis("left")

        left_y_range = self.plot_widget.getViewBox().viewRange()[1]
        left_y_min, left_y_max = left_y_range

        axis_size = left_axis.geometry().height()

        left_ticks = left_axis.tickValues(left_y_min, left_y_max, axis_size)

        major_ticks = []
        for ticks in left_ticks:
            major_ticks.extend(ticks[1])
        left_tick_positions = [tick for tick in major_ticks]

        right_y_range = self.right_view.viewRange()[1]
        right_y_min, right_y_max = right_y_range

        right_tick_positions = []
        for y_left in left_tick_positions:
            y_ratio = (y_left - left_y_min) / (left_y_max - left_y_min)
            y_right = right_y_min + y_ratio * (right_y_max - right_y_min)
            right_tick_positions.append(y_right)

        right_tick_labels = ["{:.2f}".format(y) for y in right_tick_positions]

        right_axis = self.plot_widget.getAxis("right")
        right_ticks = [
            (pos, label) for pos, label in zip(right_tick_positions, right_tick_labels)
        ]
        right_axis.setTicks([right_ticks])

    def receive_data(self, timestamp, mean, std, fwhm):
        self.timestamps = timestamp
        self.mean_data = mean
        self.std_data = std
        self.fwhm_data = fwhm

    def clear(self):
        self.timestamps = []
        self.mean_data = []
        self.std_data = []
        self.fwhm_data = []
        self.mean_curve.setData([], [])
        self.std_curve.setData([], [])
        self.fwhm_curve.setData([], [])


if __name__ == "__main__":
    import sys
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication(sys.argv)
    viewer = TrendViewer()
    viewer.show()
    sys.exit(app.exec_())

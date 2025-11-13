from datetime import datetime

import numpy as np
import pyqtgraph as pg
from pyqtgraph import mkBrush, mkPen

from nicos.guisupport.qt import (
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSignal,
    pyqtSlot,
)
from nicos_ess.gui.widgets.pyqtgraph.roi import CROSS_COLOR, CROSS_HOOVER_COLOR

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)


HISTOGRAM_COLOR = (28, 166, 223, 200)


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(datetime.fromtimestamp(value)) for value in values]


class LineView(QWidget):
    clicked = pyqtSignal(str)
    data_changed = pyqtSignal(dict)

    def __init__(self, parent=None, name="", preview_mode=False, *args):
        super(LineView, self).__init__(parent, *args)

        self.name = name
        self.preview_mode = preview_mode
        self.data = []
        self._time_axis_enabled = False

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        hbox = QHBoxLayout()

        self.mode_checkbox = QCheckBox("Plot latest curve")
        self.mode_checkbox.setChecked(True)
        self.mode_checkbox.stateChanged.connect(self.toggle_mode)
        hbox.addWidget(self.mode_checkbox)

        self.clear_button = QPushButton("Clear curves")
        self.clear_button.clicked.connect(self.clear_data)
        hbox.addWidget(self.clear_button)

        self.log_checkbox = QCheckBox("Logarithmic mode")
        self.log_checkbox.stateChanged.connect(self.toggle_log_mode)
        hbox.addWidget(self.log_checkbox)

        if not self.preview_mode:
            layout.addLayout(hbox)

        splitter_widget = QSplitter(Qt.Orientation.Vertical)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.view = self.plot_widget.getViewBox()
        splitter_widget.addWidget(self.plot_widget)

        self.legend = self.plot_widget.addLegend(
            pen=mkPen("k", width=0.5),
            brush=mkBrush((0, 0, 0, 10)),
        )
        self.legend.hide()

        self.init_vertical_line()

        self.plot_widget_sliced = pg.PlotWidget(
            axisItems={"bottom": TimeAxisItem(orientation="bottom")}
        )
        self.plot_widget_sliced.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget_sliced.hide()
        self.plot_sliced = self.plot_widget_sliced.plot(pen=mkPen("k", width=1))
        splitter_widget.addWidget(self.plot_widget_sliced)

        layout.addWidget(splitter_widget)

        self.setLayout(layout)

    def init_vertical_line(self):
        self.vertical_line = pg.InfiniteLine(
            pos=10,
            angle=90,
            movable=True,
            pen=mkPen(CROSS_COLOR, width=3),
            hoverPen=mkPen(CROSS_HOOVER_COLOR, width=3),
        )
        self.view.addItem(self.vertical_line)
        self.vertical_line.hide()
        self.vertical_line.sigPositionChanged.connect(self.vertical_line_changed)

    @pyqtSlot()
    def vertical_line_changed(self):
        if not self.vertical_line.isVisible():
            return
        v_val = int(self.vertical_line.value())
        x_vals = []
        y_vals = []
        for data in self.data:
            x_data, y_data = data["curve"]
            if data.get("is_histogram", False):
                continue
            if v_val < x_data[0] or v_val > x_data[-1]:
                continue
            idx = np.searchsorted(x_data, v_val)
            y_vals.append(y_data[idx])
            x_vals.append(data["timestamp"].timestamp())
        self.plot_sliced.setData(y=y_vals, x=x_vals)

    def set_axis_format(
        self,
        *,
        title=None,
        x_label=None,
        y_label=None,
        y_units=None,
        x_is_time=False,
    ):
        # Install a custom time axis ONCE if we are plotting timestamps
        if x_is_time and not self._time_axis_enabled:
            bottom = TimeAxisItem(orientation="bottom")
            bottom.enableAutoSIPrefix(False)  # avoid 'Gs' etc.
            self.plot_widget.setAxisItems({"bottom": bottom})
            self._time_axis_enabled = True
        elif not x_is_time and self._time_axis_enabled:
            # Optional: restore default axis if needed in your app
            self.plot_widget.setAxisItems({"bottom": pg.AxisItem(orientation="bottom")})
            self._time_axis_enabled = False

        # For time axes do NOT pass 'units' (prevents '(Gs)' in the label)
        if x_is_time:
            self.plot_widget.setLabel("bottom", x_label or "Time")
        else:
            self.plot_widget.setLabel("bottom", x_label or "X")

        self.plot_widget.setLabel("left", y_label or "Counts", units=y_units or None)
        if title:
            self.plot_widget.setTitle(title)

    def toggle_mode(self, state):
        if state == Qt.Checked:
            self.plot_latest_curve()
            self.legend.hide()
            self.vertical_line.hide()
            self.plot_widget_sliced.hide()
        else:
            self.plot_all_curves()
            if not self.preview_mode:
                self.legend.show()
                self.vertical_line.show()
                self.plot_widget_sliced.show()
                self.vertical_line_changed()

    def toggle_log_mode(self, state):
        log_mode = state == Qt.Checked
        self.plot_widget.setLogMode(y=log_mode)
        self.plot_widget_sliced.setLogMode(y=log_mode)

    def clear_data(self):
        self.data = []
        self.plot_widget.clear()

    def generate_contrasting_color(self):
        color = pg.intColor(np.random.randint(0, 255), alpha=255)
        while color.red() + color.green() + color.blue() < 300:
            color = pg.intColor(np.random.randint(0, 255), alpha=255)
        return color

    def set_data(self, arrays, labels):
        """
        If x_data has length N+1 and y_data has length N,
        we interpret them as histogram bin edges and counts.
        Otherwise, it's a normal line plot.
        """
        y_data = arrays[0]
        x_data = labels["x"]
        if self.data and np.array_equal(y_data, self.data[-1]["curve"][1]):
            return

        color = self.generate_contrasting_color()
        is_histogram = False
        if len(x_data) == len(y_data) + 1:
            is_histogram = True

        new_data = {
            "curve": (x_data, y_data),
            "timestamp": datetime.now(),
            "color": color,
            "is_histogram": is_histogram,  # Store the flag
        }
        self.data.append(new_data)

        self.move_vertical_line_within_bounds(
            lower_bound=x_data[0] + 1, upper_bound=x_data[-1]
        )
        self.data_changed.emit(self.save_state())
        self.mode_changed()

    def move_vertical_line_within_bounds(self, lower_bound, upper_bound):
        v_val = int(self.vertical_line.value())
        if v_val < lower_bound:
            self.vertical_line.setValue(lower_bound)
        elif v_val > upper_bound:
            self.vertical_line.setValue(upper_bound)

    def mode_changed(self):
        if self.mode_checkbox.isChecked():
            self.plot_latest_curve()
        else:
            self.plot_all_curves()

    def plot_latest_curve(self):
        self.plot_widget.clear()
        if not self.data:
            return
        latest_data = self.data[-1]
        x_data, y_data = latest_data["curve"]
        is_hist = latest_data["is_histogram"]

        if is_hist:
            x0 = x_data[0:-1]
            x1 = x_data[1:]
            bar_graph = pg.BarGraphItem(
                x0=x0,
                x1=x1,
                height=y_data,
                brush=HISTOGRAM_COLOR,
                pen=mkPen((0, 0, 0, 0)),
            )
            self.plot_widget.addItem(bar_graph)
        else:
            self.plot_widget.plot(
                x=x_data,
                y=y_data,
                pen=mkPen("k"),
                name=latest_data["timestamp"].strftime("%Y/%m/%d, %H:%M:%S"),
            )

    def plot_all_curves(self):
        self.plot_widget.clear()
        for data in self.data:
            x_data, y_data = data["curve"]
            color = data["color"]
            is_hist = data["is_histogram"]

            if is_hist:
                width = x_data[1] - x_data[0]
                bar_graph = pg.BarGraphItem(
                    x=x_data[:-1],
                    height=y_data,
                    width=width,
                    brush=color,
                )
                self.plot_widget.addItem(bar_graph)
                # Optional: no legend entry by default for BarGraphItem
                # If you want a "fake" legend entry, you can create an empty
                # PlotDataItem with the same color. E.g.:
                #   label_name = data["timestamp"].strftime("%Y/%m/%d, %H:%M:%S")
                #   self.legend.addItem(bar_graph, label_name)
            else:
                self.plot_widget.plot(
                    x=x_data,
                    y=y_data,
                    pen=color,
                    name=data["timestamp"].strftime("%Y/%m/%d, %H:%M:%S"),
                )
        self.vertical_line_changed()

    def save_state(self):
        return {
            "data": self.data,
            "log_mode": self.log_checkbox.isChecked(),
            "plot_latest": self.mode_checkbox.isChecked(),
            "vertical_line_val": self.vertical_line.value(),
        }

    def restore_state(self, state):
        self.data = state["data"]
        self.log_checkbox.setChecked(state["log_mode"])
        self.mode_checkbox.setChecked(state["plot_latest"])
        self.vertical_line.setValue(state["vertical_line_val"])

        if state["plot_latest"]:
            self.plot_latest_curve()
        else:
            self.plot_all_curves()

    def mousePressEvent(self, ev):
        self.clicked.emit(self.name)

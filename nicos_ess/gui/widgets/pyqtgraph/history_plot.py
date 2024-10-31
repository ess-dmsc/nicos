import time
from datetime import datetime

import numpy as np

import pyqtgraph as pg
from pyqtgraph import mkPen, mkBrush
from qtgr import QWidget

from nicos.guisupport.qt import (
    QVBoxLayout,
    pyqtSignal,
    QHBoxLayout,
    QColor,
    QSplitter,
    Qt,
    pyqtSlot,
    QFrame,
)
from nicos_ess.gui.widgets.pyqtgraph.derived_history_widgets import (
    HistogramPlot,
    XYPlot,
)

from nicos_ess.gui.widgets.pyqtgraph.utils.utils import (
    TimeAxisItem,
    ClickableLabel,
    clear_layout,
    PlotTypes,
)

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)


class HistoryWidget(QWidget):
    boundsChanged = pyqtSignal(float, float)
    derivedWidgetRemoved = pyqtSignal(str)

    def __init__(self, parent=None):
        super(HistoryWidget, self).__init__(parent)

        self.left_view = pg.ViewBox()
        self.plotwidget_time = pg.PlotWidget(
            viewBox=self.left_view,
            axisItems={"bottom": TimeAxisItem(orientation="bottom")},
        )
        self.plotwidget_time.showGrid(x=True, y=True, alpha=0.2)
        self.left_bound_line = pg.InfiniteLine(
            angle=90,
            movable=True,
            pen=mkPen("k", width=2),
            bounds=(0, time.time() + 60),
        )
        self.left_bound_line.hide()
        self.left_bound_line_locked = True
        self.right_bound_line = pg.InfiniteLine(
            angle=90,
            movable=True,
            pen=mkPen("k", width=2),
            bounds=(0, time.time() + 60),
        )
        self.right_bound_line.hide()
        self.right_bound_line_locked = True

        self.plotwidget_time.addItem(self.left_bound_line)
        self.plotwidget_time.addItem(self.right_bound_line)

        self.plotwidget_time.getAxis("right").setPen(mkPen("r"))
        self.plotwidget_time.getAxis("right").setGrid(False)

        self.right_view = pg.ViewBox()
        self.right_view.setXLink(self.plotwidget_time)

        self.plotwidget_time.scene().addItem(self.right_view)
        self.plotwidget_time.getAxis("right").linkToView(self.right_view)
        self.right_view.setYRange(0, 100)
        self.right_view.autoRangeEnabled()

        self.info_label = pg.TextItem("", anchor=(0, 0), color=(0, 0, 0))
        self.info_label.setFlag(
            self.info_label.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self.info_label.setParentItem(self.plotwidget_time.plotItem)

        menu = self.plotwidget_time.getPlotItem().getViewBox().menu
        menu.addSeparator()
        menu.addAction("Show/Hide Boundary Lines", self.toggle_infinite_lines)
        menu.addAction("Autoscale Boundary Lines", self.autoscale_boundary_lines)

        self._ts_plots = {}
        self._labels = {}
        self._lines = {}
        self._hover_markers = {}
        self._ts_plot_states = {}
        self._derived_plot_widgets = {}

        self._min_ts = time.time() - 60 * 60 * 24
        self._max_ts = time.time() + 60 * 60 * 24

        self.init_ui()

        self.setup_connections()

    def init_ui(self):
        main_layout = QHBoxLayout()
        self.legend_layout = QVBoxLayout()

        self.legend_widget = QWidget()
        self.legend_widget.setLayout(self.legend_layout)

        self.time_plot_frame = QFrame()
        self.time_plot_layout = QHBoxLayout()
        self.time_plot_frame.setLayout(self.time_plot_layout)
        self.time_plot_layout.addWidget(self.plotwidget_time)
        self.time_plot_layout.addWidget(self.legend_widget)

        self.derived_plots_frame = QFrame()
        self.derived_plots_layout = QHBoxLayout()
        self.derived_plots_frame.setLayout(self.derived_plots_layout)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.time_plot_frame)
        self.splitter.addWidget(self.derived_plots_frame)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.splitter.setSizes([self.height() // 2, self.height() // 2])

        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

    def setup_connections(self):
        self.plotwidget_time.getViewBox().sigRangeChanged.connect(
            self.on_view_range_changed
        )
        self.right_view.sigRangeChanged.connect(self.on_view_range_changed)
        self.plotwidget_time.getViewBox().sigResized.connect(self.update_views)
        self.left_bound_line.sigPositionChanged.connect(self.on_left_bound_line_moved)
        self.right_bound_line.sigPositionChanged.connect(self.on_right_bound_line_moved)
        self.left_bound_line.sigPositionChangeFinished.connect(
            self.on_line_finished_moving
        )
        self.right_bound_line.sigPositionChangeFinished.connect(
            self.on_line_finished_moving
        )
        self.plotwidget_time.scene().sigMouseMoved.connect(self.mouse_moved)

    def toggle_infinite_lines(self):
        self.left_bound_line.setVisible(not self.left_bound_line.isVisible())
        self.right_bound_line.setVisible(not self.right_bound_line.isVisible())

    def autoscale_boundary_lines(self):
        self.left_bound_line.setValue(self._min_ts)
        self.right_bound_line.setValue(self._max_ts)
        self.left_bound_line_locked = True
        self.right_bound_line_locked = True

    def _reset_hover_markers(self):
        for hover_marker in self._hover_markers.values():
            hover_marker.setVisible(False)

    def _update_hover_marker(self, plot, hover_marker, index, value, which_axis):
        if which_axis == "right_view":
            right_view_point = self.right_view.mapFromView(
                pg.Point(plot.xData[index], value)
            )
            left_view_point = self.left_view.mapToView(right_view_point)
            hover_marker.setData([plot.xData[index]], [left_view_point.y()])
        else:
            hover_marker.setData([plot.xData[index]], [value])
        hover_marker.setVisible(True)

    @pyqtSlot(object)
    def mouse_moved(self, pos):
        if not self.plotwidget_time.sceneBoundingRect().contains(pos):
            self.info_label.setText("")
            self._reset_hover_markers()
            return

        self.info_label.setPos(
            self.plotwidget_time.getViewBox().sceneBoundingRect().topLeft()
        )

        mouse_point = self.plotwidget_time.getViewBox().mapSceneToView(pos)
        timestamp = mouse_point.x()
        time_str = (
            f"Time: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        info_str = ""

        for key, plot in self._ts_plots.items():
            if (
                not plot.isVisible()
                or timestamp < plot.xData[0]
                or timestamp > plot.xData[-1]
            ):
                continue

            which_axis = self._ts_plot_states[key]
            hover_marker = self._hover_markers[key]

            if which_axis == "hidden":
                hover_marker.setVisible(False)
                continue

            index = np.argmin(np.abs(plot.xData - timestamp))
            if 0 <= index < len(plot.xData):
                value = plot.yData[index]
                info_str += f", {key}: {value}"
                self._update_hover_marker(plot, hover_marker, index, value, which_axis)
            else:
                hover_marker.setVisible(False)

        if info_str:
            self.info_label.setText(time_str + info_str)
        else:
            self.info_label.setText("")
            self._reset_hover_markers()

    @pyqtSlot()
    def on_left_bound_line_moved(self):
        pos = self.left_bound_line.value()
        bounds = self.left_bound_line.bounds()
        right_pos = self.right_bound_line.value()
        if pos > right_pos:
            self.left_bound_line.setValue(right_pos)

        if pos > bounds[0]:
            self.left_bound_line_locked = False
        else:
            self.left_bound_line.setValue(bounds[0])
            self.left_bound_line_locked = True
        self.boundsChanged.emit(
            self.left_bound_line.value(), self.right_bound_line.value()
        )

    @pyqtSlot()
    def on_right_bound_line_moved(self):
        pos = self.right_bound_line.value()
        bounds = self.right_bound_line.bounds()
        left_pos = self.left_bound_line.value()
        if pos < left_pos:
            self.right_bound_line.setValue(left_pos)

        if pos < bounds[1]:
            self.right_bound_line_locked = False
        else:
            self.right_bound_line.setValue(bounds[1])
            self.right_bound_line_locked = True
        self.boundsChanged.emit(
            self.left_bound_line.value(), self.right_bound_line.value()
        )

    @pyqtSlot()
    def on_line_finished_moving(self):
        for widget in self._derived_plot_widgets.values():
            widget.set_plots(self._lines)
            if self.derived_plots_frame.isHidden():
                self.derived_plots_frame.show()

    def set_autoscale(self):
        self.left_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        self.right_view.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

        for widget in self._derived_plot_widgets.values():
            widget.set_autoscale()

    def _add_plot_line(self, key, timestamps, values, color, units=""):
        plot_item = pg.PlotCurveItem(
            timestamps, values, name=key, pen=mkPen(color), pen_width=2
        )
        self._ts_plots[key] = plot_item
        self._ts_plot_states[key] = "left_view"
        self._hover_markers[key] = pg.ScatterPlotItem(
            [], [], pen=mkPen("k"), brush=mkBrush(color), size=10
        )
        self._hover_markers[key].setVisible(False)
        self._hover_markers[key].setZValue(10)
        self.plotwidget_time.addItem(self._hover_markers[key], ignoreBounds=True)
        self.left_view.addItem(plot_item)

        label_str = f"{key} ({units})" if units else key

        label_widget = ClickableLabel(label_str)
        qcolor = QColor(*color)
        label_widget.setStyleSheet(f"color: {qcolor.name()}; font-size: 18px;")
        label_widget.clicked.connect(lambda k=key: self.toggle_plot_visibility(k))
        self._labels[key] = label_widget
        self.legend_layout.addWidget(label_widget)

    def set_plots(self, lines):
        self._lines = lines
        self.plotwidget_time.clear()
        self._ts_plots.clear()
        for label in self._labels.values():
            label.deleteLater()
        self._labels.clear()
        clear_layout(self.legend_layout)

        self.plotwidget_time.addItem(self.left_bound_line)
        self.plotwidget_time.addItem(self.right_bound_line)

        self.info_label.setParentItem(self.plotwidget_time.plotItem)

        curr_min_ts = time.time() + 60
        curr_max_ts = 0

        self.left_bound_line.setValue(self._min_ts)
        self.right_bound_line.setValue(self._max_ts)

        for key, line in lines.items():
            timestamps, values = line.get_data()
            units = line.get_units()
            color = line.get_color()
            self._add_plot_line(key, timestamps, values, color, units)
            curr_min_ts = (
                min(curr_min_ts, np.min(timestamps))
                if len(timestamps) > 0
                else curr_min_ts
            )
            curr_max_ts = (
                max(curr_max_ts, np.max(timestamps))
                if len(timestamps) > 0
                else curr_max_ts
            )

        self.legend_layout.addStretch()
        self._update_infinite_lines(curr_min_ts, curr_max_ts)
        self.align_right_axis()

        if not self._derived_plot_widgets:
            self.derived_plots_frame.hide()

        for widget in self._derived_plot_widgets.values():
            widget.set_plots(lines)
            if self.derived_plots_frame.isHidden():
                self.derived_plots_frame.show()

    def update_plot(self, key, lines):
        line = lines[key]
        timestamps, values = line.get_data()
        self._ts_plots[key].setData(timestamps, values)
        self._update_infinite_lines(np.min(timestamps), np.max(timestamps))
        self.align_right_axis()

        for widget in self._derived_plot_widgets.values():
            widget.update_plot(key, lines)
            if self.derived_plots_frame.isHidden():
                self.derived_plots_frame.show()

    def _update_infinite_lines(self, min_ts, max_ts):
        self.left_bound_line.setBounds((min_ts, max_ts))
        self.right_bound_line.setBounds((min_ts, max_ts))

        if self.left_bound_line_locked:
            self.left_bound_line.setValue(min_ts)
        if self.right_bound_line_locked:
            self.right_bound_line.setValue(max_ts)

    def _set_label_hidden(self, label):
        label.setStyleSheet(
            "color: grey; text-decoration: "
            "line-through; font-size: 18px; border: 2px transparent;"
        )

    def _set_label_left_view(self, label, color):
        qcolor = QColor(*color)
        label.setStyleSheet(
            f"color: {qcolor.name()}; font-size: 18px; border: 2px transparent;"
        )

    def _set_label_right_view(self, label, color):
        qcolor = QColor(*color)
        label.setStyleSheet(
            f"color: {qcolor.name()}; font-size: 18px; border: 2px solid red;"
        )

    def toggle_plot_visibility(self, key):
        plot = self._ts_plots[key]
        label = self._labels[key]
        plot_state = self._ts_plot_states[key]
        color = self._lines[key].get_color()

        if plot_state == "left_view":
            self.left_view.removeItem(plot)
            self.right_view.addItem(plot)
            self._set_label_right_view(label, color)
            self._ts_plot_states[key] = "right_view"
        elif plot_state == "right_view":
            self.right_view.removeItem(plot)
            self._set_label_hidden(label)
            self._ts_plot_states[key] = "hidden"
        elif plot_state == "hidden":
            self.left_view.addItem(plot)
            self._set_label_left_view(label, color)
            self._ts_plot_states[key] = "left_view"

        num_right_views = sum(
            [1 for state in self._ts_plot_states.values() if state == "right_view"]
        )
        if num_right_views == 0:
            self.plotwidget_time.hideAxis("right")
        else:
            self.plotwidget_time.showAxis("right")

        self.left_view.autoRange()
        self.right_view.autoRange()
        self.plotwidget_time.autoRange()

    def clear(self):
        self.plotwidget_time.clear()
        self.left_view.clear()
        self.right_view.clear()
        for label in self._labels.values():
            label.deleteLater()
        self._labels.clear()
        self._lines.clear()
        self._ts_plot_states.clear()
        for widget in self._derived_plot_widgets.values():
            widget.clear()
        self.plotwidget_time.hideAxis("right")
        self.left_bound_line.hide()
        self.right_bound_line.hide()

    def on_view_range_changed(self):
        self.align_right_axis()

    def _calculate_right_axis_ticks(self, left_ticks, left_range, right_range):
        left_min, left_max = left_range
        right_min, right_max = right_range
        scale = (right_max - right_min) / (left_max - left_min)

        right_ticks = [(right_min + (tick - left_min) * scale) for tick in left_ticks]
        right_labels = [
            "{:.8f}".format(tick).rstrip("0").rstrip(".") for tick in right_ticks
        ]
        return list(zip(right_ticks, right_labels))

    def align_right_axis(self):
        if self.plotwidget_time.geometry().height() == 0:
            return

        left_axis = self.plotwidget_time.getAxis("left")
        left_y_min, left_y_max = self.plotwidget_time.getViewBox().viewRange()[1]
        axis_size = left_axis.geometry().height()

        left_ticks = [
            tick
            for sublist in left_axis.tickValues(left_y_min, left_y_max, axis_size)
            for tick in sublist[1]
        ]

        right_y_min, right_y_max = self.right_view.viewRange()[1]
        right_ticks = self._calculate_right_axis_ticks(
            left_ticks, (left_y_min, left_y_max), (right_y_min, right_y_max)
        )

        right_axis = self.plotwidget_time.getAxis("right")
        right_axis.setTicks([right_ticks])

    def update_views(self):
        self.right_view.setGeometry(
            self.plotwidget_time.getViewBox().sceneBoundingRect()
        )
        self.right_view.linkedViewChanged(
            self.plotwidget_time.getViewBox(), self.right_view.XAxis
        )

    def create_xy_plot(self, lines_to_correlate):
        self.create_derived_plot(PlotTypes.XY, lines_to_correlate)

    def create_histogram_plot(self, lines_to_histogram):
        self.create_derived_plot(PlotTypes.HISTOGRAM, lines_to_histogram)

    def create_derived_plot(self, plot_type, lines_to_use):
        plot_name = plot_type.value
        if plot_name in self._derived_plot_widgets:
            old_widget = self._derived_plot_widgets[plot_name]
            old_widget.deleteLater()
            self._derived_plot_widgets.pop(plot_name)

        widget = self._create_plot_widget(plot_type)
        widget.set_lines_to_use(lines_to_use)
        self.boundsChanged.connect(widget.on_bounds_changed)
        self.derived_plots_layout.addWidget(widget)
        self._derived_plot_widgets[plot_name] = widget

        self.left_bound_line.show()
        self.right_bound_line.show()
        self.boundsChanged.emit(
            self.left_bound_line.value(), self.right_bound_line.value()
        )
        widget.set_plots(self._lines)
        widget.widgetRemoved.connect(self.on_derived_widget_removed)
        if self.derived_plots_frame.isHidden():
            self.derived_plots_frame.show()

    def _create_plot_widget(self, plot_type):
        if plot_type == PlotTypes.XY:
            return XYPlot()
        elif plot_type == PlotTypes.HISTOGRAM:
            return HistogramPlot()
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

    @pyqtSlot(str)
    def on_derived_widget_removed(self, widget_name):
        if widget_name in self._derived_plot_widgets:
            try:
                self.boundsChanged.disconnect(
                    self._derived_plot_widgets[widget_name].on_bounds_changed
                )
            except Exception as e:
                print(f"Failed to disconnect boundsChanged signal: {e}")
            self._derived_plot_widgets[widget_name].clear()
            self._derived_plot_widgets[widget_name].hide()
            self._derived_plot_widgets[widget_name] = None
            self._derived_plot_widgets.pop(widget_name)
            self.derivedWidgetRemoved.emit(widget_name)

        if not self._derived_plot_widgets:
            self.left_bound_line.hide()
            self.right_bound_line.hide()
            self.derived_plots_frame.hide()

    def remove_all_derived_widgets(self):
        for widget in list(self._derived_plot_widgets.values()):
            self.on_derived_widget_removed(widget)
        self._derived_plot_widgets.clear()

    def reset_widget(self):
        self.clear()
        self.left_bound_line.setValue(0)
        self.right_bound_line.setValue(1)
        self.left_bound_line_locked = True
        self.right_bound_line_locked = True
        self.left_bound_line.hide()
        self.right_bound_line.hide()
        self.plotwidget_time.hideAxis("right")
        self.derived_plots_frame.hide()

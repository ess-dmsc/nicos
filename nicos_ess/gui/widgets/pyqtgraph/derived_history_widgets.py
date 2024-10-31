import itertools

import numpy as np

import pyqtgraph as pg
from qtgr import QWidget

from nicos.guisupport.qt import (
    QVBoxLayout,
    pyqtSignal,
    pyqtSlot,
)
from nicos_ess.gui.widgets.pyqtgraph.utils.fitter import Fitter1D, FitType
from nicos_ess.gui.widgets.pyqtgraph.utils.utils import (
    COLORS,
    PlotTypes,
    HISTOGRAM_COLORS,
    interpolate_to_detector_timestamps,
)

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)


class DerivedWidgetBase(QWidget):
    """
    Base class for derived plot widgets.
    """

    widgetRemoved = pyqtSignal(str)

    def __init__(self, parent=None):
        super(DerivedWidgetBase, self).__init__(parent)

    @pyqtSlot(float, float)
    def on_bounds_changed(self, left_bound, right_bound):
        raise NotImplementedError

    def set_autoscale(self):
        raise NotImplementedError

    def set_plots(self, lines):
        raise NotImplementedError

    def update_plot(self, key, lines):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class HistogramPlot(DerivedWidgetBase):
    def __init__(self, parent=None):
        super(HistogramPlot, self).__init__(parent)

        self.plotwidget = pg.PlotWidget()
        self.plotwidget.showGrid(x=True, y=True, alpha=0.2)

        self.bar_graph_item = None

        menu = self.plotwidget.getPlotItem().getViewBox().menu
        menu.addSeparator()
        menu.addAction("Remove Plot", self._remove_plot)

        self._plots = {}
        self._lines = {}
        self._left_bound = 0
        self._right_bound = 0

        self._key_to_histogram = None

        self._bar_brush = pg.mkBrush(HISTOGRAM_COLORS[0])

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.plotwidget)
        self.setLayout(main_layout)

    def _remove_plot(self):
        self._plots = {}
        self._lines = {}
        self.clear()
        self.widgetRemoved.emit(PlotTypes.HISTOGRAM.value)

    @pyqtSlot(float, float)
    def on_bounds_changed(self, left_bound, right_bound):
        self._left_bound = left_bound
        self._right_bound = right_bound

    def set_lines_to_use(self, keys):
        self._key_to_histogram = keys[0]

    def set_autoscale(self):
        self.plotwidget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def set_plots(self, lines):
        self.plotwidget.clear()
        self._plots.clear()
        self._lines = lines

        if not (self._key_to_histogram and lines):
            return

        line = lines.get(self._key_to_histogram)
        if not line:
            return

        timestamps, values = line.get_data()

        if len(values) < 3:
            return

        idx_1, idx_2 = np.searchsorted(
            timestamps, [self._left_bound, self._right_bound]
        )
        if idx_1 >= idx_2:
            return

        values = values[idx_1:idx_2]
        x, y = self._calc_stats(values)

        if len(x) < 2:
            return

        if self.bar_graph_item:
            self.plotwidget.removeItem(self.bar_graph_item)

        self.bar_graph_item = pg.BarGraphItem(
            x=x, height=y, width=x[1] - x[0], brush=self._bar_brush
        )
        self.plotwidget.addItem(self.bar_graph_item)

        bottom_label_str = (
            f"{line.get_name()} ({line.get_units()})"
            if line.get_units()
            else line.get_name()
        )

        self.plotwidget.setTitle(title=f"Histogram of {line.get_name()}")
        self.plotwidget.setLabel("bottom", bottom_label_str)
        self.plotwidget.setLabel("left", "Counts")

    def _calc_stats(self, data_array):
        num_bins = min(max(int(np.sqrt(len(data_array))), 2), 100)

        bins = np.linspace(min(data_array), max(data_array), num_bins)
        hist, bin_edges = np.histogram(data_array, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        x = bin_centers
        y = hist
        return x, y

    def update_plot(self, key, lines):
        _ = key
        self.set_plots(lines)

    def clear(self):
        self.plotwidget.clear()
        self._plots.clear()
        self._lines.clear()
        self.bar_graph_item = None


class XYPlot(DerivedWidgetBase):
    def __init__(self, parent=None):
        super(XYPlot, self).__init__(parent)

        self.plotwidget = pg.PlotWidget()
        self.plotwidget.showGrid(x=True, y=True, alpha=0.2)

        self.fit_curve = pg.PlotCurveItem(pen=pg.mkPen(COLORS[1], width=1))
        self.plotwidget.addItem(self.fit_curve)

        self._fit_params_text = None

        menu = self.plotwidget.getPlotItem().getViewBox().menu
        menu.addSeparator()
        menu.addAction("Remove Plot", self._remove_plot)
        menu.addSeparator()
        menu.addAction("Fit Linear Curve", lambda: self._on_fit_curve(FitType.LINEAR))
        menu.addAction(
            "Fit Quadratic Curve", lambda: self._on_fit_curve(FitType.QUADRATIC)
        )
        menu.addAction(
            "Fit Gaussian Curve", lambda: self._on_fit_curve(FitType.GAUSSIAN)
        )

        self._plots = {}
        self._lines = {}
        self._left_bound = 0
        self._right_bound = 0
        self._last_timestamp_bounds = None

        self._keys_to_correlate = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.plotwidget)
        self.setLayout(main_layout)

    def _remove_plot(self):
        self._plots = {}
        self._lines = {}
        self.clear()
        self.widgetRemoved.emit(PlotTypes.XY.value)

    def _on_fit_curve(self, fit_type):
        x, y = self._plots["xyPlot"].getData()
        if x is None or y is None:
            return

        fitter = Fitter1D(x, y, fit_type)
        params = fitter.fit()
        y_fit = fitter.get_result()

        if y_fit is None:
            self.fit_curve.clear()
            return

        self.fit_curve.setData(x, y_fit)

        self._display_fit_parameters(fit_type, params, x, y)

    def _display_fit_parameters(self, fit_type, params, x, y):
        if fit_type == FitType.LINEAR:
            slope, intercept = params
            text = f"Slope: {slope:.3f}\nIntercept: {intercept:.3f}"

        elif fit_type == FitType.QUADRATIC:
            a, b, c = params
            text = f"a: {a:.3f}\nb: {b:.3f}\nc: {c:.3f}"

        elif fit_type == FitType.GAUSSIAN:
            amplitude, xo, sigma, offset = params
            text = (
                f"Amplitude: {amplitude:.3f}\n"
                f"Center (xo): {xo:.3f}\n"
                f"Sigma: {sigma:.3f}\n"
                f"Offset: {offset:.3f}"
            )
        else:
            text = "Unknown fit type"

        if hasattr(self, "_fit_params_text"):
            self.plotwidget.removeItem(self._fit_params_text)

        self._fit_params_text = pg.TextItem(text, anchor=(0, 1), color=COLORS[1])
        self._fit_params_text.setPos(x[-1], np.max(y))
        self.plotwidget.addItem(self._fit_params_text)

    @pyqtSlot(float, float)
    def on_bounds_changed(self, left_bound, right_bound):
        self._left_bound = left_bound
        self._right_bound = right_bound

    def set_lines_to_use(self, lines):
        self._keys_to_correlate = lines

    def set_autoscale(self):
        self.plotwidget.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def set_plots(self, lines):
        if not (self._keys_to_correlate and lines):
            return

        data = list(
            itertools.chain(
                *[
                    line.get_data()
                    for line in lines.values()
                    if line.get_name() in self._keys_to_correlate
                ]
            )
        )

        if len(data[0]) < 2 or len(data[2]) < 2:
            return

        idx_1_1, idx_1_2 = np.searchsorted(
            data[0], [self._left_bound, self._right_bound]
        )
        idx_2_1, idx_2_2 = np.searchsorted(
            data[2], [self._left_bound, self._right_bound]
        )
        idx_1_2 = min(idx_1_2, len(data[0]) - 1)
        idx_2_2 = min(idx_2_2, len(data[2]) - 1)

        if self._last_timestamp_bounds == (
            data[0][idx_1_1],
            data[0][idx_1_2],
            data[2][idx_2_1],
            data[2][idx_2_2],
        ):
            return

        self.plotwidget.clear()
        self._plots.clear()
        self._lines = lines
        self._last_timestamp_bounds = (
            data[0][idx_1_1],
            data[0][idx_1_2],
            data[2][idx_2_1],
            data[2][idx_2_2],
        )

        data[0], data[1] = (
            data[0][idx_1_1 : idx_1_2 + 1],
            data[1][idx_1_1 : idx_1_2 + 1],
        )
        data[2], data[3] = (
            data[2][idx_2_1 : idx_2_2 + 1],
            data[3][idx_2_1 : idx_2_2 + 1],
        )

        print(f"slice indices: {idx_1_1}, {idx_1_2}, {idx_2_1}, {idx_2_2}")

        infostr = ""
        for ts, dat in zip(data[2], data[3]):
            infostr += f"{ts}: {dat}\n"

        print(infostr)
        print(f"The last dev_ts is {data[0][-1]}")

        try:
            common_ts, dev_data, det_data = interpolate_to_detector_timestamps(*data)
        except AssertionError as e:
            print(e)
            return

        labels = [
            line.get_name()
            for line in lines.values()
            if line.get_name() in self._keys_to_correlate
        ]
        units = [
            line.get_units()
            for line in lines.values()
            if line.get_name() in self._keys_to_correlate
        ]

        bottom_label_str = f"{labels[0]} ({units[0]})" if units[0] else labels[0]
        left_label_str = f"{labels[1]} ({units[1]})" if units[1] else labels[1]

        self.plotwidget.setTitle(title=" vs ".join(labels))
        self.plotwidget.setLabel("bottom", bottom_label_str)
        self.plotwidget.setLabel("left", left_label_str)

        self._plots["xyPlot"] = self.plotwidget.plot(
            dev_data,
            det_data,
            pen=None,
            symbol="o",
            symbolPen=COLORS[0],
            symbolBrush=COLORS[0],
            symbolSize=10,
        )

        if self.fit_curve not in self.plotwidget.items():
            self.plotwidget.addItem(self.fit_curve)

        if self._fit_params_text:
            self.plotwidget.addItem(self._fit_params_text)

    def update_plot(self, key, lines):
        _ = key
        self.set_plots(lines)

    def clear(self):
        self.plotwidget.clear()
        self.fit_curve.clear()
        self._plots.clear()
        self._lines.clear()

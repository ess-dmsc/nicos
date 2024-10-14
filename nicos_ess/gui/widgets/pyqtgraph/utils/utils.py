from datetime import datetime
from enum import Enum

import numpy as np
import pyqtgraph as pg
from scipy.interpolate import interp1d

from nicos.guisupport.qt import QLabel, pyqtSignal

COLORS = [
    (0, 114, 178),  # Blue
    (213, 94, 0),  # Vermillion
    (0, 158, 115),  # Green
    (230, 159, 0),  # Orange
    (86, 180, 233),  # Sky Blue
    (204, 121, 167),  # Reddish Purple
    (240, 228, 66),  # Yellow (High contrast)
    (117, 112, 179),  # Violet
    (27, 158, 119),  # Dark Green
    (217, 95, 2),  # Dark Orange
    (117, 107, 177),  # Light Violet
    (231, 41, 138),  # Pink
    (102, 166, 30),  # Dark Green
    (230, 171, 2),  # Mustard Yellow
    (166, 118, 29),  # Brown
    (44, 160, 44),  # Dark Green
    (148, 103, 189),  # Dark Purple
    (214, 39, 40),  # Red
]

HISTOGRAM_COLORS = [
    (28, 166, 223, 200),  # Light Blue
]


def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


def interpolate_to_common_timestamps(*args):
    ts_data_pairs = list(zip(*[iter(args)] * 2))

    for pair in ts_data_pairs:
        assert len(pair[0]) == len(
            pair[1]
        ), "Data and timestamps must be the same length"
        assert len(pair[0]) == len(np.unique(pair[0])), "Timestamps must be unique"
        assert len(pair[0]) > 1, "Must have more than one timestamp"
        assert np.min(pair[0]) >= 0, "Timestamps must be positive"

    assert len(ts_data_pairs) > 1, "Must have more than one data source"

    common_ts = np.unique(np.concatenate([ts for ts, _ in ts_data_pairs]))  # [2:-3]

    assert len(common_ts) > 1, "Must have more than one timestamp"

    interp_funcs = []

    bounds = []
    for ts, data in ts_data_pairs:
        # Undecided ????
        fill_value = data[-1]
        # fill_value = 'extrapolate'
        interp = interp1d(
            ts, data, kind="linear", fill_value=fill_value, bounds_error=True
        )

        low_bound, high_bound = interp.x[0], interp.x[-1]
        interp_funcs.append(interp)
        bounds.append((low_bound, high_bound))

    highest_low_bound = max([bound[0] for bound in bounds])
    lowest_high_bound = min([bound[1] for bound in bounds])
    idx_low = np.searchsorted(common_ts, highest_low_bound)
    idx_high = np.searchsorted(common_ts, lowest_high_bound)
    common_ts = common_ts[idx_low:idx_high]

    interp_data = []
    for interp_func in interp_funcs:
        interp_data.append(interp_func(common_ts))

    return common_ts, interp_funcs, interp_data


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(datetime.fromtimestamp(value)) for value in values]


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class PlotTypes(Enum):
    XY = "xyPlot"
    HISTOGRAM = "histogramPlot"

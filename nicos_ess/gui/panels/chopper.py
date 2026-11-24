"""Chopper panel: the discs seen from the moderator, and the selected disc's delay errors."""

from collections import deque

import numpy as np
import pyqtgraph as pg

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QSplitter,
    Qt,
    QVBoxLayout,
)
from nicos.utils import currenttime
from nicos_ess.devices.chopper_math import check_geometry
from nicos_ess.gui.widgets.chopper_widget import (
    ChopperLegendWidget,
    ChopperWidget,
)
from nicos_ess.gui.widgets.pyqtgraph.frame_format import readable
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView, Solo
from nicos_ess.gui.widgets.pyqtgraph.theme import COLORS, curve_color
from nicos_ess.utilities.live_frame import curve_frame, float_array

BIN_WIDTH = 100  # ns
# Larger delay errors in ns are not real, and 100 ns bins cannot resolve them.
LARGEST_ERROR = 1e15
HISTORY = 10000

KEY_ROLES = {
    "speed_key": "speed",
    "total_delay_key": "total_delay",
    "park_angle_key": "park_angle",
    "delay_errors_key": "delay_errors",
}

ALL_CHOPPERS = (
    "{name: dev.get_chopper_gui_info() for name, dev in session.devices.items()"
    " if hasattr(dev, 'get_chopper_gui_info')}"
)


def delay_error_stats(samples):
    """Histogram, mean, standard deviation and FWHM of delay-error samples (ns)."""
    samples = float_array(samples)
    # A missing sample becomes nan, and the comparison leaves out nan as well.
    samples = samples[np.abs(samples) < LARGEST_ERROR]
    if not samples.size:
        return None
    # The bins cover only the bulk, otherwise a few stray samples would squeeze
    # the peak into one bin.
    median = np.median(samples)
    spread = 15 * np.median(np.abs(samples - median))
    low, high = samples.min(), samples.max()
    if spread:
        low, high = max(low, median - spread), min(high, median + spread)
    # The bins lie on a fixed grid so they stay in place while samples arrive,
    # and there are at most 101 bins.
    width = BIN_WIDTH * max(1, np.ceil((high - low) / BIN_WIDTH / 100))
    low = np.floor(low / width) * width
    high = max(np.ceil(high / width) * width, low + width)
    hist, edges = np.histogram(samples, bins=np.arange(low, high + width / 2, width))
    outside = samples.size - int(hist.sum())
    peak = int(np.argmax(hist))
    below = np.flatnonzero(hist[:peak] < hist[peak] / 2)
    left = below[-1] + 1 if below.size else 0
    below = np.flatnonzero(hist[peak:] < hist[peak] / 2)
    right = below[0] + peak if below.size else len(hist)
    return {
        "edges": edges,
        "y": hist,
        "mean": float(samples.mean()),
        "stddev": float(samples.std()),
        "fwhm": float(edges[right] - edges[left]),
        "left": edges[left],
        "right": edges[right],
        "outside": outside,
    }


def histogram_frame(stats):
    facts = [f"{name} {readable(stats[key])} ns" for name, key in TEXTS]
    facts += [f"{stats['outside']} outside"] * bool(stats["outside"])
    meta = {"facts": facts} if len(stats["y"]) else {}
    x, y = stats["edges"], stats["y"]
    return curve_frame("delay error", "counts", x, y, "ns", counts=True, meta=meta)


def trend_frames(trend, since):
    """Return frames of the mean, deviation and FWHM over time.

    The mean uses the left axis and the others use the right axis.
    """
    t, *values = np.array(trend, dtype=float).reshape(-1, 4).T
    keep = t >= since
    t = t[keep]
    return [
        curve_frame("time", "ns", t, v[keep], "datetime64[s]", name=name, meta=meta)
        for (name, _key), v, meta in zip(TEXTS, values, ({}, RIGHT, RIGHT), strict=True)
    ]


NO_STATS = dict(
    edges=[0.0], y=np.zeros(0), mean=0, stddev=0, fwhm=0, left=0, right=0, outside=0
)
TEXTS = (("mean", "mean"), ("std. dev.", "stddev"), ("FWHM", "fwhm"))
RIGHT = {"axis": "right"}


class ChopperPanel(Panel):
    panelName = "Choppers"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self.chopper_widget = ChopperWidget(parent=self)
        self.histogram = FrameView("Delay errors", totals=False)
        self.trend = FrameView("Delay error trend", totals=False)
        # Lines mark the mean and one standard deviation on either side, and the
        # FWHM bins are filled under the curve. They use the colours of their
        # trends. The mean is dashed because the histogram has the same colour.
        dash = Qt.PenStyle.DashLine
        self.marks = [
            pg.InfiniteLine(angle=90, pen=pg.mkPen(curve_color(i), width=2, style=s))
            for i, s in ((0, dash), (1, None), (1, None))
        ]
        self.fwhm = pg.PlotDataItem(
            stepMode="center", fillLevel=0, brush=COLORS[2] + "45", pen=pg.mkPen(None)
        )
        self.fwhm.setZValue(-1)  # The fill goes under the histogram line.
        for item in (self.fwhm, *self.marks):
            self.histogram.plot.addItem(item, ignoreBounds=True)
        self.trend_span = QSpinBox(minimum=1, maximum=3600, value=60, suffix=" s trend")
        self.trend_span.valueChanged.connect(self._show_selected)
        self._roles = {}
        self._registered = set()
        self._latest = {}
        self._trends = {}

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(ChopperLegendWidget(parent=self))
        controls.addStretch(1)
        controls.addWidget(self.trend_span)
        layout.addLayout(controls)

        self._unverified_geometry_warning = QLabel()
        self._unverified_geometry_warning.setWordWrap(True)
        self._unverified_geometry_warning.setStyleSheet(
            "color: #8b0000; background-color: #ffd6d6; border: 1px solid #c40000;"
            " padding: 6px; font-weight: bold;"
        )
        self._unverified_geometry_warning.hide()
        layout.addWidget(self._unverified_geometry_warning)

        plots = QSplitter(Qt.Orientation.Horizontal)
        self.solo = Solo([FrameCanvas(self.histogram), FrameCanvas(self.trend)])
        for canvas in self.solo.canvases:
            plots.addWidget(canvas)
        view = QSplitter(Qt.Orientation.Vertical)
        view.addWidget(self.chopper_widget)
        view.addWidget(plots)
        view.setStretchFactor(0, 1)
        view.setStretchFactor(1, 1)
        view.setSizes([1, 1])
        layout.addWidget(view)

        client.connected.connect(self._load_choppers)
        client.setup.connect(lambda _setup: self._load_choppers())
        client.disconnected.connect(self.on_client_disconnect)
        self.chopper_widget.onChopperSelected.connect(self._show_selected)
        self._show_selected()  # This shows empty plots until data arrives.

    def _load_choppers(self):
        infos = self.client.eval(ALL_CHOPPERS, {})
        choppers = []
        for info in infos.values() if isinstance(infos, dict) else ():
            try:
                check_geometry(info)
            except ValueError as err:
                self.log.warning("Ignoring chopper %s: %s", info.get("chopper"), err)
                continue
            choppers.append(info)
        self._roles = {
            info[field].lower(): (info["chopper"], role)
            for info in choppers
            for field, role in KEY_ROLES.items()
            if info.get(field)
        }
        self.chopper_widget.update_chopper_data(choppers)
        self._show_unverified(choppers)

        for key in self._roles.keys() - self._registered:
            self._registered.add(self.client.register(self, key))
        # the client's refresh on reconnect can arrive before the choppers are loaded
        current = self.client.ask(
            "getcachekeys", ",".join(self._roles), quiet=True, default=[]
        )
        for key, value in current or ():
            self.on_keyChange(key, value, currenttime(), False)

    def on_client_disconnect(self):
        self.chopper_widget.clear()
        self._show_selected(None)
        self._show_unverified([])

    def on_keyChange(self, key, value, timestamp, expired):
        target = self._roles.get(key.lower())
        if target is None:
            super().on_keyChange(key, value, timestamp, expired)
            return
        name, role = target
        value = None if expired else value
        if role == "delay_errors":
            self._delay_errors(name, timestamp, value)
        else:
            self.chopper_widget.set_value(name, role, value)

    def _delay_errors(self, name, timestamp, samples):
        if samples is None:
            self._latest.pop(name, None)
            self._trends.pop(name, None)
        else:
            stats = delay_error_stats(samples)
            if stats is None:
                return
            self._latest[name] = stats
            trend = self._trends.setdefault(name, deque(maxlen=HISTORY))
            trend.append((timestamp, stats["mean"], stats["stddev"], stats["fwhm"]))
        if name == self.chopper_widget.get_selected_chopper():
            self._show_selected()

    def _show_selected(self, *_args):
        name = self.chopper_widget.get_selected_chopper()
        stats = self._latest.get(name, NO_STATS)  # A disc without data shows nothing.
        trend = self._trends.get(name, ())
        received = trend[-1][0] if trend else None
        # The usual period between readings flags late data.
        times = [t for t, *_v in list(trend)[-9:]]
        period = float(np.median(np.diff(times))) if len(times) > 1 else 0.0
        self.histogram.period = self.trend.period = period
        of = f" of {name}" if name else ""
        self.histogram.name = f"Delay errors{of}"
        self.trend.name = f"Delay error trend{of}"
        self.histogram.show_frame(histogram_frame(stats), received)
        mean, spread = stats["mean"], stats["stddev"]
        for mark, x in zip(
            self.marks, (mean, mean - spread, mean + spread), strict=True
        ):
            mark.setValue(x)
            mark.setVisible(stats is not NO_STATS)
        edges = np.asarray(stats["edges"])
        first, last = np.searchsorted(edges, (stats["left"], stats["right"]))
        self.fwhm.setData(edges[first : last + 1], stats["y"][first:last])
        self.fwhm.setVisible(stats is not NO_STATS)
        since = trend[-1][0] - self.trend_span.value() if trend else 0
        self.trend.show_frames(trend_frames(trend, since), received)

    def _show_unverified(self, choppers):
        names = [c["chopper"] for c in choppers if not c["visual_geometry_verified"]]
        self._unverified_geometry_warning.setText(
            "UNVERIFIED CHOPPER GEOMETRY: openings and angles for "
            f"{', '.join(names)} have not been verified. "
            "Do not use this visualization as truth."
        )
        self._unverified_geometry_warning.setVisible(bool(names))

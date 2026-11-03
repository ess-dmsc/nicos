"""Chopper panel: the discs seen from the moderator, and the selected disc's delay errors."""

from collections import deque

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QHBoxLayout,
    QLabel,
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
from nicos_ess.gui.widgets.pyqtgraph.histogram_data_viewer import (
    HistogramDataViewer,
    TrendViewer,
)

BIN_WIDTH = 100  # ns
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
    samples = np.asarray(samples, dtype=float)
    if not samples.size:
        return None
    low, high = samples.min(), samples.max()
    if high == low:
        bins = [low - BIN_WIDTH / 2, high + BIN_WIDTH / 2]
    else:
        count = min(max(int(np.ceil((high - low) / BIN_WIDTH)), 1), 100)
        bins = np.linspace(low, high, count + 1)
    hist, edges = np.histogram(samples, bins=bins)
    peak = int(np.argmax(hist))
    below = np.flatnonzero(hist[:peak] < hist[peak] / 2)
    left = below[-1] if below.size else 0
    below = np.flatnonzero(hist[peak:] < hist[peak] / 2)
    right = min((below[0] + peak if below.size else len(hist) - 1) + 1, len(edges) - 1)
    return {
        "x": (edges[:-1] + edges[1:]) / 2,
        "y": hist,
        "mean": float(samples.mean()),
        "stddev": float(samples.std()),
        "fwhm": float(edges[right] - edges[left]),
        "left": edges[left],
        "right": edges[right],
    }


class ChopperPanel(Panel):
    panelName = "Choppers"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self.chopper_widget = ChopperWidget(parent=self)
        self.histogram_widget = HistogramDataViewer(parent=self)
        self.trend_widget = TrendViewer(parent=self)
        self._roles = {}
        self._registered = set()
        self._latest = {}
        self._trends = {}

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(ChopperLegendWidget(parent=self))
        controls.addStretch(1)
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
        plots.addWidget(self.histogram_widget)
        plots.addWidget(self.trend_widget)
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
        self.histogram_widget.clear()
        self.trend_widget.clear()
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
            self._show_selected(name)

    def _show_selected(self, name):
        stats = self._latest.get(name)
        if stats is None:
            self.histogram_widget.clear()
            self.trend_widget.clear()
            return
        self.histogram_widget.receive_data(
            stats["x"],
            stats["y"],
            stats["mean"],
            stats["stddev"],
            stats["fwhm"],
            stats["left"],
            stats["right"],
        )
        self.trend_widget.receive_data(
            *(list(c) for c in zip(*self._trends[name], strict=True))
        )

    def _show_unverified(self, choppers):
        names = [c["chopper"] for c in choppers if not c["visual_geometry_verified"]]
        self._unverified_geometry_warning.setText(
            "UNVERIFIED CHOPPER GEOMETRY: openings and angles for "
            f"{', '.join(names)} have not been verified. "
            "Do not use this visualization as truth."
        )
        self._unverified_geometry_warning.setVisible(bool(names))

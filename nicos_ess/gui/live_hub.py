"""All live views of a GUI share the live data through one `LiveHub` per connection.

The hub decodes each live data event once. For every output it keeps the newest
frame, the total over time, the views that show the output and its plot settings.
"""

from __future__ import annotations

import fnmatch
import json
import time

from nicos.clients.gui.utils import SettingGroup
from nicos.core.constants import LIVE
from nicos.guisupport.qt import QObject, QTimer, pyqtSignal, sip
from nicos_ess.gui.widgets.pyqtgraph.frame_format import same_unit, total_of
from nicos_ess.utilities.frame_views import axis
from nicos_ess.utilities.live_frame import frames
from nicos_ess.utilities.series import Series

SETTINGS = "Live views"
# A longer gap between frames in seconds is a pause and not the frame period.
SLOW = 60
# The hub saves the plot settings of this many outputs that were shown last.
SAVED_PLOTS = 200


class LiveHub(QObject):
    # The signal carries the names of the outputs that arrived.
    arrived = pyqtSignal(object)
    # This is emitted when outputs move to other views.
    placed = pyqtSignal()

    def __init__(self, client, log):
        super().__init__()
        self.client, self.log = client, log
        self.panels, self.outputs, self.series = [], {}, {}
        # This maps each output to the device that sent it.
        self.devices = {}
        # This holds the seconds between the last two frames of each output.
        self.periods = {}
        # Frames came again at this time after a pause, as at the start of a count.
        self.resumed = 0.0
        placement, views = _read_saved()
        # Damaged entries are left out.
        self.placement = {
            k: [i for i in v if type(i) is int]
            for k, v in placement.items()
            if isinstance(v, list)
        }
        self.view_states = {
            name: {k: state for k, state in states.items() if isinstance(state, dict)}
            for name, states in views.items()
            if isinstance(states, dict)
        }
        client.livedata.connect(self.on_livedata)
        client.connected.connect(self.on_connected)
        client.setup.connect(self.on_setup)

    def save(self):
        views = dict(list(self.view_states.items())[-SAVED_PLOTS:])
        saved = dict(placement=self.placement, views=views)
        with SettingGroup(SETTINGS) as settings:
            settings.setValue("hub", json.dumps(saved))

    def register(self, panel):
        # PyQt breaks this connection when the hub is deleted first, which happens at exit.
        panel.destroyed.connect(self._unregister)
        self.panels = sorted([*self.panels, panel], key=lambda p: p.index)
        if self.client.isconnected and len(self.panels) == 1:
            self.on_connected()

    def _unregister(self):
        # sip marks the closed panel deleted before Qt sends the signal.
        self.panels = [p for p in self.panels if not sip.isdeleted(p)]
        # Outputs placed only in the closed view now go to another view.
        QTimer.singleShot(0, self.placed.emit)

    def indices(self):
        return [p.index for p in self.panels]

    def names(self):
        return sorted(self.outputs)

    def title(self, index):
        return next((p.title for p in self.panels if p.index == index), f"Live {index}")

    def where(self, name):
        """Return the indices of the views that show *name*.

        If the user has not placed *name* in a view of this GUI, the views
        whose ``outputs`` option matches it show it, or else the views of its
        own output (an ROI plot "det.roi0" goes where "det" is), or else the
        first view.
        """
        indices = self.indices()
        if name in self.placement:
            place = [i for i in self.placement[name] if i in indices]
            # An empty placement hides the output, a stale one falls through.
            if place or not self.placement[name]:
                return place
        wanted = self._wanted_by_option(name)
        output = name.split(".")[0]
        if not wanted and output != name and output in self.outputs:
            wanted = self.where(output)
        return wanted or indices[:1]

    def _wanted_by_option(self, name):
        """Return the indices of the views whose ``outputs`` option matches *name*."""
        return [
            panel.index
            for panel in self.panels
            if any(fnmatch.fnmatchcase(name, pattern) for pattern in panel.outputs)
        ]

    def show_in(self, name, index, on):
        place = set(self.where(name)) - {index} | ({index} if on else set())
        self.placement[name] = sorted(place)
        self.placed.emit()

    def move(self, name, index, source=None):
        """Show *name* in the view *index*, and no longer in *source*.

        Without *source*, the output leaves all other views.
        """
        stay = set() if source is None else set(self.where(name)) - {source}
        self.placement[name] = sorted(stay | {index})
        self.placed.emit()

    def show_everything_in(self, index):
        for name in self.names():
            self.placement[name] = sorted({*self.where(name), index})
        self.placed.emit()

    def drop(self, name):
        """Forget the output *name*, but not where it is placed or its plot settings."""
        if self.outputs.pop(name, None) is not None:
            # A plot kept during a drag holds the series, so it is not replaced.
            self.series_for(name).clear()
            self.devices.pop(name, None)
            self.periods.pop(name, None)
            self.placed.emit()

    def states_of(self, name):
        """Return the plot settings of *name* by view, and mark them as used last."""
        self.view_states[name] = self.view_states.pop(name, {})
        return self.view_states[name]

    def series_for(self, name):
        """Return the totals over time of *name*."""
        return self.series.setdefault(name, Series())

    def on_connected(self):
        self.client.tell("eventunmask", ["livedata"])

    def on_setup(self, _setups=None):
        """Forget the outputs of devices that are no longer loaded."""
        loaded = self.client.getDeviceList(only_explicit=False)
        for name in [n for n, d in self.devices.items() if d not in loaded]:
            self.drop(name)

    def on_livedata(self, params, blobs):
        if params.get("tag") != LIVE:
            # Other tags belong to written data files.
            return
        received = time.time()
        try:
            arrays = [
                (name, frame, totals(frame, received))
                for name, frame in frames(params, blobs)
            ]
        except ValueError as err:
            self.log.warning("unreadable live data of %s: %s", params.get("det"), err)
            return
        if received - max((t for _f, t in self.outputs.values()), default=0) >= SLOW:
            # All outputs were quiet, so a count starts.
            self.resumed = received
        for name, frame, points in arrays:
            self._keep(name, frame, points, received, params["det"])
        if arrays:
            self.arrived.emit([name for name, _frame, _points in arrays])

    def _keep(self, name, frame, points, received, device):
        """Keep *frame* as the newest frame of *name* and add *points* to its
        totals over time."""
        if name in self.outputs and received - self.outputs[name][1] < SLOW:
            self.periods[name] = received - self.outputs[name][1]
        last = self.outputs.get(name, (frame,))[0]
        other_source = self.devices.get(name, device) != device
        self.outputs[name] = (frame, received)
        self.devices[name] = device
        series = self.series_for(name)
        if (
            other_source
            or last.counts != frame.counts
            or not same_unit(last.unit, frame.unit)
        ):
            # The totals of another source or quantity do not continue the
            # line, and the other source may stamp them by another clock.
            series.clear()
        series.add(*points)


def _read_saved():
    """Return the placement and the plot settings that `LiveHub.save` wrote.

    A damaged part of the settings is read as empty.
    """
    with SettingGroup(SETTINGS) as settings:
        raw = settings.value("hub")
    try:
        saved = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        return {}, {}
    placement, views = saved.get("placement"), saved.get("views")
    return (
        placement if isinstance(placement, dict) else {},
        views if isinstance(views, dict) else {},
    )


def totals(frame, received):
    """Return the times and values that *frame* adds to its totals over time."""
    ax = axis(frame, frame.dims[0]) if len(frame.dims) == 1 else None
    if ax is not None and ax.is_time and frame.data.size > 1:
        return ax.values[1:] if ax.is_edges else ax.values, frame.data
    return float(frame.meta.get("time") or received), float(total_of(frame))


def hub_for(client, log):
    """Return the `LiveHub` of *client* and create it on first use."""
    if getattr(client, "_live_hub", None) is None:
        client._live_hub = LiveHub(client, log)
    return client._live_hub

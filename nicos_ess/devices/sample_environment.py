"""Presence of plug-and-play sample environment equipment."""

import threading

from nicos import session
from nicos.core import POLLER, SIMULATION, Override, Readable, listof, status
from nicos.utils import currenttime
from nicos_ess.devices.epics.pva.epics_common import create_wrapper

PVA_SCHEME = "pva://"


def presence_signals(setup_info):
    """Return {setup name: presence signal} of all plug-and-play setups."""
    return {
        name: info["extended"]["presence_signal"]
        for name, info in setup_info.items()
        if info
        and info["group"] == "plugplay"
        and "presence_signal" in info["extended"]
    }


class SampleEnvironmentPresence(Readable):
    """Lists the plug-and-play setups whose equipment is present.

    Every setup in group ``plugplay`` names a presence signal in its
    ``extended`` dict::

        extended = dict(presence_signal="pva://SE-SEE:SE-LS336-003:KRDG0")

    The setup is present while that signal is connected.  Only ``pva://``
    signals are supported.  Like the ESS EPICS devices, only the poller
    monitors the signals and writes the value to the cache.  The Setups panel
    lists plug-and-play setups that are present or loaded; nothing is loaded
    or unloaded automatically.
    """

    parameter_overrides = {
        "unit": Override(mandatory=False, default=""),
        "fmtstr": Override(default="%s"),
    }

    valuetype = listof(str)

    def doInit(self, mode):
        self._present = set()
        self._lock = threading.Lock()
        self._monitors = []
        if mode == SIMULATION or session.sessiontype != POLLER:
            return
        self._epics = create_wrapper(3.0, use_pva=True)
        for setup, signal in sorted(presence_signals(session.getSetupInfo()).items()):
            if not signal.startswith(PVA_SCHEME):
                self.log.warning(
                    "setup %s: unsupported presence signal %r", setup, signal
                )
                continue
            self._monitors.append(
                self._epics.subscribe(
                    signal[len(PVA_SCHEME) :], setup, None, self._on_connection
                )
            )

    def doShutdown(self):
        for monitor in self._monitors:
            self._epics.close_subscription(monitor)
        self._monitors = []

    def _getFromCache(self, name, func, maxage=None):
        if session.sessiontype == POLLER:
            return Readable._getFromCache(self, name, func, maxage)
        # like CacheReader: other sessions never write the poller's value back
        default = [] if name == "value" else (status.UNKNOWN, "no poller value")
        return self._cache.get(self, name, default) if self._cache else default

    def doRead(self, maxage=0):
        with self._lock:
            return sorted(self._present)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def _on_connection(self, pvname, setup, is_connected, **kwargs):
        with self._lock:
            if is_connected:
                self._present.add(setup)
            else:
                self._present.discard(setup)
            present = sorted(self._present)
        if self._cache:
            self._cache.put(self, "value", present, currenttime(), self.maxage)

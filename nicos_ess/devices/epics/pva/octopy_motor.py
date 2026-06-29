import threading
import time

from nicos.core import CommunicationError, MoveError, Override, Param, pvname, status
from nicos.core.mixins import CanDisable
from nicos.devices.abstract import CanReference, Motor
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    command_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
)


class OctopyMotor(EpicsDeviceBase, CanDisable, CanReference, Motor):
    """Motor device for Octopy-style axis PVs."""

    valuetype = float

    parameters = {
        "motorpv": Param(
            "Base PV name (without the trailing suffix).",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        # velocity may be changed from outside, don't cache forever
        "speed": Override(volatile=True, unit="mm/s"),
    }

    _primary_channel = "value"
    _default_pv_prefix_attr = "motorpv"
    _epics_channels = {
        "value": readback_channel("-position-r", cache_key="value", primary=True),
        "target": setpoint_channel("-s", cache_key="target"),
        "stop": command_channel("-halt-s"),
        "speed": setpoint_channel("-velocity-s"),
        "enable": setpoint_channel("-enable-s", refresh_status=True),
        "home": command_channel("-home-s"),
        "reset": command_channel("-reset-s"),
        "busy": status_channel("-busy-r"),
        "move_done": status_channel("-move_done-r"),
    }

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        EpicsDeviceBase.doPreinit(self, mode)

    # One PV is enough to see that the IOC is there.
    _connect_channels = ("target",)

    def doReadTarget(self):
        return self._read_channel_cached("target")

    def doReadSpeed(self):
        return self._epics.get_channel_value("speed")

    def doStart(self, value):
        if abs(self.read(0) - value) <= self.precision:
            return

        if self._cache:
            # ensure that we are not retrieving old values
            self._cache.invalidate(self, "busy")
            self._cache.invalidate(self, "move_done")

        if self._read_channel_cached("busy", maxage=0) == 1:
            raise MoveError("Motor is busy")

        self._cache.put(self._name, "status", (status.BUSY, "Moving"), time.time())
        self._epics.put_channel_value("target", value)
        # octopy does not update move_done immediately, so we need to wait here
        # until it is set to 0.
        self._epics.wait_for("move_done", 0, timeout=5.0)

    def doStop(self):
        self._epics.put_channel_value("stop", 1)

    def doEnable(self, on):
        self._epics.put_channel_value("enable", 1 if on else 0)

    def doWriteSpeed(self, value):
        self._epics.put_channel_value("speed", max(0.0, value))

    def doReference(self):
        self._epics.put_channel_value("home", 1)

    def doReset(self):
        self._epics.put_channel_value("reset", 1)

    def doIsAtTarget(self, pos=None, target=None):
        if pos is None:
            pos = self.read(0)
        if target is None:
            target = self.target

        within_target = abs(target - pos) <= self.precision

        return within_target and self._read_channel_cached("move_done", maxage=0) == 1

    def doIsCompleted(self):
        return self._is_completed(maxage=0)

    def _is_completed(self, maxage=0):
        busy = self._read_channel_cached("busy", maxage=maxage) == 1
        move_done = self._read_channel_cached("move_done", maxage=maxage) == 1
        return not busy and move_done

    def _compute_status(self, maxage=0):
        try:
            if not self._is_completed(maxage=maxage):
                target = self._read_channel_cached("target", maxage=maxage)
                return status.BUSY, f"moving to {target}"

            is_enabled = self._read_channel_cached("enable", maxage=maxage) == 1
            if not is_enabled:
                return status.WARN, "Motor is not enabled"
        except (TimeoutError, CommunicationError):
            return status.UNKNOWN, "lost connection to EPICS"

        return status.OK, "ready"

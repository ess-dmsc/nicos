import threading
import time

from nicos.core import MoveError, Override, Param, pvname, status
from nicos.core.mixins import CanDisable
from nicos.devices.abstract import CanReference, Motor
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
)


class OctopyMotor(EpicsDeviceBase, CanDisable, CanReference, Motor):
    """Motor device for controllers exposing *Octopy*‑style PVs.

    Unlike the standard *EPICS motor record*, an Octopy axis only provides a
    minimal set of process variables (PVs):

    ===== =====================================
    readback  ``<base>-position-r``
    setpoint  ``<base>-s``
    velocity  ``<base>-velocity-s``
    enable    ``<base>-enable-s``
    halt      ``<base>-halt-s``
    home      ``<base>-home-s``
    reset     ``<base>-reset-s``
    ===== =====================================

    The :pyattr:`motorpv` parameter must therefore contain the *base* part of
    the PV name (e.g. ``SE:SE-HTP-003:axis-x``).  All other PVs are derived at
    run‑time by appending the suffixes listed above.
    """

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
    _default_pv_root_attr = "motorpv"
    _epics_channels = {
        "value": EpicsChannelInfo(
            "value", "-position-r", EpicsChannelRole.VALUE_AND_STATUS
        ),
        "target": EpicsChannelInfo("target", "-s", EpicsChannelRole.VALUE),
        "stop": EpicsChannelInfo("", "-halt-s", EpicsChannelRole.VALUE),
        "speed": EpicsChannelInfo("", "-velocity-s", EpicsChannelRole.VALUE),
        "enable": EpicsChannelInfo("", "-enable-s", EpicsChannelRole.STATUS),
        "home": EpicsChannelInfo("", "-home-s", EpicsChannelRole.VALUE),
        "reset": EpicsChannelInfo("", "-reset-s", EpicsChannelRole.VALUE),
        "busy": EpicsChannelInfo("", "-busy-r", EpicsChannelRole.STATUS),
        "move_done": EpicsChannelInfo("", "-move_done-r", EpicsChannelRole.STATUS),
    }

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        EpicsDeviceBase.doPreinit(self, mode)

    def _pvs_to_connect(self):
        return [f"{self.motorpv}-s"]

    def doRead(self, maxage=0):
        return self._read_channel_cached("value", maxage=maxage)

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
        """
        A final check at the end of a move to ensure we are at the target.
        """
        if pos is None:
            pos = self.read(0)
        if target is None:
            target = self.target

        within_target = abs(target - pos) <= self.precision

        return within_target and self._read_channel_cached("move_done", maxage=0) == 1

    def doIsCompleted(self):
        """
        Continuously check if a movement is completed.
        """
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

            # Check if the motor is enabled
            is_enabled = self._read_channel_cached("enable", maxage=maxage) == 1
            if not is_enabled:
                return status.WARN, "Motor is not enabled"
        except TimeoutError:
            return status.UNKNOWN, "lost connection to EPICS"

        return status.OK, "ready"

    def _on_connection_change(self, change):
        # Any of the few octopy PVs dropping means the axis is unusable.
        if change.is_connected:
            self.log.debug("%s connected!", change.pv_name)
        else:
            self.log.warning("%s disconnected!", change.pv_name)
            self._cache.put(
                self._name,
                "status",
                (status.UNKNOWN, "lost connection to EPICS"),
                time.time(),
            )

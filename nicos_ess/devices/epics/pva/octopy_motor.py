import threading
import time

from nicos import session
from nicos.core import POLLER, MoveError, Override, Param, pvname, status
from nicos.core.mixins import CanDisable
from nicos.devices.abstract import CanReference, Motor
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class OctopyMotor(EpicsParameters, CanDisable, CanReference, Motor):
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

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._epics_subscriptions = []
        self._cache_key_status = "status"

        self._record_fields = {
            "value": RecordInfo("value", "-position-r", RecordType.BOTH),
            "target": RecordInfo("target", "-s", RecordType.VALUE),
            "stop": RecordInfo("", "-halt-s", RecordType.VALUE),
            "speed": RecordInfo("", "-velocity-s", RecordType.VALUE),
            "enable": RecordInfo("", "-enable-s", RecordType.VALUE),
            "home": RecordInfo("", "-home-s", RecordType.VALUE),
            "reset": RecordInfo("", "-reset-s", RecordType.VALUE),
            "busy": RecordInfo("", "-busy-r", RecordType.VALUE),
            "move_done": RecordInfo("", "-move_done-r", RecordType.VALUE),
        }

        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(f"{self.motorpv}-s")

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            for key, info in self._record_fields.items():
                if info.record_type in (RecordType.VALUE, RecordType.BOTH):
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.motorpv}{info.pv_suffix}",
                            key,
                            self._value_change_callback,
                            self._connection_change_callback,
                        )
                    )

    def _get_cached_pv_or_ask(self, param, as_string=False):
        return get_from_cache_or(self, param, lambda: self._get_pv(param, as_string))

    def _get_pv(self, param, as_string=False):
        return self._epics_wrapper.get_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", as_string
        )

    def _put_pv(self, param, value):
        self._epics_wrapper.put_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", value
        )

    def _wait_until(self, pv_name, expected_value, precision=None, timeout=5.0):
        """Set up a subscription and wait until the PV reaches the expected value."""
        event = threading.Event()

        def callback(name, param, value, units, limits, severity, message, **kwargs):
            if precision is not None and isinstance(value, (int, float)):
                if abs(value - expected_value) <= precision:
                    event.set()
            else:
                if value == expected_value:
                    event.set()

        sub = self._epics_wrapper.subscribe(
            f"{self.motorpv}{self._record_fields[pv_name].pv_suffix}",
            pv_name,
            callback,
        )
        try:
            # already done? exit immediately
            current_value = self._get_pv(
                pv_name,
                as_string=False if isinstance(expected_value, (int, float)) else True,
            )
            if precision is not None and isinstance(current_value, (int, float)):
                if abs(current_value - expected_value) <= precision:
                    return
            else:
                if current_value == expected_value:
                    return
            # wait for callback to signal completion
            if not event.wait(timeout):
                raise TimeoutError(
                    f"Timeout waiting for {pv_name} to become {expected_value}"
                )
        finally:
            self._epics_wrapper.close_subscription(sub)

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("value")

    def doReadTarget(self):
        return self._get_cached_pv_or_ask("target")

    def doReadSpeed(self):
        return self._get_cached_pv_or_ask("speed")

    def doStart(self, value):
        if abs(self.read(0) - value) <= self.precision:
            return

        if self._get_cached_pv_or_ask("busy") == 1:
            raise MoveError("Motor is busy")

        self._cache.put(
            self._name, self._cache_key_status, (status.BUSY, "Moving"), time.time()
        )
        self._put_pv("target", value)
        # octopy does not update move_done immediately, so we need to wait here
        # until it is set to 0.
        self._wait_until("move_done", 0, timeout=5.0)

    def doStop(self):
        self._put_pv("stop", 1)

    def doEnable(self, on):
        self._put_pv("enable", 1 if on else 0)

    def doWriteSpeed(self, value):
        self._put_pv("speed", max(0.0, value))

    def doReference(self):
        self._put_pv("home", 1)

    def doReset(self):
        self._put_pv("reset", 1)

    def doIsAtTarget(self, pos=None, target=None):
        """
        A final check at the end of a move to ensure we are at the target.
        """
        if pos is None:
            pos = self.read(0)
        if target is None:
            target = self.target

        within_target = abs(target - pos) <= self.precision

        self.log.warn(
            f"doIsAtTarget: pos={pos}, target={target}, within_target={within_target}, move_done={self._get_cached_pv_or_ask('move_done')}"
        )

        return within_target and self._get_cached_pv_or_ask("move_done") == 1

    def doIsCompleted(self):
        """
        Continously check if a movement is completed.
        """
        busy = self._get_cached_pv_or_ask("busy") == 1
        move_done = self._get_cached_pv_or_ask("move_done") == 1
        self.log.warn(f"doIsCompleted: busy={busy}, move_done={move_done}")
        return not busy and move_done

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, self._cache_key_status, self._do_status)

    def _do_status(self):
        if not self.doIsCompleted():
            return status.BUSY, f"moving to {self.target}"

        # Check if the motor is enabled
        is_enabled = self._get_cached_pv_or_ask("enable") == 1
        if not is_enabled:
            return status.WARN, "Motor is not enabled"

        return status.OK, "ready"

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        self._cache.put(self._name, param, value, time.time())
        self._cache.put(
            self._name, self._cache_key_status, self._do_status(), time.time()
        )

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if not is_connected:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                self._cache_key_status,
                (status.ERROR, "communication failure"),
                time.time(),
            )
        else:
            self.log.debug("%s connected!", name)

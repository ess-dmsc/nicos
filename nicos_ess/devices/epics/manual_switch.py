import time

from nicos import session
from nicos.core import (
    POLLER,
    Override,
    Param,
    PositionError,
    anytype,
    nonemptylistof,
    oneof,
    pvname,
    status,
)
from nicos.devices.abstract import Moveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class ManualSwitch(EpicsParameters, Moveable):
    """A manually change-able, discrete-state EPICS device."""

    parameters = {
        "writepv": Param(
            "PV that stores the chosen state",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
        "states": Param(
            "List of allowed logical states",
            type=nonemptylistof(anytype),
            mandatory=True,
        ),
        "mapping": Param(
            "Dict mapping logical *states* → raw PV values",
            type=dict,
            mandatory=False,
            settable=False,
            default={},
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "writepv": RecordInfo("target", "", RecordType.BOTH),
        }

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

        self._epics_wrapper.connect_pv(self.writepv)

        if not self.mapping:
            self.mapping = {state: state for state in self.states}
        self._reverse_mapping = {v: k for k, v in self.mapping.items()}

    def doInit(self, mode):
        self.valuetype = oneof(*self.states)

        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )

    def doStart(self, target):
        if target not in self.states:
            raise PositionError(self, f"{target!r} is not among {self.states!r}")

        self._epics_wrapper.put_pv_value(self.writepv, self.mapping[target])
        self._cache.put(self._name, "target", target, time.time())

    def doReadTarget(self, maxage=0):
        raw = get_from_cache_or(
            self,
            "target",
            lambda: self._epics_wrapper.get_pv_value(self.writepv),
        )
        return self._reverse_mapping.get(raw, raw)

    def doRead(self, maxage=0):
        return (
            self.target
            if self.target in self.states
            else f"Unknown target {self.target!r} not in {self.states!r}"
        )

    def doStatus(self, maxage=0):
        def _status_from_pv():
            try:
                return self._epics_wrapper.get_alarm_status(self.writepv)
            except TimeoutError:
                return status.ERROR, "timeout reading status"

        return get_from_cache_or(self, "status", _status_from_pv)

    def doIsAllowed(self, target):
        ok = target in self.states
        return ok, "" if ok else f"{target!r} is not in {self.states!r}"

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        logical = self._reverse_mapping.get(value, value)
        self._cache.put(self._name, param, logical, time.time())

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["writepv"].cache_key:
            return

        if is_connected:
            self.log.debug("%s connected!", name)
            self._cache.put(self._name, "status", (status.OK, ""), time.time())
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.ERROR, "communication failure"),
                time.time(),
            )

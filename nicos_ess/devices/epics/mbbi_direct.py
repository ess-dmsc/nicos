import copy
import time

from nicos import session
from nicos.core import (
    POLLER,
    Attach,
    Override,
    Param,
    Readable,
    Waitable,
    listof,
    status,
)
from nicos.devices.abstract import MappedMoveable, Moveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class MBBIDirectStatus(EpicsParameters, Readable):
    """
    This device automatically handles EPICS MBBI direct records with named bits.
    """

    parameters = {
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
        "number_of_bits": Param(
            "Number of bits to monitor",
            type=int,
            settable=False,
            mandatory=True,
        ),
    }
    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    def doPreinit(self, mode):
        self._bit_map = {}
        self._alarm_state = {}
        self._record_fields = {}
        for i in range(self.number_of_bits):
            hex = f"{i:x}".upper()
            self._record_fields[f"bit_value_{i}"] = RecordInfo(
                "", f".B{hex}", RecordType.STATUS
            )
            self._record_fields[f"bit_name_{i}"] = RecordInfo(
                "", f"BitNam{i}", RecordType.STATUS
            )
            self._bit_map[f"bit_value_{i}"] = f"bit_name_{i}"

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check one of the PVs exists
        self._epics_wrapper.connect_pv(self.pv_root)

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            for k, v in self._record_fields.items():
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        f"{self.pv_root}{v.pv_suffix}",
                        k,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        in_alarm = []
        highest_severity = status.OK
        for name in self._record_fields:
            if name not in self._bit_map.keys():
                continue

            value = self._get_cached_value_or_ask(name)
            if value == 0:
                continue

            message = self._bit_map.get(name, None)
            highest_severity = severity = status.WARN

            if self._alarm_state[name] != (severity, message):
                self._write_alarm_to_log(name, severity, message)
            in_alarm.append(f"{message} Alarm")
            self._alarm_state[name] = (severity, message)
        return highest_severity, ", ".join(in_alarm)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = param
        self._cache.put(self._name, cache_key, (severity, message), time_stamp)
        self._cache.put(self._name, "status", self._do_status(), time_stamp)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        # Only check for one PV
        if param != self._record_fields["communication"].cache_key:
            return

        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.ERROR, "communication failure"),
                time.time(),
            )

    def _get_cached_value_or_ask(self, name):
        def _get_pv_value(pv):
            return self._epics_wrapper.get_pv_value(pv)

        pv = f"{self.pv_root}{self._record_fields[name].pv_suffix}"
        return get_from_cache_or(self, name, lambda: _get_pv_value(pv))

    def _write_alarm_to_log(self, name, severity, message):
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error("%s (%s)", name, message)
        elif severity == status.WARN:
            self.log.warning("%s (%s)", name, message)

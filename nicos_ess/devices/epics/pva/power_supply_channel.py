import copy
import threading
import time

from nicos import session
from nicos.core import Attach, Param, Readable, oneof, pvname, status
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class PowerSupplyChannel(EpicsParameters, MappedMoveable):
    parameters = {
        "channel_pv": Param(
            "Root pv for the channel",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "status": Param(
            "State of the channel",
            mandatory=True,
            settable=False,
            userparam=False,
            volatile=True,
        ),
        "control": Param(
            "Power on/off",
            type=oneof("On", "Off"),
            mandatory=True,
            settable=True,
            userparam=False,
        ),
        "control_rb": Param(
            "Power on/off",
            type=str,
            mandatory=True,
            settable=True,
            userparam=False,
        ),
        "voltage_value": Param(
            "Monitored voltage",
        ),
        "voltage_target": Param("Voltage setting", settable=True),
        "current_value": Param(
            "Monitored current",
        ),
        "current_target": Param("Current limit", settable=True),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    _channel_status = (status.OK, "")
    _record_fields = {
        "channel_pv": RecordInfo("channel_pv", "", RecordType.VALUE),
        "status": RecordInfo("status", "STATUS", RecordType.VALUE),
        "voltage_value": RecordInfo("voltage_value", "VMon", RecordType.VALUE),
        "voltage_target": RecordInfo("voltage_target", "V0Set", RecordType.VALUE),
        "current_value": RecordInfo("current_value", "IMon", RecordType.VALUE),
        "current_target": RecordInfo("current_target", "I0Set", RecordType.VALUE),
        "control": RecordInfo("control", "Pw", RecordType.VALUE),
        "control_rb": RecordInfo("control_rb", "Pw-RB", RecordType.VALUE),
    }

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._epics_subscriptions = []
        self._record_fields = copy.deepcopy(self._record_fields)
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check PV exists
        self._epics_wrapper.connect_pv(
            f"{self.pv_root}-{self._record_fields['status']}"
        )

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            for k, v in self._record_fields.items():
                if v.record_type in [RecordType.VALUE, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.channel_pv}{v.pv_suffix}",
                            k,
                            self._value_change_callback,
                            self._connection_change_callback,
                        )
                    )
                if v.record_type in [RecordType.STATUS, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.channel_pv}{v.pv_suffix}",
                            k,
                            self._status_change_callback,
                            self._connection_change_callback,
                        )
                    )

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("voltage_value")

    def doReadVoltageValue(self):
        return self._get_cached_pv_or_ask("voltage_value")

    def doReadVoltageTarget(self):
        return self._get_cached_pv_or_ask("voltage_target")

    def doReadCurrentValue(self):
        return self._get_cached_pv_or_ask("current_value")

    def doReadCurrentTarget(self):
        return self._get_cached_pv_or_ask("current_target")

    def doReadControl(self):
        return self._get_cached_pv_or_ask("control_rb")

    def doWriteVoltageTarget(self, value):
        self._put_pv("voltage_target", value)

    def doWriteCurrentTarget(self, value):
        self._put_pv("current_target", value)

    def doStart(self):
        if self._get_cached_pv_or_ask("control_rb") == "Off":
            self._put_pv("control")

    def doStop(self):
        if self._get_cached_pv_or_ask("control_rb") == "Off":
            self._put_pv("control")

    def doReset(self):
        # Ignore
        pass

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def doReadMapping(self):
        return self._attached_control.mapping

    def _do_status(self):
        pass
        # pseudo code, needs fix
        # with self._lock:
        #     channel_status = self._get_cached_pv_or_ask("status")
        #     if channel_status.val == 0:
        #         return (status.OK, channel_status)
        #     if channel_status.val == 1 or channel_status.val == 2:
        #         return (status.BUSY, channel_status)
        #     else:
        #         return (status.WARN, channel_status)

    def _get_cached_pv_or_ask(self, param, as_string=False):
        return get_from_cache_or(
            self,
            param,
            lambda: self._get_pv(param, as_string),
        )

    def _get_pv(self, param, as_string=False):
        return self._epics_wrapper.get_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", as_string
        )

    def _put_pv(self, param, value):
        self._epics_wrapper.put_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", value
        )

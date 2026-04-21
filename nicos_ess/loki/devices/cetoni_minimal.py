import math
import time

from nicos import session
from nicos.core import POLLER, Attach, HasLimits, Moveable, Override, Param, status
from nicos.devices.abstract import CanReference, MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class CetoniPumpController(EpicsParameters, CanReference, HasLimits, Moveable):
    parameters = {
        "pvroot": Param(
            "The root of the pv",
            type=str,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "flowrate": Param(
            description="Syringe flowrate",
            settable=True,
            volatile=True,
        ),
        "flowrate_unit": Param(
            description="Flowrate unit",
            type=str,
        ),
        "pressure": Param(
            description="Syringe pressure",
            volatile=True,
        ),
        "pressure_unit": Param(
            description="Pressure unit",
            type=str,
        ),
        "innerdiameter": Param(
            description="Syringe diameter",
            volatile="True",
        ),
        "innerdiameter_unit": Param(
            description="Diameter unit",
            type=str,
        ),
        "maxstroke": Param(
            description="Syringe max piston stroke",
            volatile="True",
        ),
        "maxstroke_unit": Param(
            description="Max piston stroke unit",
            type=str,
        ),
        "maxpressure": Param(
            description="Syringe max pressure",
            volatile="True",
        ),
        "maxpressure_unit": Param(
            description="Max pressure unit",
            type=str,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, default=""),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": RecordInfo(
                cache_key="value",
                pv_suffix="FilledVolume",
                record_type=RecordType.BOTH,
            ),
            "writepv": RecordInfo(
                cache_key="target",
                pv_suffix="C_SetFillVol",
                record_type=RecordType.VALUE,
            ),
            "flowrate": RecordInfo(
                cache_key="flowrate",
                pv_suffix="FlowRate",
                record_type=RecordType.VALUE,
            ),
            "flowrate_unit": RecordInfo(
                cache_key="flowrate_unit",
                pv_suffix="FlowRate.EGU",
                record_type=RecordType.VALUE,
            ),
            "pressure": RecordInfo(
                cache_key="pressure",
                pv_suffix="Pressure",
                record_type=RecordType.VALUE,
            ),
            "pressure_unit": RecordInfo(
                cache_key="pressure_unit",
                pv_suffix="Pressure.EGU",
                record_type=RecordType.VALUE,
            ),
            "home": RecordInfo(
                cache_key="home",
                pv_suffix="C_InitPosition",
                record_type=RecordType.BOTH,
            ),
            "innerdiameter": RecordInfo(
                cache_key="innerdiameter",
                pv_suffix="SyrInnerDiam",
                record_type=RecordType.BOTH,
            ),
            "innerdiameter_unit": RecordInfo(
                cache_key="innerdiameter_unit",
                pv_suffix="SyrInnerDiam.EGU",
                record_type=RecordType.BOTH,
            ),
            "maxstroke": RecordInfo(
                cache_key="maxstroke",
                pv_suffix="SyrMaxPstStrk",
                record_type=RecordType.BOTH,
            ),
            "maxstroke_unit": RecordInfo(
                cache_key="maxstroke_unit",
                pv_suffix="SyrMaxPstStrk.EGU",
                record_type=RecordType.BOTH,
            ),
            "maxpressure": RecordInfo(
                cache_key="maxpressure",
                pv_suffix="MaxPressure",
                record_type=RecordType.BOTH,
            ),
            "maxpressure_unit": RecordInfo(
                cache_key="maxpressure_unit",
                pv_suffix="MaxPressure.EGU",
                record_type=RecordType.BOTH,
            ),
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self.connect_pvs()
        self.set_up_subscriptions()

    def connect_pvs(self):
        self._epics_wrapper.connect_pv(self._get_pv_name("readpv"))
        self._epics_wrapper.connect_pv(self._get_pv_name("writepv"))
        self._epics_wrapper.connect_pv(self._get_pv_name("flowrate"))
        # self._epics_wrapper.connect_pv(self._get_pv_name("flowrate_unit"))
        self._epics_wrapper.connect_pv(self._get_pv_name("pressure"))
        # self._epics_wrapper.connect_pv(self._get_pv_name("pressure_unit"))
        self._epics_wrapper.connect_pv(self._get_pv_name("home"))
        self._epics_wrapper.connect_pv(self._get_pv_name("innerdiameter"))
        self._epics_wrapper.connect_pv(self._get_pv_name("maxstroke"))
        self._epics_wrapper.connect_pv(self._get_pv_name("maxpressure"))

    def set_up_subscriptions(self):
        self._epics_subscriptions = []
        # if session.sessiontype == POLLER and self.monitor:
        for key, record_info in self._record_fields.items():
            if record_info.record_type in [RecordType.VALUE, RecordType.BOTH]:
                value_subscription = self._epics_wrapper.subscribe(
                    pvname=self._get_pv_name(key),
                    pvparam=record_info.cache_key,
                    change_callback=self._value_change_callback,
                    connection_callback=self._connection_change_callback,
                )
                self._epics_subscriptions.append(value_subscription)
            if record_info.record_type in [RecordType.STATUS, RecordType.BOTH]:
                status_subscription = self._epics_wrapper.subscribe(
                    pvname=self._get_pv_name(key),
                    pvparam=record_info.cache_key,
                    change_callback=self._status_change_callback,
                    connection_callback=self._connection_change_callback,
                )
                self._epics_subscriptions.append(status_subscription)

    def _get_pv_name(self, pvparam):
        return f"{self.pvroot}{self._record_fields[pvparam].pv_suffix}"

    def _get_cached_pv_or_ask(
        self, key: str, maxage: float = 5, as_string: bool = False
    ):
        if math.isclose(maxage, 0.0):
            return self._read_pv(key, as_string)
        else:
            return get_from_cache_or(
                self,
                self._record_fields[key].cache_key,
                lambda: self._epics_wrapper.get_pv_value(
                    self._get_pv_name(key), as_string
                ),
            )

    def _read_pv(self, key, as_string=False):
        return self._epics_wrapper.get_pv_value(
            self._get_pv_name(key), as_string=as_string
        )

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(name, value)

    def doRead(self, maxage):
        return self._get_cached_pv_or_ask("readpv")

    def doReadPressure(self):
        return self._get_cached_pv_or_ask("pressure", maxage=0.0)

    def doReadPressure_Unit(self):
        return self._get_cached_pv_or_ask("pressure_unit")

    def doReadFlowrate(self):
        return self._get_cached_pv_or_ask("flowrate")

    def doReadFlowrate_Unit(self):
        return self._get_cached_pv_or_ask("flowrate_unit")

    def doWriteFlowrate(self, target):
        self._set_pv(self._get_pv_name("flowrate"), target)

    def doReference(self):
        self._set_pv(self._get_pv_name("home"), 1)

    def doReadInnerdiameter(self):
        return self._get_cached_pv_or_ask("innerdiameter", maxage=0.0)

    def doReadInnerdiameter_Unit(self):
        return self._get_cached_pv_or_ask("innerdiameter_unit")

    def doReadMaxstroke(self):
        return self._get_cached_pv_or_ask("maxstroke", maxage=0.0)

    def doReadMaxstroke_Unit(self):
        return self._get_cached_pv_or_ask("maxstroke_unit")

    def doReadMaxpressure(self):
        return self._get_cached_pv_or_ask("maxpressure", maxage=0.0)

    def doReadMaxpressure_Unit(self):
        return self._get_cached_pv_or_ask("maxpressure_unit")

    def doStart(self, target):
        self._set_pv(self._get_pv_name("writepv"), target)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self._get_pv_name("readpv"):
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        self._cache.put(self._name, param, value, time_stamp)
        self._cache.put(self._name, "unit", units, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self._get_pv_name("readpv"):
            # Unexpected updates ignored
            return
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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

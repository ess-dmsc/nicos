import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    HasLimits,
    Moveable,
    Override,
    Param,
    oneof,
    pvname,
    status,
    usermethod,
)
from nicos.devices.abstract import CanReference, MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class CetoniPumpController(EpicsParameters, CanReference, MappedMoveable):
    """
    A device for controlling a Cetoni syringe pump

     The device:
        - can show the current filled volume in the syringe
        - can control the absolute filled volume (aspirate or dispense to target vol)
        - can control a relative volume (aspirate or dispense a specific vol)
        - can fill the syringe
        - can empty the syringe
        - can stop pumping
        - can home the syringe
    """

    parameters = {
        "pvroot": Param(
            "The root of the pv",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, default=""),
        "mapping": Override(mandatory=False, internal=True),
    }

    attached_devices = {
        "abs_vol": Attach("Target volume", Moveable),
        "rel_vol": Attach("Target relative volume", Moveable),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": RecordInfo(
                cache_key="value",
                pv_suffix="FilledVolume",
                record_type=RecordType.BOTH,
            ),
            "absvol_sp": RecordInfo(
                cache_key="absvol_sp",
                pv_suffix="C_SetFillVol",
                record_type=RecordType.VALUE,
            ),
            "fill_syringe": RecordInfo(
                cache_key="fill_syringe",
                pv_suffix="C_FillSyringe",
                record_type=RecordType.VALUE,
            ),
            "empty_syringe": RecordInfo(
                cache_key="empty_syringe",
                pv_suffix="C_EmptySyringe",
                record_type=RecordType.VALUE,
            ),
            "stop_pump": RecordInfo(
                cache_key="stop_pump",
                pv_suffix="C_Stop",
                record_type=RecordType.VALUE,
            ),
            "home": RecordInfo(
                cache_key="home",
                pv_suffix="C_InitPosition",
                record_type=RecordType.BOTH,
            ),
            # "pressure": RecordInfo(cache_key="filled_volume", pv_suffix="Pressure")
            # "ispumping": RecordInfo(cache_key="", pv_suffix="IsPumping", record_type=RecordType.STATUS),
            # "isfault": RecordInfo(cache_key="", pv_suffix="FaultState", record_type=RecordType.STATUS),
            # "ishomed": RecordInfo(cache_key="", pv_suffix="RefPosInitd", record_type=RecordType.STATUS),
            "maxvol": RecordInfo(
                cache_key="maxvol", pv_suffix="MaxVol", record_type=RecordType.VALUE
            ),
            # "innerdiameter_rb": RecordInfo(cache_key="filled_volume", pv_suffix="SyrInnerDiam-RB",
            # "innerdiameter_sp": RecordInfo(cache_key="filled_volume", pv_suffix="SyrInnerDiam-SP",
            # "maxstroke_rb": RecordInfo(cache_key="filled_volume", pv_suffix="SyrMaxPstStrk-RB",
            # "maxstroke_sp": RecordInfo(cache_key="filled_volume", pv_suffix="SyrMaxPstStrk-SP",
            # "maxpressure_rb": RecordInfo(cache_key="filled_volume", pv_suffix="MaxPressure-RB",
            # "maxpressure_sp": RecordInfo(cache_key="filled_volume", pv_suffix="MaxPressure-SP",
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self.connect_pvs()

        self._commands = {
            "pump_to_abs_volume": self.pump_to_abs_volume,
            "pump_relative_volume": self.pump_relative_volume,
            "fill_syringe": self.fill_syringe,
            "empty_syringe": self.empty_syringe,
            "stop": self.stop_pump,
        }

        self.set_limits_on_attached_devices()

    def set_limits_on_attached_devices(self):
        total_vol = self._read_pv("maxvol")
        print(total_vol)
        self._attached_abs_vol.userlimits = 0, total_vol

    def doInit(self, mode):
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())
        self.set_up_subscriptions()

    def connect_pvs(self):
        self._epics_wrapper.connect_pv(self._get_pv_name("readpv"))

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

    def _get_cached_pv_or_ask(self, key: str, as_string: bool = False):
        return get_from_cache_or(
            self,
            self._record_fields[key].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self._get_pv_name(key), as_string),
        )

    def _get_pv_name(self, pvparam):
        return f"{self.pvroot}{self._record_fields[pvparam].pv_suffix}"

    def _read_pv(self, name, as_string=False):
        return self._epics_wrapper.get_pv_value(name, as_string=as_string)

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(name, value)

    @usermethod
    def pump_to_abs_volume(self, volume=None):
        if self._mode == SIMULATION:
            return
        if not volume:
            volume = self._attached_abs_vol.read()
        self._set_pv("absvol_sp", volume)

    @usermethod
    def pump_relative_volume(self, volume=None):
        if self._mode == SIMULATION:
            return
        if not volume:
            volume = self._attached_rel_vol.read()
        ### TODO

    @usermethod
    def fill_syringe(self):
        if self._mode == SIMULATION:
            return
        self._set_pv("fill_syringe", 1)

    @usermethod
    def empty_syringe(self):
        if self._mode == SIMULATION:
            return
        self._set_pv("empty_syringe", 1)

    @usermethod
    def stop_pump(self):
        if self._mode == SIMULATION:
            return
        self._set_pv("stop_pump", 1)

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("readpv")

    def doStart(self, target):
        self._cache.put(self, "status", (status.BUSY, "Pumping"), time.time())
        if target in self._commands:
            self._commands[target]()

    def doReference(self):
        self._set_pv(self._get_pv_name("home"), 1)

    def doStop(self):
        self.stop_pump()

    def doStatus(self, maxage=0):
        # return get_from_cache_or(self, "status", self._do_status)
        return self._do_status(maxage=0)

    def _do_status(self, maxage=0):
        fault = self._get_cached_pv_or_ask("isfault")
        print(f"fault: {fault}")
        if fault:
            return status.ERROR, fault
        homed = self._get_cached_pv_or_ask("ishomed")
        print(f"homed: {homed}")
        if not homed:
            return status.ERROR, "Not homed"
        busy = self._get_cached_pv_or_ask("ispumping")
        print(f"busy: {busy}")
        if busy:
            return status.BUSY, "Pumping"
        return status.OK

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


class CetoniPumpStepper(EpicsParameters, MappedMoveable):
    """
    A device for controlling a Cetoni syringe pump in a stepwise manner

     The device:
        - can control stepwise aspirating or dispensing a set volume

    """

    parameters = {
        "aspiratepv": Param(
            "pv to aspirate stepwise volume",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "dispensepv": Param(
            "pv to dispense stepwise volume",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {"mapping": Override(mandatory=False, internal=True)}

    def doInit(self, mode):
        self._setROParam("mapping", {"Dispense step": 0, "Aspirate step": 1})
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self.mapping.keys())

    def doStart(self, value):
        if value == "Dispense step":
            self._epics_wrapper.put_pv_value(self.dispensepv, 1)
        elif value == "Aspirate step":
            self._epics_wrapper.put_pv_value(self.aspiratepv, 1)

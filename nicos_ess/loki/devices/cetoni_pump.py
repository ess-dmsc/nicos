import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    HasLimits,
    Moveable,
    Override,
    Param,
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


class CetoniPumpController(EpicsParameters, CanReference, HasLimits, Moveable):
    """
    A device for controlling a Cetoni syringe pump

     The device:
      - exposes the mapped commands: start / stop / purge / pause / resume
      - reads the current textual *state* from the attached `status` device
      - reads error text from `message_pv` (non-empty => ERROR)
      - writes to start/stop/purge/pause PVs as before
    """

    parameters = {
        "pvroot": Param(
            "The root of the PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, default=""),
        "abslimits": Override(volatile=True, mandatory=False),
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
            # "pressure": RecordInfo(cache_key="filled_volume", pv_suffix="Pressure",
            "ispumping": RecordInfo(
                cache_key="",
                pv_suffix="IsPumping",
                record_type=RecordType.STATUS,
            ),
            "isfault": RecordInfo(
                cache_key="",
                pv_suffix="FaultState",
                record_type=RecordType.STATUS,
            ),
            "ishomed": RecordInfo(
                cache_key="",
                pv_suffix="RefPosInitd",
                record_type=RecordType.STATUS,
            ),
            "maxvol": RecordInfo(
                cache_key="",
                pv_suffix="MaxVol",
                record_type=RecordType.VALUE,
            ),
            # "flowrate_rb": RecordInfo(cache_key="filled_volume", pv_suffix="FlowRate-RB",
            # "flowrate_sp": RecordInfo(cache_key="filled_volume", pv_suffix="FlowRate-RB",
            # "aspiratestep": RecordInfo(cache_key="filled_volume", pv_suffix="C_AspirateStep",
            # "dispensestep": RecordInfo(cache_key="filled_volume", pv_suffix="C_DispenseStep",
            # "innerdiameter_rb": RecordInfo(cache_key="filled_volume", pv_suffix="SyrInnerDiam-RB",
            # "innerdiameter_sp": RecordInfo(cache_key="filled_volume", pv_suffix="SyrInnerDiam-SP",
            # "maxstroke_rb": RecordInfo(cache_key="filled_volume", pv_suffix="SyrMaxPstStrk-RB",
            # "maxstroke_sp": RecordInfo(cache_key="filled_volume", pv_suffix="SyrMaxPstStrk-SP",
            # "maxpressure_rb": RecordInfo(cache_key="filled_volume", pv_suffix="MaxPressure-RB",
            # "maxpressure_sp": RecordInfo(cache_key="filled_volume", pv_suffix="MaxPressure-SP",
            # "stepsize_rb": RecordInfo(cache_key="filled_volume", pv_suffix="StepSize-RB",
            # "stepsize_sp": RecordInfo(cache_key="filled_volume", pv_suffix="StepSize-SP",
            # "home": RecordInfo(cache_key="filled_volume", pv_suffix=" InitPosition",
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self.check_connection_to_pvs()

    def doInit(self, mode):
        self.set_up_subscriptions()

    def check_connection_to_pvs(self):
        self._epics_wrapper.connect_pv(self._get_pv_name("readpv"))
        self._epics_wrapper.connect_pv(self._get_pv_name("writepv"))

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

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("readpv")

    def doStart(self, value):
        self._cache.put(self, "status", (status.BUSY, "Moving"), time.time())
        self._set_pv(self._get_pv_name("writepv"), value)

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

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

    def doReference(self):
        self._set_pv(self._get_pv_name("reference"), 1)

    def doReadAbslimits(self):
        max_volume = self._get_cached_pv_or_ask("maxvol")
        return 0, max_volume

    def doWriteInnerdiameter(self, value):
        self._set_pv(self._get_pv_name("innerdiameter_sp"), value)
        return value

    def doWriteMaxStroke(self, value):
        self._set_pv(self._get_pv_name("maxstroke_sp"), value)
        return value

    def doWritemaxpressure(self, value):
        self._set_pv(self._get_pv_name("maxpressure_sp"), value)
        return value

    def doWriteStepsize(self, value):
        self._set_pv(self._get_pv_name("stepsize_sp"), value)
        return value

    @usermethod
    def aspirate_step(self):
        self._set_pv(self._get_pv_name("aspiratestep"), 1)

    @usermethod
    def dispense_step(self):
        self._set_pv(self._get_pv_name("dispensestep"), 1)

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

import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
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


class CetoniPumpController(EpicsParameters, CanReference, Moveable):
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
        # "innerdiameter": Param(
        #     "The inner diameter of the syringe",
        #     type=float,
        # ),
        # "maxstroke": Param(
        #     "The maximum stroke length of the piston",
        #     type=float,
        # ),
        # "maxpressure": Param(
        #     "The maximum allowed pressure",
        #     type=float,
        # ),
        # "stepsize": Param(
        #     "Define step size for quick aspiration/dispensing of defined volume",
        #     type=float,
        # ),
    }

    parameter_overrides = {
        # readpv and writepv are determined automatically from the base PV
        "readpv": Override(mandatory=False, userparam=False, settable=False),
        "writepv": Override(mandatory=False, userparam=False, settable=False),
        "unit": Override(mandatory=False, settable=False, default=""),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": RecordInfo(
                cache_key="filled_volume_rbv",
                pv_suffix="FilledVolume",
                record_type=RecordType.VALUE,
            ),
            "writepv": RecordInfo(
                cache_key="filled_volume_sp",
                pv_suffix="C_SetFillVol",
                record_type=RecordType.VALUE,
            ),
            # "pressure": RecordInfo(cache_key="filled_volume", pv_suffix="Pressure",
            # "ispumping": RecordInfo(cache_key="filled_volume", pv_suffix="IsPumping",
            # "isfault": RecordInfo(cache_key="filled_volume", pv_suffix="FaultState",
            # "ishomed": RecordInfo(cache_key="filled_volume", pv_suffix="RefPosInitd",
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

    def doInit(self, mode):
        self.set_up_subscriptions()

    def set_up_subscriptions(self):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

        if session.sessiontype == POLLER and self.monitor:
            value_subscription = self._epics_wrapper.subscribe(
                pvname=self._get_pv_name("readpv"),
                pvparam=self._record_fields["readpv"].cache_key,
                change_callback=self._value_change_callback,
                connection_callback=self._connection_change_callback,
            )
            status_subscription = self._epics_wrapper.subscribe(
                pvname=self._get_pv_name("readpv"),
                pvparam=self._record_fields["readpv"].cache_key,
                change_callback=self._status_change_callback,
                connection_callback=self._connection_change_callback,
            )
            self._epics_subscriptions = [value_subscription, status_subscription]

    def _get_cached_pv_or_ask(self, key: str, as_string: bool = False):
        return get_from_cache_or(
            self,
            self._record_fields[key].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self._pv(key), as_string),
        )

    def _get_pv_name(self, pvparam):
        return f"{self.pvroot}{self._record_fields[pvparam]}"

    def _read_pv(self, name, as_string=False):
        return self._epics_wrapper.get_pv_value(name, as_string=as_string)

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(name, value)

    def doRead(self, maxage=0):
        # return self._epics_wrapper.get_pv_value(self._get_pv_name("readpv"))
        return self._get_cached_pv_or_ask("readpv")

    def doStart(self, value):
        self._set_pv(self._get_pv_name("writepv"), value)

    def doStatus(self, maxage=0):
        fault = self._read_pv(self._get_pv_name("isfault"))
        if fault:
            return status.ERROR, fault

        homed = self._read_pv(self._get_pv_name("ishomed"))
        if not homed:
            return status.ERROR, "Not homed"

        busy = self._read_pv(self._get_pv_name("ispumping"))
        if busy:
            return status.BUSY, "Pumping"

        return status.OK

    def doReference(self):
        self._set_pv(self._get_pv_name("reference"), 1)

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

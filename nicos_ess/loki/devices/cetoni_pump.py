import time

from nicos import session
from nicos.core import (
    HasLimits,
    Moveable,
    Param,
    Override,
    SIMULATION,
    status,
    POLLER,
    usermethod,
    CanDisable,
    oneof,
    Attach,
    PositionError,
    ConfigurationError,
)
from nicos.devices.abstract import CanReference, MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    create_wrapper,
    RecordInfo,
    RecordType,
    get_from_cache_or,
    PvReadOrWrite,
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
        "flowrate_max": Param(
            description="Max flowrate",
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
        "pressure_max": Param(
            description="Syringe max pressure",
            volatile=True,
        ),
        "pressure_unit": Param(
            description="Pressure unit",
            type=str,
        ),
        "innerdiameter": Param(
            description="Syringe diameter",
            volatile=True,
        ),
        "innerdiameter_unit": Param(
            description="Diameter unit",
            type=str,
        ),
        "stroke_max": Param(
            description="Syringe max piston stroke",
            volatile=True,
        ),
        "stroke_unit": Param(
            description="Piston stroke unit",
            type=str,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, default=""),
        "abslimits": Override(volatile=True, mandatory=False),
        "userlimits": Override(volatile=True, chatty=False),
    }

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._record_fields = self._get_record_fields()
        if mode == SIMULATION:
            return
        self._epics_wrapper.connect_pv(self._get_pv_name("value"))

    def doInit(self, mode):
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._set_up_subscriptions()

    def _get_record_fields(self):
        return {
            "value": RecordInfo(
                cache_key="value",
                pv_suffix="FilledVolume",
                record_type=RecordType.BOTH,
            ),
            "target": RecordInfo(
                cache_key="target",
                pv_suffix="C_SetFillVol",
                record_type=RecordType.VALUE,
            ),
            "flowrate": RecordInfo(
                cache_key="flowrate",
                pv_suffix="FlowRate",
                record_type=RecordType.VALUE,
            ),
            "flowrate_max": RecordInfo(
                cache_key="flowrate_max",
                pv_suffix="MaxFlowRate",
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
            "pressure_max": RecordInfo(
                cache_key="pressure_max",
                pv_suffix="MaxPressure",
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
                record_type=RecordType.OTHER,
            ),
            "innerdiameter": RecordInfo(
                cache_key="innerdiameter",
                pv_suffix="SyrInnerDiam",
                record_type=RecordType.VALUE,
            ),
            "innerdiameter_unit": RecordInfo(
                cache_key="innerdiameter_unit",
                pv_suffix="SyrInnerDiam.EGU",
                record_type=RecordType.VALUE,
            ),
            "stroke_max": RecordInfo(
                cache_key="stroke_max",
                pv_suffix="SyrMaxPstStrk",
                record_type=RecordType.VALUE,
            ),
            "stroke_unit": RecordInfo(
                cache_key="stroke_unit",
                pv_suffix="SyrMaxPstStrk.EGU",
                record_type=RecordType.VALUE,
            ),
            "max_vol": RecordInfo(
                cache_key="max_vol",
                pv_suffix="MaxVol",
                record_type=RecordType.VALUE,
            ),
            "stop": RecordInfo(
                cache_key="stop",
                pv_suffix="C_Stop",
                record_type=RecordType.OTHER,
            ),
            "fill_syringe": RecordInfo(
                cache_key="fill_syringe",
                pv_suffix="C_FillSyringe",
                record_type=RecordType.OTHER,
            ),
            "empty_syringe": RecordInfo(
                cache_key="empty_syringe",
                pv_suffix="C_EmptySyringe",
                record_type=RecordType.OTHER,
            ),
            "generate_flow": RecordInfo(
                cache_key="generate_flow",
                pv_suffix="C_GenerateFlow",
                record_type=RecordType.OTHER,
            ),
            "is_pumping": RecordInfo(
                cache_key="is_pumping",
                pv_suffix="IsPumping",
                record_type=RecordType.STATUS,
            ),
            "is_homed": RecordInfo(
                cache_key="is_homed",
                pv_suffix="RefPosInitd",
                record_type=RecordType.STATUS,
            ),
            "is_fault": RecordInfo(
                cache_key="is_fault",
                pv_suffix="FaultState",
                record_type=RecordType.STATUS,
            ),
            "reset_fault": RecordInfo(
                cache_key="reset_fault",
                pv_suffix="C_ResetFault",
                record_type=RecordType.OTHER,
            ),
        }

    def _set_up_subscriptions(self):
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

    def _get_pv_name(self, pv_param):
        return f"{self.pvroot}{self._record_fields[pv_param].pv_suffix}"

    def _get_pv_val(self, pv_param, as_string=False):
        pv_name = self._get_pv_name(pv_param)
        pv_val = self._epics_wrapper.get_pv_value(pv_name, as_string)
        return pv_val

    def _put_pv_val(self, pv_param, target):
        pv_name = self._get_pv_name(pv_param)
        self._epics_wrapper.put_pv_value(pv_name, target)

    def _get_cache_key(self, pv_param):
        return self._record_fields[pv_param].cache_key or pv_param

    def _get_cached_pv_or_ask(self, pv_param, as_string=False):
        """
        Gets the PV value from the cache if possible, else get it from the device.
        """
        cache_key = self._get_cache_key(pv_param)
        return get_from_cache_or(
            self,
            cache_key,
            lambda: self._get_pv_val(pv_param, as_string),
        )

    def doReadAbslimits(self):
        high_limit = self._get_cached_pv_or_ask("max_vol")
        return 0, high_limit

    def doRead(self, maxage):
        return self._get_cached_pv_or_ask("value")

    def doReadPressure(self):
        return self._get_cached_pv_or_ask("pressure")

    def doReadPressure_Max(self):
        return self._get_cached_pv_or_ask("pressure_max")

    def doReadPressure_Unit(self):
        return self._get_cached_pv_or_ask("pressure_unit")

    def doReadFlowrate(self):
        return self._get_cached_pv_or_ask("flowrate")

    def doReadFlowrate_Max(self):
        return self._get_cached_pv_or_ask("flowrate_max")

    def doReadFlowrate_Unit(self):
        return self._get_cached_pv_or_ask("flowrate_unit")

    def doWriteFlowrate(self, target):
        self._put_pv_val("flowrate", target)

    def doReadInnerdiameter(self):
        return self._get_cached_pv_or_ask("innerdiameter")

    def doReadInnerdiameter_Unit(self):
        return self._get_cached_pv_or_ask("innerdiameter_unit")

    def doReadStroke_Max(self):
        return self._get_cached_pv_or_ask("stroke_max")

    def doReadStroke_Unit(self):
        return self._get_cached_pv_or_ask("stroke_unit")

    def doReference(self):
        self._put_pv_val("home", 1)

    def doReset(self):
        self._put_pv_val("reset_fault", 1)
        self._cache.invalidate(self, "is_fault")

    def doStart(self, target):
        self._put_pv_val("target", target)

    def doStop(self):
        self._put_pv_val("stop", 1)

    @usermethod
    def fill_syringe(self):
        if self._mode == SIMULATION:
            return
        self._put_pv_val("fill_syringe", 1)

    @usermethod
    def empty_syringe(self):
        if self._mode == SIMULATION:
            return
        self._put_pv_val("empty_syringe", 1)

    @usermethod
    def generate_flow(self, target):
        """
        Generate constant flow with target flow rate

        Positive value = dispense
        Negative value = aspirate
        """
        if self._mode == SIMULATION:
            return
        self._put_pv_val("generate_flow", target)

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        is_in_fault = self._get_cached_pv_or_ask("is_fault")
        if is_in_fault:
            return status.ERROR, "In faulty state"

        is_homed = self._get_cached_pv_or_ask("is_homed")
        if not is_homed:
            return status.WARN, "Not homed"

        is_pumping = self._get_cached_pv_or_ask("is_pumping")
        if is_pumping:
            return status.BUSY, "Pumping"
        else:
            return status.OK, "idle"

    def _value_change_callback(
        self,
        pv_name,
        pv_param,
        value,
        units,
        limits,
        severity,
        message,
        **kwargs,
    ):
        time_stamp = time.time()
        self._cache.put(dev=self._name, key=pv_param, value=value, time=time_stamp)

    def _status_change_callback(
        self,
        pv_name,
        pv_param,
        value,
        units,
        limits,
        severity,
        message,
        **kwargs,
    ):
        time_stamp = time.time()
        if pv_param == "value":
            self._cache.put(
                dev=self._name,
                key="value_status",
                value=(severity, message),
                time=time_stamp,
            )
        else:
            self._cache.put(dev=self._name, key=pv_param, value=value, time=time_stamp)
        self._cache.put(
            dev=self._name, key="status", value=self._do_status(), time=time_stamp
        )

    def _connection_change_callback(
        self,
        pv_name,
        pv_param,
        is_connected,
        **kwargs,
    ):
        if is_connected:
            self.log.debug("%s connected!", pv_name)
        else:
            self.log.warning("%s disconnected!", pv_name)
            self._cache.put(
                dev=self._name,
                key="status",
                value=(status.ERROR, "communication failure"),
                time=time.time(),
            )


class CetoniPumpLinkedMode(EpicsParameters, CanDisable, MappedMoveable):
    parameters = {
        "pvroot": Param(
            "The root of the pv",
            type=str,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "flowrate": Param(
            description="Linked syringe flowrate",
            settable=True,
            volatile=True,
        ),
        "flowrate_max": Param(
            description="Max flowrate",
            volatile=True,
        ),
        "flowrate_unit": Param(
            description="Flowrate unit",
            type=str,
        ),
        "dosing_time": Param(
            description="Number of seconds to run the linked mode in time limited flow",
            type=int,
            unit="s",
            settable=True,
        ),
        "total_vol": Param(
            description="Total volume",
            volatile=True,
        ),
        "first_fill_syringe": Param(
            description="The direction of flow will fill this syringe first, options=[SP1, SP2]",
            volatile=True,
            settable=True,
            type=str,
        ),
    }

    parameter_overrides = {
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    attached_devices = {
        "sp1": Attach("controller for syringe SP1", CetoniPumpController),
        "sp2": Attach("controller for syringe SP2", CetoniPumpController),
    }

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._record_fields = self._get_record_fields()
        if mode == SIMULATION:
            return
        self._epics_wrapper.connect_pv(self._get_pv_name("enable"))

    def doInit(self, mode):
        self._setROParam("mapping", {"Continuous flow": 0, "Time limited flow": 1})
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._set_up_subscriptions()

    def _get_record_fields(self):
        return {
            "value": RecordInfo(
                cache_key="value",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdStopMode-SP",
                record_type=RecordType.VALUE,
            ),
            "target": RecordInfo(
                cache_key="target",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdStopMode-SP",
                record_type=RecordType.VALUE,
            ),
            "flowrate": RecordInfo(
                cache_key="flowrate",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdFlowRate-SP",
                record_type=RecordType.VALUE,
            ),
            "flowrate_max": RecordInfo(
                cache_key="flowrate_max",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdMaxFlowRate",
                record_type=RecordType.VALUE,
            ),
            "flowrate_unit": RecordInfo(
                cache_key="flowrate_unit",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdFlowRate-SP.EGU",
                record_type=RecordType.VALUE,
            ),
            "dosing_time": RecordInfo(
                cache_key="dosing_time",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdMaxDosingTime-SP",
                record_type=RecordType.VALUE,
            ),
            "total_vol": RecordInfo(
                cache_key="total_vol",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdTotalVol",
                record_type=RecordType.VALUE,
            ),
            "first_fill_syringe": RecordInfo(
                cache_key="first_fill_syringe",
                pv_suffix="B02-CSLab:SE-Pumps:FillingSyringeIdx-S",
                record_type=RecordType.VALUE,
            ),
            "start": RecordInfo(
                cache_key="start",
                pv_suffix="B02-CSLab:SE-Pumps:C_LnkdStart",
                record_type=RecordType.OTHER,
            ),
            "stop": RecordInfo(
                cache_key="stop",
                pv_suffix="B02-CSLab:SE-Pumps:SP1StopAllPumps",
                record_type=RecordType.OTHER,
            ),
            "enable": RecordInfo(
                cache_key="enable",
                pv_suffix="B02-CSLab:SE-Pumps:C_LnkdEnable",
                record_type=RecordType.STATUS,
            ),
            "is_enabled": RecordInfo(
                cache_key="is_enabled",
                pv_suffix="B02-CSLab:SE-Pumps:LinkedSyringesEnbld",
                record_type=RecordType.STATUS,
            ),
            "is_pumping": RecordInfo(
                cache_key="is_pumping",
                pv_suffix="B02-CSLab:SE-Pumps:LnkdIsPumping",
                record_type=RecordType.STATUS,
            ),
        }

    def _set_up_subscriptions(self):
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

    def _get_pv_name(self, pv_param):
        return f"{self.pvroot}{self._record_fields[pv_param].pv_suffix}"

    def _get_pv_val(self, pv_param, as_string=False):
        pv_name = self._get_pv_name(pv_param)
        pv_val = self._epics_wrapper.get_pv_value(pv_name, as_string)
        return pv_val

    def _put_pv_val(self, pv_param, target):
        pv_name = self._get_pv_name(pv_param)
        self._epics_wrapper.put_pv_value(pv_name, target)

    def _get_cache_key(self, pv_param):
        return self._record_fields[pv_param].cache_key or pv_param

    def _get_cached_pv_or_ask(self, pv_param, as_string=False):
        """
        Gets the PV value from the cache if possible, else get it from the device.
        """
        cache_key = self._get_cache_key(pv_param)
        return get_from_cache_or(
            self,
            cache_key,
            lambda: self._get_pv_val(pv_param, as_string),
        )

    def _get_mapped_choices(self, pv_name):
        choices = self._epics_wrapper.get_value_choices(pv_name)
        if not choices:
            raise ConfigurationError(self, f"PV {pv_name} has no value choices")
        return choices

    def _target_valid(self, pv_name, value):
        choices = self._get_mapped_choices(pv_name)
        if not value in choices:
            raise ConfigurationError(self, f"Invalid choice for {pv_name}: {value}")
        return True

    def _readRaw(self, maxage=0):
        return self._get_cached_pv_or_ask("value")

    def _startRaw(self, target):
        print("target:", target)
        self._put_pv_val("target", target)

    def doReadFlowrate(self):
        return self._get_cached_pv_or_ask("flowrate")

    def doReadFlowrate_Max(self):
        return self._get_cached_pv_or_ask("flowrate_max")

    def doReadFlowrate_Unit(self):
        return self._get_cached_pv_or_ask("flowrate_unit")

    def doWriteFlowrate(self, target):
        self._put_pv_val("flowrate", target)

    def doReadDosing_Time(self):
        return self._get_cached_pv_or_ask("dosing_time")

    def doWriteDosing_Time(self, target):
        self._put_pv_val("dosing_time", target)

    def doReadTotal_Vol(self):
        return self._get_cached_pv_or_ask("total_vol")

    def doReadFirst_Fill_Syringe(self):
        return self._get_cached_pv_or_ask("first_fill_syringe", as_string=True)

    def doWriteFirst_Fill_Syringe(self, target):
        pv_name = self._get_pv_name("first_fill_syringe")
        if self._target_valid(pv_name, target):
            self._put_pv_val("first_fill_syringe", target)

    def doEnable(self, on=False):
        if on:
            self._put_pv_val("enable", 1)
        else:
            self._put_pv_val("enable", 0)
        self._cache.invalidate(self, "is_enabled")

    def doStart(self, target):
        # TODO:
        #  set mode then start B02-CSLab:SE-Pumps:LnkdStopMode-SP
        #
        # self._put_pv_val("start", 1)
        pass

    def doStop(self):
        self._put_pv_val("stop", 1)

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        is_sp1_fault = self._attached_sp1._get_cached_pv_or_ask("is_fault")
        if is_sp1_fault:
            return status.ERROR, "SP1 in faulty state"

        is_sp2_fault = self._attached_sp2._get_cached_pv_or_ask("is_fault")
        if is_sp2_fault:
            return status.ERROR, "SP2 in faulty state"

        is_pumping = self._get_cached_pv_or_ask("is_pumping")
        if is_pumping:
            # TODO: pumping continuous or pumping time
            return status.BUSY, "Pumping"

        is_enabled = self._get_cached_pv_or_ask("is_enabled")
        if is_enabled:
            return status.OK, "Enabled"
        else:
            return status.WARN, "Not enabled"

    def _value_change_callback(
        self,
        pv_name,
        pv_param,
        value,
        units,
        limits,
        severity,
        message,
        **kwargs,
    ):
        time_stamp = time.time()
        self._cache.put(dev=self._name, key=pv_param, value=value, time=time_stamp)

    def _status_change_callback(
        self,
        pv_name,
        pv_param,
        value,
        units,
        limits,
        severity,
        message,
        **kwargs,
    ):
        time_stamp = time.time()
        if pv_param == "value":
            self._cache.put(
                dev=self._name,
                key="value_status",
                value=(severity, message),
                time=time_stamp,
            )
        else:
            self._cache.put(dev=self._name, key=pv_param, value=value, time=time_stamp)
        self._cache.put(
            dev=self._name, key="status", value=self._do_status(), time=time_stamp
        )

    def _connection_change_callback(
        self,
        pv_name,
        pv_param,
        is_connected,
        **kwargs,
    ):
        if is_connected:
            self.log.debug("%s connected!", pv_name)
        else:
            self.log.warning("%s disconnected!", pv_name)
            self._cache.put(
                dev=self._name,
                key="status",
                value=(status.ERROR, "communication failure"),
                time=time.time(),
            )

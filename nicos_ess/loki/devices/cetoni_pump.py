from time import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    CanDisable,
    ConfigurationError,
    HasLimits,
    Moveable,
    Override,
    Param,
    status,
    usermethod,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)
from nicos_ess.devices.mixins import CanReferenceWithWarning


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
        "linked_pumping_mode": Attach(
            "Device to set the linked pumping mode", MappedMoveable
        )
    }

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._record_fields = self._get_record_fields()
        if mode == SIMULATION:
            return
        self._epics_wrapper.connect_pv(self._get_pv_name("enable"))

    def doInit(self, mode):
        if mode != SIMULATION:
            self._set_mapping()
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._set_up_subscriptions()
        MappedMoveable.doInit(self, mode)

    def _get_record_fields(self):
        return {
            "flowrate": RecordInfo(
                cache_key="flowrate",
                pv_suffix="FlowRate-SP",
                record_type=RecordType.VALUE,
            ),
            "flowrate_max": RecordInfo(
                cache_key="flowrate_max",
                pv_suffix="MaxFlowRate",
                record_type=RecordType.VALUE,
            ),
            "flowrate_unit": RecordInfo(
                cache_key="flowrate_unit",
                pv_suffix="FlowRate-SP.EGU",
                record_type=RecordType.VALUE,
            ),
            "total_vol": RecordInfo(
                cache_key="total_vol",
                pv_suffix="TotalVol",
                record_type=RecordType.VALUE,
            ),
            "first_fill_syringe": RecordInfo(
                cache_key="first_fill_syringe",
                pv_suffix="FillingSyringeIdx-SP",
                record_type=RecordType.VALUE,
            ),
            "start": RecordInfo(
                cache_key="start",
                pv_suffix="Start-Cmd",
                record_type=RecordType.OTHER,
            ),
            "stop": RecordInfo(
                cache_key="stop",
                pv_suffix="StopAllPumps-Cmd",
                record_type=RecordType.OTHER,
            ),
            "enable": RecordInfo(
                cache_key="enable",
                pv_suffix="Enable-Cmd",
                record_type=RecordType.OTHER,
            ),
            "is_disabled": RecordInfo(
                cache_key="is_disabled",
                pv_suffix="Disabled",
                record_type=RecordType.STATUS,
            ),
            "is_pumping": RecordInfo(
                cache_key="is_pumping",
                pv_suffix="IsPumping",
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

    def _set_mapping(self):
        new_mapping = {"Start": 0}
        self._setROParam("mapping", new_mapping)
        self._inverse_mapping = {}
        for k, v in self.mapping.items():
            self._inverse_mapping[v] = k

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

        # return cached result
        if self.monitor:
            result = self._cache.get(self._name, cache_key)
            if result:
                return result

        # read from hardware and store result in cache
        value = self._get_pv_val(pv_param, as_string)
        if self.monitor:
            self._cache.put(dev=self._name, key=cache_key, value=value, time=time())

        return value

    def _get_cached_mappedpv_or_ask(self, pv_param, as_string=False):
        """
        Gets the PV value from the cache if possible, else get it from the device.
        """
        cache_key = self._get_cache_key(pv_param)
        return get_from_cache_or(
            self,
            cache_key,
            lambda: self._mapReadValue(self._get_pv_val(pv_param, as_string)),
        )

    def _get_mapped_choices(self, pv_name):
        choices = self._epics_wrapper.get_value_choices(pv_name)
        if not choices:
            raise ConfigurationError(self, f"PV {pv_name} has no value choices")
        return choices

    def _target_valid(self, pv_name, value):
        choices = self._get_mapped_choices(pv_name)
        if value not in choices:
            raise ConfigurationError(self, f"Invalid choice for {pv_name}: {value}")
        return True

    def doRead(self, maxage=0):
        return ""

    def doStart(self, target):
        is_disabled = self._get_cached_pv_or_ask("is_disabled")
        if is_disabled:
            self.log.warning("Please enable before starting")
            return
        if target.lower() == "start":
            self._put_pv_val("start", 1)

    def doReadFlowrate(self):
        return self._get_cached_pv_or_ask("flowrate")

    def doReadFlowrate_Max(self):
        return self._get_cached_pv_or_ask("flowrate_max")

    def doReadFlowrate_Unit(self):
        return self._get_cached_pv_or_ask("flowrate_unit")

    def doWriteFlowrate(self, target):
        self._put_pv_val("flowrate", target)

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
        self._cache.invalidate(self, "is_disabled")
        # self._cache.invalidate(self, "status")

    def doStop(self):
        self._put_pv_val("stop", 1)

    def doStatus(self, maxage=0):
        return self._do_status()

    def _do_status(self):
        is_pumping = self._get_cached_pv_or_ask("is_pumping")
        mode = self._attached_linked_pumping_mode.read()
        if is_pumping:
            return status.BUSY, f"Pumping in mode: {mode}"

        is_disabled = self._get_cached_pv_or_ask("is_disabled")
        if is_disabled:
            return status.WARN, "Disabled"
        else:
            return status.OK, "Enabled"

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
        time_stamp = time()
        if pv_param in ["value", "target", "first_fill_syringe"]:
            self._cache.put(
                dev=self._name,
                key=pv_param,
                value=self._mapReadValue(value),
                time=time_stamp,
            )
        else:
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
        time_stamp = time()
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
                time=time(),
            )


class CetoniPumpController(
    EpicsParameters, CanReferenceWithWarning, HasLimits, Moveable
):
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
            settable=True,
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

    attached_devices = {
        "linked_pump_device": Attach(
            "Device to start the linked pumping flow", CetoniPumpLinkedMode
        )
    }

    def _getWaiters(self):
        """
        Attached device linked_pump_device gets automatically added
        to the list of waiters, but this device should not be waited up on.
        """
        return []

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
                pv_suffix="FillVol-SP",
                record_type=RecordType.VALUE,
            ),
            "flowrate": RecordInfo(
                cache_key="flowrate",
                pv_suffix="FlowRate-SP",
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
                pv_suffix="InitPosition-Cmd",
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
                pv_suffix="Stop-Cmd",
                record_type=RecordType.OTHER,
            ),
            "fill_syringe": RecordInfo(
                cache_key="fill_syringe",
                pv_suffix="FillSyringe-Cmd",
                record_type=RecordType.OTHER,
            ),
            "empty_syringe": RecordInfo(
                cache_key="empty_syringe",
                pv_suffix="EmptySyringe-Cmd",
                record_type=RecordType.OTHER,
            ),
            "generate_flow": RecordInfo(
                cache_key="generate_flow",
                pv_suffix="GenerateFlow-Cmd",
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
                pv_suffix="ResetFault-Cmd",
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

    def _linked_mode_disabled(self):
        linked_mode_disabled = self._attached_linked_pump_device._get_cached_pv_or_ask(
            "is_disabled"
        )
        if not linked_mode_disabled:
            self.log.warning(
                f"Please disable device: {self._attached_linked_pump_device.name} first"
            )
            return False
        return True

    def doReadUnit(self):
        pv_name = self._get_pv_name("value")
        return get_from_cache_or(
            self, "unit", lambda: self._epics_wrapper.get_units(pv_name)
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

    def doWritePressure_Max(self, target):
        if not self._linked_mode_disabled():
            return
        pv_name = self._get_pv_name("pressure_max")
        limit_low, limit_high = self._epics_wrapper.get_limits(pv_name)
        target = max(limit_low, target)
        target = min(limit_high, target)
        self._put_pv_val("pressure_max", target)
        return target

    def doReadPressure_Unit(self):
        return self._get_cached_pv_or_ask("pressure_unit")

    def doReadFlowrate(self):
        return self._get_cached_pv_or_ask("flowrate")

    def doReadFlowrate_Max(self):
        return self._get_cached_pv_or_ask("flowrate_max")

    def doReadFlowrate_Unit(self):
        return self._get_cached_pv_or_ask("flowrate_unit")

    def doWriteFlowrate(self, target):
        if not self._linked_mode_disabled():
            return
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
        if not self._linked_mode_disabled():
            return
        self._put_pv_val("home", 1)

    def doReset(self):
        if not self._linked_mode_disabled():
            return
        self._put_pv_val("reset_fault", 1)
        self._cache.invalidate(self, "is_fault")

    def doStart(self, target):
        if not self._linked_mode_disabled():
            return
        self._put_pv_val("target", target)

    def doStop(self):
        if not self._linked_mode_disabled():
            return
        self._put_pv_val("stop", 1)

    @usermethod
    def fill_syringe(self):
        if self._mode == SIMULATION:
            return
        if not self._linked_mode_disabled():
            return
        self._put_pv_val("fill_syringe", 1)

    @usermethod
    def empty_syringe(self):
        if self._mode == SIMULATION:
            return
        if not self._linked_mode_disabled():
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
        if not self._linked_mode_disabled():
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
        time_stamp = time()
        self._cache.put(dev=self._name, key=pv_param, value=value, time=time_stamp)
        if pv_param == "value":
            self._cache.put(self._name, "unit", units, time_stamp)

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
        time_stamp = time()
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
                time=time(),
            )

import time

from nicos.core import (
    SIMULATION,
    Attach,
    CanDisable,
    Override,
    Param,
    oneof,
    status,
    usermethod,
)
from nicos_ess.devices.epics.pva import EpicsAnalogMoveable, EpicsMappedMoveable
from nicos_ess.devices.epics.pva.epics_common import (
    command_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
    worst_status,
)
from nicos_ess.devices.mixins import CanReferenceWithWarning


class CetoniPumpLinkedMode(CanDisable, EpicsMappedMoveable):
    """Control linked pumping between two Cetoni syringes.

    Liquid is transferred back and forth between the syringes at the
    configured flowrate. Two pumping modes are supported:

    * Manual: pump until explicitly stopped.
    * Time: pump for the duration specified by ``max_dosing_time``.

    The ``first_fill_syringe`` parameter selects which syringe fills first,
    determining the initial flow direction. The device must be enabled
    before linked pumping can start.
    """

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
        "total_vol": Param(
            description="Total volume",
            volatile=True,
        ),
        "first_fill_syringe": Param(
            description="First syringe to fill",
            volatile=True,
            settable=True,
            type=str,
        ),
        "max_dosing_time": Param(
            description="Time for linked pumping in time mode",
            volatile=True,
            settable=True,
        ),
    }

    parameter_overrides = {
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    def _after_subscribe(self, mode):
        first_fill_syringe = self._epics.get_channel_value_choices("first_fill_syringe")
        self.parameters["first_fill_syringe"].type = oneof(*first_fill_syringe)
        super()._after_subscribe(mode)

    def _build_epics_channels(self):
        epics_channels = super()._build_epics_channels()
        epics_channels.update(
            {
                "flowrate": setpoint_channel(
                    cache_key="flowrate",
                    pv_prefix_attr="pvroot",
                    pv_suffix="FlowRate-SP",
                ),
                "flowrate_max": readback_channel(
                    cache_key="flowrate_max",
                    pv_prefix_attr="pvroot",
                    pv_suffix="MaxFlowRate",
                ),
                "total_vol": readback_channel(
                    cache_key="total_vol",
                    pv_prefix_attr="pvroot",
                    pv_suffix="TotalVol",
                ),
                "first_fill_syringe": setpoint_channel(
                    cache_key="first_fill_syringe",
                    pv_prefix_attr="pvroot",
                    pv_suffix="FillingSyringeIdx-SP",
                    is_enum=True,
                ),
                "max_dosing_time": setpoint_channel(
                    cache_key="max_dosing_time",
                    pv_prefix_attr="pvroot",
                    pv_suffix="MaxDosingTime-SP",
                ),
                "start": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="Start-Cmd",
                ),
                "stop": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="StopAllPumps-Cmd",
                ),
                "enable": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="Enable-Cmd",
                ),
                "is_disabled": status_channel(
                    cache_key="is_disabled",
                    pv_prefix_attr="pvroot",
                    pv_suffix="Disabled",
                ),
                "is_pumping": status_channel(
                    cache_key="is_pumping",
                    pv_prefix_attr="pvroot",
                    pv_suffix="IsPumping",
                ),
            }
        )
        return epics_channels

    def doStart(self, target):
        is_disabled = self._epics.get_channel_value("is_disabled")
        if is_disabled:
            self.log.warning(f'Please enable device: "{self.name}" before starting')
            return
        self._epics.put_channel_value("write", target)
        self._epics.put_channel_value("start", 1)

    def doReadMax_Dosing_Time(self):
        return self._epics.get_channel_value("max_dosing_time")

    def doWriteMax_Dosing_Time(self, target):
        self._epics.put_channel_value("max_dosing_time", target)

    def doReadFlowrate(self):
        return self._epics.get_channel_value("flowrate")

    def doReadFlowrate_Max(self):
        return self._epics.get_channel_value("flowrate_max")

    def doReadFlowrate_Unit(self):
        return self._epics.get_channel_value("flowrate_unit")

    def doWriteFlowrate(self, target):
        self._epics.put_channel_value("flowrate", target)

    def doReadTotal_Vol(self):
        return self._epics.get_channel_value("total_vol")

    def doReadFirst_Fill_Syringe(self):
        return self._epics.get_channel_value("first_fill_syringe")

    def doWriteFirst_Fill_Syringe(self, target):
        self._epics.put_channel_value("first_fill_syringe", target)

    def doEnable(self, on=False):
        self._epics.put_channel_value("enable", 1 if on else 0)

    def doStop(self):
        self._epics.put_channel_value("stop", 1)

    def _compute_status(self, maxage=0):
        candidates = []
        is_pumping = self._epics.get_channel_value("is_pumping")
        if is_pumping:
            candidates.append((status.BUSY, "Pumping"))
        is_disabled = self._epics.get_channel_value("is_disabled")
        if is_disabled:
            candidates.append((status.DISABLED, "Disabled"))
        else:
            candidates.append((status.OK, "Enabled"))
        return worst_status(*candidates, self._read_primary_alarm(maxage=maxage))


class CetoniPumpController(CanReferenceWithWarning, EpicsAnalogMoveable):
    """Control an individual Cetoni syringe pump.

    The volume can be set using the target value or a relative move.
    The ``flowrate`` parameter controls the pumping rate,
    and ``pressure_max`` sets the pressure limit.

    The type of syringe is set using the ``syringe_type`` parameter.
    Changing the syringe type will update the volume limit and
    pressure limit.

    User methods allow filling or emptying the syringe and generating a
    constant flow where positive flow rates dispense liquid and negative flow rates
    aspirate liquid.

    If a linked pumping device is attached, it must be disabled before
    operating the syringe individually.
    """

    ## TODO
    # - add unit to parameter in device dialog
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
        "pressure": Param(
            description="Syringe pressure",
            volatile=True,
        ),
        "pressure_max": Param(
            description="Syringe max pressure",
            volatile=True,
            settable=True,
        ),
        "innerdiameter": Param(
            description="Syringe diameter",
            volatile=True,
        ),
        "stroke_max": Param(
            description="Syringe max piston stroke",
            volatile=True,
        ),
        "syringe_type": Param(
            description="Syringe type",
            volatile=True,
            settable=True,
            type=str,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, default=""),
        "abslimits": Override(volatile=True, mandatory=False),
        "userlimits": Override(volatile=True, chatty=False),
    }

    attached_devices = {
        "linked_pumping": Attach(
            "Device for linked pumping", CetoniPumpLinkedMode, optional=True
        ),
    }

    def _after_subscribe(self, mode):
        syringe_types = self._epics.get_channel_value_choices("syringe_type")
        self.parameters["syringe_type"].type = oneof(*syringe_types)

    def _build_epics_channels(self):
        epics_channels = super()._build_epics_channels()
        epics_channels.update(
            {
                "flowrate": setpoint_channel(
                    cache_key="flowrate",
                    pv_prefix_attr="pvroot",
                    pv_suffix="FlowRate-SP",
                ),
                "flowrate_max": readback_channel(
                    cache_key="flowrate_max",
                    pv_prefix_attr="pvroot",
                    pv_suffix="MaxFlowRate",
                ),
                "pressure": readback_channel(
                    cache_key="pressure",
                    pv_prefix_attr="pvroot",
                    pv_suffix="Pressure",
                ),
                "pressure_max": readback_channel(
                    cache_key="pressure_max",
                    pv_prefix_attr="pvroot",
                    pv_suffix="MaxPressure",
                ),
                "home": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="InitPosition-Cmd",
                ),
                "innerdiameter": readback_channel(
                    cache_key="innerdiameter",
                    pv_prefix_attr="pvroot",
                    pv_suffix="SyrInnerDiam",
                ),
                "stroke_max": readback_channel(
                    cache_key="stroke_max",
                    pv_prefix_attr="pvroot",
                    pv_suffix="SyrMaxPstStrk",
                ),
                "max_vol": readback_channel(
                    cache_key="max_vol",
                    pv_prefix_attr="pvroot",
                    pv_suffix="MaxVol",
                ),
                "syringe_type": setpoint_channel(
                    cache_key="syringe_type",
                    pv_prefix_attr="pvroot",
                    pv_suffix="SyrType",
                    is_enum=True,
                ),
                "stop": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="Stop-Cmd",
                ),
                "fill_syringe": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="FillSyringe-Cmd",
                ),
                "empty_syringe": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="EmptySyringe-Cmd",
                ),
                "generate_flow": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="GenerateFlow-Cmd",
                ),
                "is_pumping": status_channel(
                    cache_key="is_pumping",
                    pv_prefix_attr="pvroot",
                    pv_suffix="IsPumping",
                ),
                "is_homed": status_channel(
                    cache_key="is_homed",
                    pv_prefix_attr="pvroot",
                    pv_suffix="RefPosInitd",
                ),
                "is_fault": status_channel(
                    cache_key="is_fault",
                    pv_prefix_attr="pvroot",
                    pv_suffix="FaultState",
                ),
                "reset_fault": command_channel(
                    pv_prefix_attr="pvroot",
                    pv_suffix="ResetFault-Cmd",
                ),
            }
        )
        return epics_channels

    def _on_channel_update(self, update):
        super()._on_channel_update(update)
        # setting the syringe type updates the maximum volume which
        # should be reflected in the limits. This ensures the
        # limits are updated immediately after maximum volume changes.
        if update.channel == "max_vol":
            ts = time.time()
            self._cache.put(self._name, "abslimits", (0, update.value), ts)
            self._cache.put(self._name, "userlimits", self.doReadUserlimits(), ts)

    def _linked_mode_enabled(self):
        if self._attached_linked_pumping is None:
            return False
        return self._attached_linked_pumping.status(0)[0] != status.DISABLED

    def _disable_linked_mode(self):
        if self._attached_linked_pumping is not None:
            self._attached_linked_pumping.disable()

    def doReadAbslimits(self):
        high_limit = self._epics.get_channel_value("max_vol")
        return 0, high_limit

    def doReadPressure(self):
        return self._epics.get_channel_value("pressure")

    def doReadPressure_Max(self):
        return self._epics.get_channel_value("pressure_max")

    def doWritePressure_Max(self, target):
        limit_low, limit_high = self._epics.get_channel_limits("pressure_max")
        target = min(limit_high, max(limit_low, target))
        self._epics.put_channel_value("pressure_max", target)
        return target

    def doReadFlowrate(self):
        return self._epics.get_channel_value("flowrate")

    def doReadFlowrate_Max(self):
        return self._epics.get_channel_value("flowrate_max")

    def doWriteFlowrate(self, target):
        self._epics.put_channel_value("flowrate", target)

    def doReadInnerdiameter(self):
        return self._epics.get_channel_value("innerdiameter")

    def doReadStroke_Max(self):
        return self._epics.get_channel_value("stroke_max")

    def doReadSyringe_Type(self):
        return self._epics.get_channel_value("syringe_type")

    def doWriteSyringe_Type(self, target):
        self._epics.put_channel_value("syringe_type", target)

    def doReference(self):
        self._epics.put_channel_value("home", 1)

    def doReset(self):
        self._epics.put_channel_value("reset_fault", 1)

    def doStart(self, target):
        if self._linked_mode_enabled():
            self._disable_linked_mode()
        self._epics.put_channel_value("write", target)

    def doStop(self):
        self._epics.put_channel_value("stop", 1)

    def _compute_status(self, maxage=0):
        candidates = []

        is_in_fault = self._epics.get_channel_value("is_fault")
        if is_in_fault:
            candidates.append((status.ERROR, "In faulty state"))

        is_homed = self._epics.get_channel_value("is_homed")
        if not is_homed:
            candidates.append((status.WARN, "Not homed"))

        status_msg = ""
        if self._linked_mode_enabled():
            status_msg += f"Controlled by {self._attached_linked_pumping.name}: "
        is_pumping = self._epics.get_channel_value("is_pumping")
        if is_pumping:
            status_msg += "Pumping"
            candidates.append((status.BUSY, status_msg))
        else:
            status_msg += "Idle"
            candidates.append((status.OK, status_msg))

        return worst_status(*candidates, self._read_primary_alarm(maxage=maxage))

    @usermethod
    def fill_syringe(self):
        if self._mode == SIMULATION:
            return
        if self._linked_mode_enabled():
            self._disable_linked_mode()
        self._epics.put_channel_value("fill_syringe", 1)

    @usermethod
    def empty_syringe(self):
        if self._mode == SIMULATION:
            return
        if self._linked_mode_enabled():
            self._disable_linked_mode()
        self._epics.put_channel_value("empty_syringe", 1)

    @usermethod
    def generate_flow(self, target):
        """
        Generate constant flow with target flow rate

        Positive value = dispense
        Negative value = aspirate
        """
        if self._mode == SIMULATION:
            return
        if self._linked_mode_enabled():
            self._disable_linked_mode()
        self._epics.put_channel_value("generate_flow", target)

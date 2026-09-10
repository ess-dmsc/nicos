import time

from nicos.core import (
    SIMULATION,
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
)
from nicos_ess.devices.mixins import CanReferenceWithWarning


class CetoniPumpController(CanReferenceWithWarning, EpicsAnalogMoveable):
    ## TODO
    # - add unit to parameter in device dialog
    # - add enabled/disabled flag in epics?
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
        if update.channel == "max_vol":
            ts = time.time()
            self._cache.put(self._name, "abslimits", (0, update.value), ts)
            self._cache.put(self._name, "userlimits", self.doReadUserlimits(), ts)

    def doReadAbslimits(self):
        high_limit = self._epics.get_channel_value("max_vol")
        return 0, high_limit

    def doReadPressure(self):
        return self._epics.get_channel_value("pressure")

    def doReadPressure_Max(self):
        return self._epics.get_channel_value("pressure_max")

    def doWritePressure_Max(self, target):
        limit_low, limit_high = self._epics.get_channel_limits("pressure_max")
        target = get_target_inside_limits(target, limit_low, limit_high)
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
        # self._cache.invalidate(self, "is_fault")

    def doStart(self, target):
        # if not self._linked_mode_disabled():
        #     return
        self._epics.put_channel_value("write", target)

    def doStop(self):
        # if not self._linked_mode_disabled():
        #     return
        self._epics.put_channel_value("stop", 1)

    def _compute_status(self, maxage=0):
        is_in_fault = self._epics.get_channel_value("is_fault")
        if is_in_fault:
            return status.ERROR, "In faulty state"

        is_homed = self._epics.get_channel_value("is_homed")
        if not is_homed:
            return status.WARN, "Not homed"

        is_pumping = self._epics.get_channel_value("is_pumping")
        if is_pumping:
            return status.BUSY, "Pumping"
        else:
            return status.OK, "idle"

    @usermethod
    def fill_syringe(self):
        if self._mode == SIMULATION:
            return
        # if not self._linked_mode_disabled():
        #     return
        self._epics.put_channel_value("fill_syringe", 1)

    @usermethod
    def empty_syringe(self):
        if self._mode == SIMULATION:
            return
        # if not self._linked_mode_disabled():
        #     return
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
        # if not self._linked_mode_disabled():
        #     return
        self._epics.put_channel_value("generate_flow", target)


class CetoniPumpLinkedMode(CanDisable, EpicsMappedMoveable):
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
        super()._after_subscribe(self, mode)

    def _build_epics_channels(self):
        epics_channels = {
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
        return epics_channels

    #
    # def doStart(self, target):
    #     is_disabled = self._epics.get_channel_value("is_disabled")
    #     if is_disabled:
    #         self.log.warning("Please enable before starting")
    #         return
    #     if target.lower() == "start":
    #         self._epics.put_channel_value("start", 1)
    #
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
        # self._cache.invalidate(self, "is_disabled")

    #
    # def doStop(self):
    #     self._epics.put_channel_value("stop", 1)
    #
    # def _compute_status(self):
    #     is_pumping = self._epics.get_channel_value("is_pumping")
    #     if is_pumping:
    #         return status.BUSY, "Pumping"
    #
    #     is_disabled = self._epics.get_channel_value("is_disabled")
    #     if is_disabled:
    #         return status.WARN, "Disabled"
    #     else:
    #         return status.OK, "Enabled"


def get_target_inside_limits(target, limit_low, limit_high):
    target = max(limit_low, target)
    target = min(limit_high, target)
    return target

from nicos.core import (
    SIMULATION,
    Moveable,
    Override,
    Param,
    oneof,
    pvname,
    status,
)
from nicos.core.mixins import CanDisable, HasLimits
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    readback_channel,
)


class FlowCryoInput(HasLimits, EpicsDeviceBase, CanDisable, Moveable):
    """
    Controller device to control one input channel of the flow cryo
    """

    parameters = {
        "pvroot": Param(
            "Name of the Flow Cryo PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "input_pos": Param(
            "Input position of the Flow Cryo",
            type=oneof("A", "B", "C", "D", "D2", "D3", "D4", "D5"),
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "ramp": Param(
            "Ramping to start/stop heating",
            type=oneof(
                "Off", "Range1/Low", "Range2/Medium", "Range3/High", "Range4", "Range5"
            ),
            mandatory=True,
            settable=True,
            default="Off",
        ),
    }

    parameter_overrides = {
        # units choices are limited via epics but can be changed by user
        "unit": Override(
            mandatory=False,
            settable=False,
            volatile=True,
        ),
        "abslimits": Override(volatile=True, mandatory=False),
        "userlimits": Override(volatile=False, chatty=False),
    }

    _default_pv_prefix_attr = "pvroot"
    _primary_channel = "value"
    _connect_channels = ("alarm",)

    def doStart(self):
        # determine ramp setting set by system, then set the pv to that value
        print("starting!")

    def doStop(self):
        # set ramp pv to OFF
        print("stopping")

    def doPreinit(self, mode):
        self._current_status = (status.OK, "")
        if mode == SIMULATION:
            return
        EpicsDeviceBase.doPreinit(self, mode)

    def _build_epics_channels(self):
        epics_channels = {
            "value": readback_channel(
                f"Temp{self.input_pos}-Kelvin-R", cache_key="value", primary=True
            ),
            "alarm": readback_channel(f"Alarm{self.input_pos}-Summary"),
            "highlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.HIGH"),
            "lowlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.LOW"),
            "hwhighlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.HIHI"),
            "hwlowlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.LOLO"),
        }
        return epics_channels

    # TODO: Compute proper status
    def _compute_status(self, maxage=0):
        msg = self._read_channel_cached("alarm")
        if msg == 0:
            return status.OK, " "
        else:
            # TODO: Error Catching to determine where error is coming from
            return status.ERROR, "ALARM"

    def doReadAbslimits(self):
        abs_min = self._epics.get_channel_value("hwlowlimit")
        abs_max = self._epics.get_channel_value("hwhighlimit")
        return abs_min, abs_max

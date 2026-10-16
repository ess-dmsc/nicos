from nicos.core import (
    SIMULATION,
    Moveable,
    Override,
    Param,
    oneof,
    pvname,
)
from nicos.core.mixins import CanDisable, HasLimits
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    readback_channel,
    setpoint_channel,
)


class FlowCryoInput(HasLimits, EpicsDeviceBase, CanDisable, Moveable):
    """
    Controller device for the Lakeshore 336.

    This implementation assumes that the input and outputs of the flow-cryo will not be changed 'on the fly'
    (for example: Input A -> Output 1, Input B -> Output 2, etc...). If input and output connections
    are changed, the setup in nicos must be restared for changes to take effect.
    Ramping and range are set via parameters and heating is started by moving the setpoint
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
            settable=True,
            userparam=False,
        ),
        "output_num": Param(
            "Output number the input is connected to",
            type=int,
            mandatory=True,
            settable=True,
            userparam=False,
        ),
        "range": Param(
            "Range speed macro control",
            type=oneof("Off", "Range1/Low", "Range2/Medium", "Range3/High"),
            mandatory=False,
            settable=True,
            default="Off",
        ),
        "ramp": Param(
            "Designated Ramping speed",
            type=float,
            mandatory=False,
            settable=True,
            default=1.0,
        ),
        "ramp_map": Param(
            "to turn off ramping",
            type=oneof("On", "Off"),
            mandatory=False,
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
        "userlimits": Override(volatile=True, chatty=False),
    }

    # some parameters are mapped enums in EPICS
    range_enum = {
        "Off": 0,
        "Range1/Low": 1,
        "Range2/Medium": 2,
        "Range3/High": 3,
    }

    ramp_enum = {
        "Off": 0,
        "On": 1,
    }

    _default_pv_prefix_attr = "pvroot"
    _primary_channel = "value"
    _connect_channels = ("alarm",)

    def doPreinit(self, mode):
        if mode == SIMULATION:
            return
        EpicsDeviceBase.doPreinit(self, mode)

    def doInit(self, mode):
        if mode == SIMULATION:
            return

    def _build_epics_channels(self):
        epics_channels = {
            "value": readback_channel(
                f"Temp{self.input_pos}-Kelvin-R", cache_key="value", primary=True
            ),
            "alarm": readback_channel(f"Alarm{self.input_pos}-Summary"),
            "alarm_severity": readback_channel(f"Alarm{self.input_pos}-Summary.SEVR"),
            "highlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.HIGH"),
            "lowlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.LOW"),
            "hwhighlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.HI"),
            "hwlowlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.LO"),
            "target": setpoint_channel(f"Setp{self.output_num}-SP", cache_key="target"),
            "target_rb": readback_channel(f"Setp{self.output_num}-RB"),
            "range": setpoint_channel(f"Range{self.output_num}-SP"),
            "range_rb": readback_channel(f"Range{self.output_num}-RB"),
            "ramp": setpoint_channel(f"Ramp{self.output_num}-SP"),
            "ramp_rb": readback_channel(f"Ramp{self.output_num}-RB"),
            "ramp_ctrl_sp": setpoint_channel(f"RampStatus{self.output_num}-SP"),
            "ramp_ctrl_rb": readback_channel(f"RampStatus{self.output_num}-RB"),
            "polling": setpoint_channel(f"Disable{self.input_pos}"),
        }
        return epics_channels

    def doStart(self, value):
        self._epics.put_channel_value("target", value)

    def isAllowed(self, pos):
        return Moveable.isAllowed(self, pos)

    def doStop(self):
        # the lakeshore is stopped by taking the current temperature and setting it again as the setpoint
        curval = self._epics.get_channel_value("value")
        self._epics.put_channel_value("target", curval)

    def _compute_status(self, maxage=0):
        # TODO: No proper alarm summary enabled in epics. Catch where the
        # error is coming from here (for now...)
        msg = self._read_channel_cached("alarm")
        severity = self._read_channel_cached("alarm_severity")
        return severity, msg

    def _mapReadValue(self, value, mapping):
        inverse_mapping = {v: k for k, v in mapping.items()}
        mapped_value = inverse_mapping.get(value)
        return mapped_value

    def doWriteRange(self, value):
        self._epics.put_channel_value("range", self.range_enum[value])

    def doReadRange(self):
        value = self._read_channel_cached("range_rb")
        return self._mapReadValue(value, self.range_enum)

    def doWriteRamp(self, value):
        self._epics.put_channel_value("ramp", value)

    def doReadRamp(self):
        return self._read_channel_cached("ramp_rb")

    def doWriteRamp_Map(self, value):
        self._epics.put_channel_value("ramp", self.ramp_enum[value])

    def doReadRamp_Map(self):
        value = self._read_channel_cached("ramp_ctrl_rb")
        return self._mapReadValue(value, self.ramp_enum)

    def doReadAbslimits(self):
        abs_min = self._epics.get_channel_value("lowlimit")
        abs_max = self._epics.get_channel_value("highlimit")
        return abs_min, abs_max

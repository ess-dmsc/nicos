from nicos.core import (
    SIMULATION,
    Override,
    Param,
    Readable,
    oneof,
    pvname,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    readback_channel,
    setpoint_channel,
)


class FlowCryoInput(EpicsDeviceBase, Readable):
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
            settable=True,
            volatile=True,
            type=dict("Kelvin", "Celsius", "Sensor", "Err"),
            default="Kelvin",
        ),
    }

    _default_pv_prefix_attr = "pvroot"
    _primary_channel = "value"
    _connect_channels = ("alarm",)

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
            "units": readback_channel(f"InType{self.input_pos}-Units-RB"),
            "setunits": setpoint_channel(f"InType{self.input_pos}-Units-SP"),
            "highlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.HIGH"),
            "lowlimit": readback_channel(f"Temp{self.input_pos}-Kelvin-R.LOW"),
        }
        return epics_channels

    # TODO: Compute proper status
    def _compute_status(self, maxage=0):
        msg = self._read_channel_cached("alarm")
        if msg == 0:
            return status.OK, "No Alarm"
        else:
            return status.OK, "All Good"

    def doWriteUnits(self, units):
        units_to_enum = {"Kelvin": 1, "Celsius": 2, "Sensor": 3}
        self._epics.put_channel_value("setunits", units_to_enum[units])

    def doReadUnit(self):
        enum_to_units = {1: "Kelvin", 2: "Celsius", 3: "Sensor"}
        units = self._read_channel_cached("units")
        return f"{enum_to_units[units]}" if units else "Err"

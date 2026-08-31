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
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _default_pv_prefix_attr = "pvroot"
    _primary_channel = "value"
    _connect_channels = ("value",)

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
            "alarm": readback_channel("AlarmSummary"),
        }
        return epics_channels

    # TODO: Compute proper status
    def _compute_status(self, maxage=0):
        return status.OK, ""

import threading

from nicos.core import status
from nicos_ess.estia.devices import flow_cryo_control
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = None


class FakeEstiaFlowCryo(flow_cryo_control):
    @classmethod
    def _initial_record_fields(cls):
        return {
            "value": 190.0,
            "highlimit": 990,
            "lowlimit": -1,
            "hwhighlimit": 990,
            "hwlowlimit": -1,
            "target": 0,
            "target_rb": 0,
            "range": 0,
            "range_rb": 0,
            "ramp": 0,
            "ramp_rb": 0,
            "ramp_ctrl_sp": 0,
            "ramp_ctrl_rb": 0,
            "polling": 0,
        }

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._status = (status.OK, "")
        self._epics_channels = self._initial_record_fields()
        self._epics = FakeEpicsComponent(self._epics_channels)

    def doInit(self, mode):
        pass

    def _read_channel_cached(self, field, as_string=None, maxage=None):
        return self._epics_channels[field]

    def doReadUnit(self, maxage=None):
        return self._epics_channels["unit"]

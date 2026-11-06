import threading

import pytest

from nicos.core import status
from nicos_ess.estia.devices.flow_cryo_control import FlowCryoInput
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = "estia_flowcryo"


class FakeEstiaFlowCryo(FlowCryoInput):
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

    def doRead(self, maxage=None):
        return self._epics.get_channel_value("value")


class TestEstiaFlowCryo:
    flowcryo = None

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.flowcryo = self.session.getDevice("lakeshore_A", {})

    def test_limits_update(self):
        assert self.flowcryo.abslimits == (-1, 990)

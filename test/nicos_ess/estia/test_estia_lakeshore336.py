import threading

import pytest

from nicos.core import status
from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.estia.devices.flow_cryo_control import FlowCryoInput
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = "estia_flowcryo"
PV_ROOT = "SIM:LS:"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )
    backend.values[f"{PV_ROOT}TempA-Kelvin-R.LOW"] = 0
    backend.values[f"{PV_ROOT}TempA-Kelvin-R.HIGH"] = 0
    backend.values[f"{PV_ROOT}AlarmA-Summary"] = "No Alarm"
    backend.value_choices[f"{PV_ROOT}AlarmA-Summary"] = ["No Alarm", "Alarm"]
    backend.values[f"{PV_ROOT}Range0-RB"] = 0
    backend.values[f"{PV_ROOT}Range0-SP"] = 0
    backend.value_choices[f"{PV_ROOT}Range0-RB"] = [
        "Off",
        "Range1/Low",
        "Range2/Medium",
        "Range3/High",
        "Range4",
        "Range5",
    ]
    backend.values[f"{PV_ROOT}Ramp0-RB"] = 0
    backend.values[f"{PV_ROOT}Ramp0-SP"] = 0
    backend.values[f"{PV_ROOT}RampStatus0-RB"] = 0
    backend.values[f"{PV_ROOT}RampStatus0-SP"] = 0
    backend.value_choices[f"{PV_ROOT}RampStatus0-RB"] = ["On", "Off"]


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
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.flowcryo = self.session.getDevice("lakeshore_A", {})

    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            FlowCryoInput,
            name="flow_cryo_A",
            shared={
                "pvroot": PV_ROOT,
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_limits_update(self):
        low, high = self.flowcryo.abslimits

        assert (low, high) == self.flowcryo.abslimits

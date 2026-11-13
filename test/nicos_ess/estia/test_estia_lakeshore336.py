import pytest

from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.estia.devices.flow_cryo_control import FlowCryoInput
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

session_setup = "estia_flowcryo"
PV_ROOT = "SIM:LS:"
ALARM_SUMMARY = [
    "No Alarm",
    "Alarm",
]
ALARM_CHOICES = [
    "NO_ALARM",
    "MINOR",
    "MAJOR",
    "INVALID",
]
RANGE_CHOICES = [
    "Off",
    "Range1/Low",
    "Range2/Medium",
    "Range3/High",
]
STATE = [
    "On",
    "Off",
]


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )
    backend.values[f"{PV_ROOT}TempA-Kelvin-R"] = 100
    backend.values[f"{PV_ROOT}TempA-Kelvin-R.LOW"] = 0
    backend.values[f"{PV_ROOT}TempA-Kelvin-R.HIGH"] = 999
    backend.values[f"{PV_ROOT}AlarmA-Summary"] = ALARM_SUMMARY.index("No Alarm")
    backend.value_choices[f"{PV_ROOT}AlarmA-Summary"] = ALARM_SUMMARY
    backend.values[f"{PV_ROOT}AlarmA-Summary.SEVR"] = ALARM_CHOICES.index("NO_ALARM")
    backend.value_choices[f"{PV_ROOT}AlarmA-Summary.SEVR"] = ALARM_CHOICES
    backend.values[f"{PV_ROOT}Range0-RB"] = RANGE_CHOICES.index("Off")
    backend.value_choices[f"{PV_ROOT}Range0-RB"] = RANGE_CHOICES
    backend.values[f"{PV_ROOT}Range0-SP"] = RANGE_CHOICES.index("Off")
    backend.value_choices[f"{PV_ROOT}Range0-SP"] = RANGE_CHOICES
    backend.values[f"{PV_ROOT}Ramp0-RB"] = 0
    backend.values[f"{PV_ROOT}Ramp0-SP"] = 0
    backend.values[f"{PV_ROOT}RampStatus0-RB"] = STATE.index("Off")
    backend.value_choices[f"{PV_ROOT}RampStatus0-RB"] = STATE
    backend.values[f"{PV_ROOT}RampStatus0-SP"] = STATE.index("Off")
    backend.value_choices[f"{PV_ROOT}RampStatus0-SP"] = STATE
    backend.values[f"{PV_ROOT}Setp0-RB"] = 0
    backend.values[f"{PV_ROOT}Setp0-SP"] = 0
    return backend


class TestEstiaFlowCryo:
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

    @pytest.mark.parametrize(
        ("absmin", "absmax"),
        [
            pytest.param(0, 999, id="baseline"),
            pytest.param(-50, 20, id="shift limits"),
        ],
    )
    def test_abslimits_read_from_pvs(
        self, device_harness, fake_backend, absmin, absmax
    ):
        daemon_device, _poller_device = self._create_pair(device_harness)
        fake_backend.emit_update(f"{PV_ROOT}TempA-Kelvin-R.LOW", value=absmin)
        fake_backend.emit_update(f"{PV_ROOT}TempA-Kelvin-R.HIGH", value=absmax)

        assert daemon_device.abslimits == (absmin, absmax)

    def test_start_writes_to_target_pv(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device.start(200)

        assert fake_backend.values[f"{PV_ROOT}Setp0-SP"] == 200

    @pytest.mark.parametrize(
        ("suffix", "par", "map_val", "map_enum"),
        [
            pytest.param("RampStatus0-SP", "ramp_map", "On", 1, id="turn on ramping"),
            pytest.param("Range0-SP", "range", "Range1/Low", 1, id="set range to low"),
            pytest.param(
                "Range0-SP", "range", "Range3/High", 3, id="set range to high"
            ),
        ],
    )
    def test_enum_params_write_to_sp_pvs(
        self, device_harness, fake_backend, suffix, par, map_val, map_enum
    ):
        daemon_device, _poller_device = self._create_pair(device_harness)
        setattr(daemon_device, par, map_val)
        assert fake_backend.values[f"{PV_ROOT}{suffix}"] == map_enum

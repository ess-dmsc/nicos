import pytest

from nicos.core import status
from nicos_ess.devices.epics import hplc_pump
from nicos_ess.devices.epics.pva import epics_common
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

PV_ROOT = "SIM:PUMP:"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )

    backend.values[f"{PV_ROOT}Error-R"] = 0
    backend.value_choices[f"{PV_ROOT}Error-R"] = ["No error", "Hardware error"]
    backend.values[f"{PV_ROOT}ErrorText-R"] = ""
    backend.values[f"{PV_ROOT}ErrorReset-S"] = 0
    backend.values[f"{PV_ROOT}Status-R"] = 0
    backend.value_choices[f"{PV_ROOT}Status-R"] = ["Off", "Pumping"]
    backend.values[f"{PV_ROOT}PressureMax-S"] = 0.0
    backend.values[f"{PV_ROOT}PressureMax-R"] = 10.0
    backend.values[f"{PV_ROOT}PressureMin-S"] = 0.0
    backend.values[f"{PV_ROOT}PressureMin-R"] = 1.0
    backend.values[f"{PV_ROOT}PumpForTime-S"] = 0
    backend.values[f"{PV_ROOT}PumpForVolume-S"] = 0
    backend.values[f"{PV_ROOT}Start-S"] = 0
    backend.values[f"{PV_ROOT}Stop-S"] = 0
    return backend


class TestHPLCPumpControllerHarness:
    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            hplc_pump.HPLCPumpController,
            name="hplc_pump",
            shared={
                "pv_root": PV_ROOT,
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_status_busy_while_pumping(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}Status-R", value=1)

        assert daemon_device.status() == (status.BUSY, "Pumping")

    def test_status_error_from_error_enum(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}Error-R", value=1)

        assert daemon_device.status() == (status.ERROR, "Hardware error")

    def test_stop_writes_stop_pv(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device.stop()

        assert fake_backend.values[f"{PV_ROOT}Stop-S"] == 1

    def test_pressure_limits_read_from_readback_pvs(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)
        del fake_backend

        assert daemon_device.max_pressure == 10.0
        assert daemon_device.min_pressure == 1.0

    @pytest.mark.parametrize(
        ("suffix", "cache_key", "value"),
        [
            pytest.param("PressureMax-R", "max_pressure", 20.0, id="maximum"),
            pytest.param("PressureMin-R", "min_pressure", 2.0, id="minimum"),
        ],
    )
    def test_pressure_callback_updates_public_parameter(
        self, device_harness, fake_backend, suffix, cache_key, value
    ):
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}{suffix}", value=value)

        assert daemon_device._cache.get(daemon_device, cache_key) == value

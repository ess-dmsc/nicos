import pytest

from nicos.core import status
from nicos_ess.devices.epics import power_supply_channel
from nicos_ess.devices.epics.pva import epics_common
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

PS_PV = "SIM:PS:CH1"


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )

    backend.values[f"{PS_PV}-VMon"] = 0.0
    backend.values[f"{PS_PV}-IMon"] = 0.0
    backend.values[f"{PS_PV}-Pw-RB"] = 0
    backend.values[f"{PS_PV}-Pw"] = 0
    backend.values[f"{PS_PV}-Status-ON"] = 0
    return backend


class TestPowerSupplyChannelHarness:
    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            power_supply_channel.PowerSupplyChannel,
            name="ps_channel",
            shared={
                "ps_pv": PS_PV,
                "mapping": {"OFF": 0, "ON": 1},
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend):
        del fake_backend
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_read_maps_power_readback(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        assert daemon_device.read(0) == "OFF"

        fake_backend.emit_update(f"{PS_PV}-Pw-RB", value=1)

        assert daemon_device.read(0) == "ON"

    def test_enable_writes_power_pv(self, device_harness, fake_backend):
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device.enable()

        assert fake_backend.values[f"{PS_PV}-Pw"] == 1

    def test_status_reports_channel_off_with_readings(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = self._create_pair(device_harness)
        del fake_backend

        stat, msg = daemon_device.status()
        assert stat == status.OK
        assert msg.startswith("Channel is OFF")

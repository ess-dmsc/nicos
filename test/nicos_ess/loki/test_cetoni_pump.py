from unittest.mock import patch

import pytest

from nicos.core import LimitError, status
from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.loki.devices.cetoni_pump import (
    CetoniPumpController,
    get_target_inside_limits,
)


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    backend = fake_epics_backend_factory(epics_common)
    backend.values["SP1:MaxVol"] = 5
    backend.values["SP1:FilledVolume"] = 1
    backend.values["SP1:FillVol-SP"] = 0
    backend.values["SP1:FlowRate-SP"] = 0
    backend.values["SP1:FlowRate.EGU"] = "ml/s"
    backend.values["SP1:MaxFlowRate"] = 5
    backend.values["SP1:IsPumping"] = 0
    backend.values["SP1:SyrType"] = 0
    backend.values["SP1:Pressure"] = 0
    backend.values["SP1:MaxPressure"] = 5
    backend.values["SP1:Pressure.EGU"] = "mbar"
    backend.values["SP1:SyrInnerDiam"] = 0.3
    backend.values["SP1:SyrInnerDiam.EGU"] = "mm"
    backend.values["SP1:SyrMaxPstStrk"] = 5
    backend.values["SP1:SyrMaxPstStrk.EGU"] = "mm"
    backend.values["SP1:FaultState"] = 0
    backend.values["SP1:RefPosInitd"] = 1
    backend.value_choices["SP1:SyrType"] = ["3mL 200bar", "5mL 100bar"]
    return backend


class TestCetoniPumpController:
    def test_new_target_valid(self):
        assert get_target_inside_limits(target=100, limit_low=10, limit_high=200) == 100

    def test_new_target_cap_at_limit_low(self):
        assert get_target_inside_limits(target=1, limit_low=10, limit_high=200) == 10

    def test_new_target_cap_at_limit_high(self):
        assert get_target_inside_limits(target=300, limit_low=10, limit_high=200) == 200

    def test_daemon_device_ok(self, daemon_device_harness, fake_backend):
        pump = daemon_device_harness.create_master(
            CetoniPumpController,
            name="pump",
            pvroot="SP1:",
            readpv="SP1:FilledVolume",
            writepv="SP1:FillVol-SP",
        )
        assert pump.read(maxage=0) == 1
        assert pump.status()[0] == status.OK

    def test_daemon_device_fault(self, daemon_device_harness, fake_backend):
        pump = daemon_device_harness.create_master(
            CetoniPumpController,
            name="pump",
            pvroot="SP1:",
            readpv="SP1:FilledVolume",
            writepv="SP1:FillVol-SP",
        )
        fake_backend.values["SP1:FaultState"] = 1
        assert pump.status(maxage=0)[0] == status.ERROR

    def test_daemon_device_write(self, daemon_device_harness, fake_backend):
        pump = daemon_device_harness.create_master(
            CetoniPumpController,
            name="pump",
            pvroot="SP1:",
            readpv="SP1:FilledVolume",
            writepv="SP1:FillVol-SP",
        )
        fake_backend.values["SP1:MaxVol"] = 5
        pump.move(2)
        assert ("SP1:FillVol-SP", 2, False) in fake_backend.put_calls
        assert fake_backend.values["SP1:FillVol-SP"] == 2

    def test_daemon_device_do_not_exceed_max_vol(
        self, daemon_device_harness, fake_backend
    ):
        pump = daemon_device_harness.create_master(
            CetoniPumpController,
            name="pump",
            pvroot="SP1:",
            readpv="SP1:FilledVolume",
            writepv="SP1:FillVol-SP",
        )
        fake_backend.values["SP1:MaxVol"] = 5
        with pytest.raises(LimitError):
            pump.move(100)

    def test_new_max_volume_updates_limits(self, device_harness, fake_backend):
        pump_in_daemon, pump_in_poller = device_harness.create_pair(
            CetoniPumpController,
            name="pump",
            shared={
                "pvroot": "SP1:",
                "readpv": "SP1:FilledVolume",
                "writepv": "SP1:FillVol-SP",
            },
        )
        fake_backend.emit_update("SP1:MaxVol", value=3.1)
        assert pump_in_daemon._cache.get(pump_in_daemon, "abslimits") == (0, 3.1)
        assert pump_in_daemon._cache.get(pump_in_daemon, "userlimits") == (0, 3.1)

    def test_epics_update_triggers_poller_callback(self, device_harness, fake_backend):
        original = CetoniPumpController._on_channel_update

        with patch.object(
            CetoniPumpController,
            "_on_channel_update",
            autospec=True,
            side_effect=original,
        ) as callback:
            pump_in_daemon, pump_in_poller = device_harness.create_pair(
                CetoniPumpController,
                name="pump",
                shared={
                    "pvroot": "SP1:",
                    "readpv": "SP1:FilledVolume",
                    "writepv": "SP1:FillVol-SP",
                },
            )
            fake_backend.emit_update("SP1:FilledVolume", value=3)
            callback.assert_called_once()
            device, update = callback.call_args.args
            assert device is pump_in_poller
            assert update.channel == "read"
            assert update.pv_name == "SP1:FilledVolume"
            assert update.value == 3
            assert pump_in_poller._epics.cache_key_for(update.channel) == "value"
            assert pump_in_daemon._cache.get(pump_in_daemon, "value") == 3

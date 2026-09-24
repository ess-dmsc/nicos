from unittest.mock import patch

import pytest

from nicos.core import LimitError, status
from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.loki.devices.cetoni_pump import (
    CetoniPumpController,
    CetoniPumpLinkedMode,
)


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    backend = fake_epics_backend_factory(epics_common)
    backend.values["SP1MaxVol"] = 5
    backend.values["SP1FilledVolume"] = 1
    backend.values["SP1FillVol-SP"] = 0
    backend.values["SP1FlowRate-SP"] = 0
    backend.values["SP1FlowRate.EGU"] = "ml/s"
    backend.values["SP1MaxFlowRate"] = 5
    backend.values["SP1IsPumping"] = 0
    backend.values["SP1SyrType"] = 0
    backend.values["SP1Pressure"] = 0
    backend.values["SP1MaxPressure"] = 5
    backend.values["SP1Pressure.EGU"] = "mbar"
    backend.values["SP1SyrInnerDiam"] = 0.3
    backend.values["SP1SyrInnerDiam.EGU"] = "mm"
    backend.values["SP1SyrMaxPstStrk"] = 5
    backend.values["SP1SyrMaxPstStrk.EGU"] = "mm"
    backend.values["SP1FaultState"] = 0
    backend.values["SP1RefPosInitd"] = 1
    backend.values["LnkdFlowRate-SP"] = 0
    backend.values["LnkdMaxFlowRate"] = 1
    backend.values["LnkdTotalVol"] = 3
    backend.values["LnkdFillingSyringeIdx-SP"] = 0
    backend.values["LnkdMaxDosingTime-SP"] = 5
    backend.values["LnkdDisabled"] = 0
    backend.values["LnkdIsPumping"] = 0
    backend.values["LnkdStopMode-SP"] = 0
    backend.values["LnkdStart-Cmd"] = 0

    backend.limits["SP1MaxPressure"] = (0, 5)

    backend.value_choices["SP1SyrType"] = ["3mL 200bar", "5mL 100bar"]
    backend.value_choices["LnkdFillingSyringeIdx-SP"] = ["SP1", "SP2"]
    backend.value_choices["LnkdStopMode-SP"] = ["Manual", "Time"]
    return backend


@pytest.fixture
def pump_in_daemon(daemon_device_harness, fake_backend):
    return daemon_device_harness.create_master(
        CetoniPumpController,
        name="pump_in_daemon",
        pvroot="",
        pump_pvroot="SP1",
        readpv="SP1FilledVolume",
        writepv="SP1FillVol-SP",
    )


@pytest.fixture
def pump_pair(device_harness, fake_backend):
    return device_harness.create_pair(
        CetoniPumpController,
        name="pump",
        shared={
            "pvroot": "",
            "pump_pvroot": "SP1",
            "readpv": "SP1FilledVolume",
            "writepv": "SP1FillVol-SP",
        },
    )


@pytest.fixture
def linked_pumping_in_daemon(daemon_device_harness, fake_backend):
    return daemon_device_harness.create_master(
        CetoniPumpLinkedMode,
        name="linked",
        pvroot="Lnkd",
        readpv="LnkdStopMode-SP",
        writepv="LnkdStopMode-SP",
    )


class TestCetoniPumpController:
    def test_pump_device_ok(self, pump_in_daemon):
        assert pump_in_daemon.read(maxage=0) == 1
        assert pump_in_daemon.status()[0] == status.OK

    def test_pump_device_fault(self, pump_in_daemon, fake_backend):
        fake_backend.values["SP1FaultState"] = 1
        assert pump_in_daemon.status(maxage=0)[0] == status.ERROR

    def test_pump_device_write(
        self, linked_pumping_in_daemon, pump_in_daemon, fake_backend
    ):
        fake_backend.values["LnkdDisabled"] = 1
        fake_backend.values["SP1MaxVol"] = 5
        pump_in_daemon.move(2)
        assert ("SP1FillVol-SP", 2, False) in fake_backend.put_calls
        assert fake_backend.values["SP1FillVol-SP"] == 2

    def test_pump_device_do_not_exceed_max_vol(
        self, linked_pumping_in_daemon, pump_in_daemon, fake_backend
    ):
        fake_backend.values["LnkdDisabled"] = 1
        fake_backend.values["SP1MaxVol"] = 5
        with pytest.raises(LimitError):
            pump_in_daemon.move(100)

    def test_pump_set_max_pressure_inside_limits(self, pump_in_daemon, fake_backend):
        fake_backend.values["SP1MaxPressure"] = 5
        pump_in_daemon.pressure_max = 4
        assert pump_in_daemon.pressure_max == 4

    def test_pump_set_max_pressure_capped_at_max(self, pump_in_daemon, fake_backend):
        fake_backend.values["SP1MaxPressure"] = 3
        pump_in_daemon.pressure_max = 6
        assert pump_in_daemon.pressure_max == 5

    def test_pump_new_max_volume_updates_limits(self, pump_pair, fake_backend):
        pump_in_daemon, pump_in_poller = pump_pair
        fake_backend.emit_update("SP1MaxVol", value=3.1)
        assert pump_in_daemon._cache.get(pump_in_daemon, "abslimits") == (0, 3.1)
        assert pump_in_daemon._cache.get(pump_in_daemon, "userlimits") == (0, 3.1)

    def test_pump_epics_update_triggers_poller_callback(self, pump_pair, fake_backend):
        original = CetoniPumpController._on_channel_update
        with patch.object(
            CetoniPumpController,
            "_on_channel_update",
            autospec=True,
            side_effect=original,
        ) as callback:
            pump_in_daemon, pump_in_poller = pump_pair
            fake_backend.emit_update("SP1FilledVolume", value=3)
            callback.assert_called_once()
            device, update = callback.call_args.args
            assert device is pump_in_poller
            assert update.channel == "read"
            assert update.pv_name == "SP1FilledVolume"
            assert update.value == 3
            assert pump_in_poller._epics.cache_key_for(update.channel) == "value"
            assert pump_in_daemon._cache.get(pump_in_daemon, "value") == 3

    def test_linked_daemon_device_ok(self, linked_pumping_in_daemon, fake_backend):
        assert linked_pumping_in_daemon.read(maxage=0) == "Manual"
        assert linked_pumping_in_daemon.status()[0] == status.OK

    def test_linked_start_updates_pvs(self, linked_pumping_in_daemon, fake_backend):
        linked_pumping_in_daemon.start("Time")
        assert fake_backend.values["LnkdStopMode-SP"] == "Time"
        assert fake_backend.values["LnkdStart-Cmd"] == 1

"""Harness tests for the Anton-Paar MCR 702e rheometer composite device.

Each test builds a daemon+poller pair sharing one cache (``create_pair``), so we
exercise the real split: the poller owns the PV subscriptions while the daemon
issues commands, and both coexist over the same cache.

These focus on the contract the GUI panel relies on:
- PV names are built from ``pv_root`` + suffix (no hardcoded full PVs)
- every non-command PV is published (by the poller) to its logical cache key
- writes go (through the daemon) to the right PV via ``set_pv`` / usermethods
"""

import numpy
import pytest

from nicos.core import UsageError, status
from nicos_ess.devices.epics import ap_rheometer
from nicos_ess.devices.epics.ap_rheometer import RheometerControl

ROOT = "SE-SEE:SE-RHEO-001:"


def pv(suffix):
    return ROOT + suffix


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    return fake_epics_backend_factory(ap_rheometer)


def _create_pair(device_harness):
    """Return (daemon_device, poller_device) sharing one cache and backend."""
    return device_harness.create_pair(
        RheometerControl, name="rheo", shared={"pv_root": ROOT}
    )


class TestRheometerControlHarness:
    def test_pv_built_from_root_and_suffix(self, device_harness, fake_backend):
        daemon, _poller = _create_pair(device_harness)

        assert device_harness.run("daemon", daemon._pv, "torque") == pv("Torque-R")
        assert device_harness.run("daemon", daemon._pv, "interv_mode") == pv(
            "IntervMode"
        )

    def test_only_poller_subscribes_and_skips_command_pvs(
        self, device_harness, fake_backend
    ):
        _create_pair(device_harness)

        subscribed = {token[0] for token in fake_backend.subscriptions}

        assert pv("Torque-R") in subscribed
        assert pv("IntervMode") in subscribed
        assert pv("EnableStress") in subscribed
        assert pv("Start") not in subscribed
        assert pv("IntervAdd") not in subscribed
        expected = (
            len(ap_rheometer._CONFIG_FIELDS)
            + len(ap_rheometer._ENABLE_FIELDS)
            + len(ap_rheometer._READBACK_FIELDS)
        )
        assert len(fake_backend.subscriptions) == expected

    def test_poller_value_callback_publishes_under_logical_cache_key(
        self, device_harness, fake_backend
    ):
        _daemon, poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("Torque-R"), value=1.5)

        assert device_harness.run(
            "poller", poller._cache.get, poller, "torque"
        ) == pytest.approx(1.5)

    def test_char_waveform_readback_is_decoded_to_string(
        self, device_harness, fake_backend
    ):
        _daemon, poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("#IntervRawTable"), value=numpy.array([65, 66, 67]))

        assert (
            device_harness.run("poller", poller._cache.get, poller, "interv_raw_table")
            == "ABC"
        )

    def test_daemon_reads_measurement_number_from_poller_cache(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("MeasNumb-R"), value=3.0)

        assert device_harness.run("daemon", daemon.doRead, 0) == pytest.approx(3.0)

    def test_daemon_status_is_busy_while_poller_sees_measuring(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("MeasState"), value=1)  # Running

        assert device_harness.run("daemon", daemon.doStatus, 0) == (
            status.BUSY,
            "measuring",
        )

    def test_poller_callbacks_update_value_and_status_cache_without_read(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("MeasState"), value=1)  # Running
        fake_backend.emit_update(pv("MeasNumb-R"), value=4.0)

        assert device_harness.run(
            "daemon", daemon._cache.get, daemon, "value"
        ) == pytest.approx(4.0)
        assert device_harness.run("daemon", daemon._cache.get, daemon, "status") == (
            status.BUSY,
            "measuring",
        )

    def test_daemon_set_pv_writes_configuration_pv(self, device_harness, fake_backend):
        daemon, _poller = _create_pair(device_harness)

        device_harness.run("daemon", daemon.set_pv, "interv_mode", "Oscillation")

        assert (pv("IntervMode"), "Oscillation", False) in fake_backend.put_calls

    def test_set_pv_rejects_non_configuration_keys(self, device_harness, fake_backend):
        daemon, _poller = _create_pair(device_harness)

        with pytest.raises(UsageError):
            device_harness.run("daemon", daemon.set_pv, "torque", 1)
        with pytest.raises(UsageError):
            device_harness.run("daemon", daemon.set_pv, "does_not_exist", 1)

    def test_daemon_command_usermethods_pulse_their_pv(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        device_harness.run("daemon", daemon.add_interval)
        device_harness.run("daemon", daemon.clear_intervals)
        device_harness.run("daemon", daemon.clear_err)

        assert (pv("IntervAdd"), 1, False) in fake_backend.put_calls
        assert (pv("IntervClear"), 1, False) in fake_backend.put_calls
        assert (pv("ClearErrMsg"), 1, False) in fake_backend.put_calls

    def test_public_start_and_stop_drive_command_pvs(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        device_harness.run("daemon", daemon.start)
        device_harness.run("daemon", daemon.stop)

        assert (pv("Start"), 1, False) in fake_backend.put_calls
        assert (pv("Stop"), 1, False) in fake_backend.put_calls

    def test_get_choices_returns_backend_enum_choices(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)
        fake_backend.value_choices[pv("IntervMode")] = ["Viscometry", "Oscillation"]

        assert device_harness.run("daemon", daemon.get_choices, "interv_mode") == [
            "Viscometry",
            "Oscillation",
        ]

    def test_daemon_status_reflects_cached_error_message(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("ErrMsg"), value="overload")

        assert device_harness.run("daemon", daemon.doStatus, 0) == (
            status.WARN,
            "overload",
        )

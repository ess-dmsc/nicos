"""Harness tests for the Anton-Paar MCR 702e rheometer composite device."""

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
    backend = fake_epics_backend_factory(ap_rheometer)
    # Volatile params are read once per device at init, so every PV backing one
    # must answer (the real IOC always serves them).
    for suffix in ap_rheometer._READBACK_FIELDS.values():
        backend.values[ROOT + suffix] = 0.0
    backend.values[ROOT + ap_rheometer._CONFIG_FIELDS["temp_setpoint"]] = 0.0
    return backend


def _create_pair(device_harness):
    """Return (daemon_device, poller_device) sharing one cache and backend."""
    return device_harness.create_pair(
        RheometerControl, name="rheo", shared={"pv_root": ROOT}
    )


class TestRheometerControlHarness:
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

    def test_daemon_status_reflects_cached_error_message(
        self, device_harness, fake_backend
    ):
        daemon, _poller = _create_pair(device_harness)

        fake_backend.emit_update(pv("ErrMsg"), value="overload")

        assert device_harness.run("daemon", daemon.doStatus, 0) == (
            status.WARN,
            "overload",
        )

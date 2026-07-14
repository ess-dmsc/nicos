import pytest

from nicos_ess.devices.epics import pulse_counter

READ_PV = "SIM:PULSE"


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    backend = fake_epics_backend_factory(pulse_counter)
    backend.values[READ_PV] = 100
    return backend


@pytest.fixture
def counter(device_harness, fake_backend):
    del fake_backend
    return device_harness.create(
        "poller",
        pulse_counter.PulseCounter,
        name="pulse_counter",
        readpv=READ_PV,
    )


def test_start_uses_current_pulse_count_as_zero(device_harness, fake_backend, counter):
    device_harness.run("poller", counter.doStart)

    assert device_harness.run("poller", counter.doRead) == 0

    fake_backend.emit_update(READ_PV, value=107)

    assert device_harness.run("poller", counter.doRead) == 7


def test_update_after_finish_does_not_change_count(
    device_harness, fake_backend, counter
):
    device_harness.run("poller", counter.doStart)
    fake_backend.emit_update(READ_PV, value=107)
    device_harness.run("poller", counter.doFinish)
    fake_backend.emit_update(READ_PV, value=110)

    assert device_harness.run("poller", counter.doRead) == 7

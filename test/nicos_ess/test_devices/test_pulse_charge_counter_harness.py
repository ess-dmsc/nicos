import pytest

from nicos_ess.devices.epics import pulse_charge_counter

READ_PV = "SIM:CHARGE"


@pytest.fixture
def fake_backend(fake_epics_backend_factory):
    backend = fake_epics_backend_factory(pulse_charge_counter)
    backend.values[READ_PV] = 0.0
    return backend


@pytest.fixture
def counter(device_harness, fake_backend):
    daemon_counter, _poller_counter = device_harness.create_pair(
        pulse_charge_counter.PulseChargeCounter,
        name="pulse_charge_counter",
        shared={"readpv": READ_PV, "reset_count_pv": "SIM:RESET"},
    )
    return daemon_counter


def test_charge_updates_are_counted(counter, fake_backend):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    assert counter.read() == [7.5]


def test_start_clears_previous_charge(counter, fake_backend):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    counter.finish()
    assert counter.read() == [7.5]
    counter.start()
    assert counter.read() == [0.0]


def test_old_charge_before_reset_completes_is_not_counted(counter, fake_backend):
    # ioc has some old value at t=0, monitor callback is in flight
    fake_backend.values[READ_PV] = 100.0
    # we start the counter, which will reset the charge counter in the IOC
    counter.start()
    # the monitor callback is called with the old value, but we should ignore it
    fake_backend.emit_update(READ_PV)
    assert counter.read() == [0.0]


def test_updates_after_finish_do_not_change_charge(counter, fake_backend):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    counter.finish()
    fake_backend.emit_update(READ_PV, value=9.5)
    assert counter.read() == [7.5]

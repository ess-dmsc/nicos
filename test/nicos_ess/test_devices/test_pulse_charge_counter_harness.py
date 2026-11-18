import time

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
        shared={"readpv": READ_PV},
    )
    return daemon_counter


def test_charge_updates_are_counted(counter, fake_backend):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    assert counter.read() == [7.5]


def test_start_clears_previous_charge(device_harness, counter, fake_backend):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    device_harness.run_daemon(counter.finish)
    assert counter.read() == [7.5]
    counter.prepare()
    counter.start()
    assert counter.read() == [0.0]


def test_value_repeated_on_reconnect_is_not_counted(counter, fake_backend):
    fake_backend.values[READ_PV] = 100.0
    counter.prepare()
    counter.start()
    fake_backend.emit_connection(READ_PV, True)
    fake_backend.emit_update(READ_PV)
    assert counter.read() == [0.0]


def test_updates_after_finish_do_not_change_charge(
    device_harness, counter, fake_backend
):
    counter.start()
    fake_backend.emit_update(READ_PV, value=7.5)
    device_harness.run_daemon(counter.finish)
    fake_backend.emit_update(READ_PV, value=9.5)
    assert counter.read() == [7.5]


def test_pulse_that_arrived_before_start_is_not_counted(
    device_harness, counter, fake_backend
):
    counter.prepare()
    before = time.time()
    counter.start()
    # arrived before the start, reaches the daemon only now
    poller = device_harness.get_device("poller", "pulse_charge_counter")
    device_harness.run_poller(poller._cache.put, poller._name, "total", 4.0, before)

    fake_backend.emit_update(READ_PV, value=6.0)
    assert counter.read() == [6.0]


def test_pulse_that_arrived_after_the_end_is_not_counted(
    device_harness, counter, fake_backend
):
    counter.prepare()
    counter.start()
    fake_backend.emit_update(READ_PV, value=6.0)
    with device_harness.activate("daemon") as session:
        original_delay = session.delay

        def delay_with_pulse(seconds):
            session.delay = original_delay
            fake_backend.emit_update(READ_PV, value=9.0)
            original_delay(seconds)

        session.delay = delay_with_pulse
        counter.finish()
    assert counter.total == 15.0
    assert counter.read() == [6.0]


def test_back_to_back_counts_are_separate(device_harness, counter, fake_backend):
    for charge in (5.0, 7.0):
        counter.prepare()
        counter.start()
        fake_backend.emit_update(READ_PV, value=charge)
        device_harness.run_daemon(counter.finish)
        assert counter.read() == [charge]


def test_device_value_follows_the_count(counter, fake_backend):
    counter.prepare()
    counter.start()
    fake_backend.emit_update(READ_PV, value=3.0)
    assert counter._cache.get(counter, "value") == 3.0
    fake_backend.emit_update(READ_PV, value=2.0)
    assert counter._cache.get(counter, "value") == 5.0


def test_stop_does_not_wait(device_harness, counter, fake_backend):
    counter.prepare()
    counter.start()
    fake_backend.emit_update(READ_PV, value=6.0)
    with device_harness.activate("daemon") as session:

        def no_delay(seconds):
            raise AssertionError("stop must not wait")

        session.delay = no_delay
        counter.stop()
    assert counter.read() == [6.0]

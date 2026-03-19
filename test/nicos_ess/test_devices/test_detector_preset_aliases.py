from nicos_ess.devices.epics.counter import EpicsCounter
from nicos_ess.devices.epics.pulse_counter import PulseCounter


def test_epics_counter_supports_standalone_n_preset_alias(daemon_device_harness):
    counter = daemon_device_harness.create_sim(
        EpicsCounter,
        name="epics_counter",
        readpv="SIM:COUNTER",
    )

    assert "n" in counter.presetInfo()


def test_pulse_counter_supports_standalone_n_preset_alias(daemon_device_harness):
    counter = daemon_device_harness.create_sim(
        PulseCounter,
        name="pulse_counter",
        readpv="SIM:PULSE",
    )

    assert "n" in counter.presetInfo()

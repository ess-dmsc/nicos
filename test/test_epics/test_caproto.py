"""Value and alarm reads through the Channel Access transport."""

from types import SimpleNamespace

import pytest
from caproto import CaprotoTimeoutError

from nicos.core import status
from nicos.devices.epics.pva import caproto


class Channel:
    def __init__(self, value, severity=0, alarm=0):
        self.response = SimpleNamespace(
            data=[value], metadata=SimpleNamespace(severity=severity, status=alarm)
        )
        self.failure = None

    def read(self, **kwargs):
        if self.failure:
            raise self.failure
        return self.response


class Context:
    def __init__(self, channels):
        self.channels = channels

    def get_pvs(self, name, **kwargs):
        return [self.channels[name]]


@pytest.fixture
def ca_readings(monkeypatch):
    channels = {"PV:VOLTAGE": Channel(12.5, 2, 3), "PV:POWER": Channel(1)}
    # Replace the CA network context so the test needs no external IOC.
    monkeypatch.setattr(caproto, "_Context", Context(channels))
    return caproto.CaprotoWrapper(), channels


def test_readings_include_values_and_alarms(ca_readings):
    wrapper, channels = ca_readings
    assert wrapper.get_pv_readings({"PV:VOLTAGE": False, "PV:POWER": True}) == {
        "PV:VOLTAGE": (12.5, (status.ERROR, "HIHI")),
        "PV:POWER": ("1", (status.OK, "")),
    }
    channels["PV:VOLTAGE"].response.data = [0.0]
    assert wrapper.get_pv_readings({"PV:VOLTAGE": False})["PV:VOLTAGE"][0] == 0.0


def test_readings_fail_on_a_disconnected_pv(ca_readings):
    wrapper, channels = ca_readings
    wrapper.get_pv_readings({"PV:VOLTAGE": False, "PV:POWER": False})
    channels["PV:POWER"].failure = CaprotoTimeoutError()
    with pytest.raises(TimeoutError, match="PV:POWER"):
        wrapper.get_pv_readings({"PV:VOLTAGE": False, "PV:POWER": False})

import pytest

from nicos.core import (
    MASTER,
    SIMULATION,
    SLAVE,
    AccessError,
    CanDisable,
    ModeError,
    Moveable,
    status,
)
from nicos_ess.devices.mixins import EventDrivenCanDisable


class EventDrivenDisableDevice(EventDrivenCanDisable, Moveable):
    valuetype = float
    hardware_access = True

    def doPreinit(self, mode):
        self._enable_calls = []
        self._poll_calls = 0

    def doRead(self, maxage=0):
        return 0.0

    def doReadTarget(self):
        return 0.0

    def doStart(self, target):
        pass

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doEnable(self, on):
        self._enable_calls.append(on)

    def poll(self, n=0, maxage=0):
        self._poll_calls += 1
        return super().poll(n, maxage)


def create_device(device_harness, *, mode=MASTER, **config):
    return device_harness.create(
        "daemon",
        EventDrivenDisableDevice,
        name="event_driven_disable",
        mode=mode,
        unit="",
        **config,
    )


def test_event_driven_disable_keeps_can_disable_api_without_automatic_poll(
    device_harness,
):
    device = create_device(device_harness)

    assert isinstance(device, CanDisable)
    device_harness.run_daemon(device.enable)
    device_harness.run_daemon(device.disable)

    assert device._enable_calls == [True, False]
    assert device._poll_calls == 0

    device_harness.run_daemon(device.poll)
    assert device._poll_calls == 1


def test_event_driven_disable_honours_slave_mode(device_harness):
    device = create_device(device_harness, mode=SLAVE)

    with pytest.raises(ModeError, match="enable not possible in slave mode"):
        device_harness.run_daemon(device.enable)

    assert device._enable_calls == []
    assert device._poll_calls == 0


def test_event_driven_disable_honours_access_requirements(device_harness):
    device = create_device(device_harness, requires={"mode": "maintenance"})

    with pytest.raises(AccessError, match="cannot enable device"):
        device_harness.run_daemon(device.enable)

    assert device._enable_calls == []
    assert device._poll_calls == 0


def test_event_driven_disable_is_a_noop_in_simulation(device_harness):
    device = create_device(device_harness, mode=SIMULATION)

    device_harness.run_daemon(device.enable)

    assert device._enable_calls == []
    assert device._poll_calls == 0

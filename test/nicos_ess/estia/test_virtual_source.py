import pytest

from nicos.devices.generic.slit import Slit
from nicos_ess.estia.devices.virtual_source import LaserMacro, VirtualSource
from test.nicos_ess.test_devices.doubles import HarnessLinearAxis


class TestVirtualSourceAndLaser:
    # laser and virtual source are tested together since they share motors

    def test_opmode_change_on_vs(self, estia_virtual_source_setup):
        devices = estia_virtual_source_setup

        assert devices["virtual_source"].opmode == "4blades"


def _create_master(daemon_device_harness, devcls, /, *args, **kwargs):
    """Create devices in master mode so doStart/doStatus logic is exercised."""
    return daemon_device_harness.create_master(devcls, *args, **kwargs)


@pytest.fixture
def estia_virtual_source_setup(daemon_device_harness):
    top = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="top",
        abslimits=(-12.5, 12.5),
        precision=0.1,
        initial_value=0,
    )
    bottom = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="bottom",
        abslimits=(-12.5, 12.5),
        precision=0.1,
        initial_value=0,
    )
    left = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="left",
        abslimits=(-25.5, -0.5),
        precision=0.1,
        initial_value=-0.5,
    )
    right = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="right",
        abslimits=(0.5, 25.5),
        precision=0.1,
        initial_value=0.5,
    )
    rotation = _create_master(
        daemon_device_harness,
        HarnessLinearAxis,
        name="rotation",
        abslimits=(-1.5, 16),
        precision=0.1,
        initial_value=0,
    )
    slit = _create_master(
        daemon_device_harness,
        Slit,
        name="slit",
        opmode="4blades",
        left="left",
        right="right",
        bottom="bottom",
        top="top",
    )
    virtual_source = _create_master(
        daemon_device_harness,
        VirtualSource,
        name="virtual_source",
        slit="slit",
        rot="rotation",
        opmode="4blades",
    )
    laser_ctrl = _create_master(
        daemon_device_harness,
        LaserMacro,
        name="laser_ctrl",
        blade_v="bottom",
        angle="rotation",
        mapping={"On": (11.5, 5), "Off": (0, 0)},
    )
    devices = {
        "top": top,
        "bottom": bottom,
        "left": left,
        "right": right,
        "rotation": rotation,
        "slit": slit,
        "virtual_source": virtual_source,
        "laser_ctrl": laser_ctrl,
    }
    return devices

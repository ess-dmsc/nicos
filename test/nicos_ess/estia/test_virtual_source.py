import pytest

from nicos.commands.device import move, set
from nicos.core.errors import InvalidValueError
from nicos.devices.generic.slit import Slit
from nicos_ess.estia.devices.virtual_source import LaserMacro, VirtualSource
from test.nicos_ess.test_devices.doubles import HarnessLinearAxis


class TestVirtualSourceAndLaserHarness:
    # laser and virtual source are tested together since they share motors
    adevs = ("left", "right", "bottom", "top", "rot")

    @pytest.mark.parametrize(
        ("target", "opmode", "result"),
        [
            pytest.param([1, 2, 3, 4, 5], "4blades", [[1, 2, 3, 4], 5]),
            pytest.param([1, 2, 3], "centered", [[1, 2], 3]),
        ],
    )
    def test_ensure_parse_target_follows_opmode(
        self, estia_virtual_source_setup, target, opmode, result
    ):
        devices = estia_virtual_source_setup
        set(devices["virtual_source"], "opmode", opmode)

        parsed_targets = devices["virtual_source"]._parseTargets(target)

        assert parsed_targets == result

    def test_opmode_change_on_vs_syncs_slit(self, estia_virtual_source_setup):
        devices = estia_virtual_source_setup

        assert devices["slit"].opmode == devices["virtual_source"].opmode

        set(devices["virtual_source"], "opmode", "4blades_opposite")
        assert devices["virtual_source"].opmode == "4blades_opposite"

        devices["virtual_source"]._syncOpmode(
            devices["slit"].opmode, devices["virtual_source"].opmode
        )
        assert devices["slit"].opmode == devices["virtual_source"].opmode

    def test_opmode_change_on_slit_prioritizes_vs(self, estia_virtual_source_setup):
        devices = estia_virtual_source_setup

        assert devices["slit"].opmode == devices["virtual_source"].opmode

        set(devices["slit"], "opmode", "4blades_opposite")
        assert devices["slit"].opmode == "4blades_opposite"

        devices["virtual_source"]._syncOpmode(
            devices["slit"].opmode, devices["virtual_source"].opmode
        )
        assert devices["virtual_source"].opmode == "4blades"
        assert devices["slit"].opmode == "4blades"

    @pytest.mark.parametrize(
        "limits",
        [
            pytest.param(
                {
                    "left": (-25.5, -0.5),
                    "right": (0.5, 25.5),
                    "bottom": (-12.5, 12.5),
                    "top": (-12.5, 12.5),
                    "rot": (-1.5, 16),
                },
                id="initial limits are equivalent",
            ),
            pytest.param(
                {
                    "left": (-10, -5),
                    "right": (5, 10),
                    "bottom": (-5, 5),
                    "top": (-3, 3),
                    "rot": (0, 3),
                },
                id="change limits on vs change blade limits",
            ),
        ],
    )
    def test_vs_userlimit_param_matches_adevs(self, estia_virtual_source_setup, limits):
        devices = estia_virtual_source_setup
        set(devices["virtual_source"], "motorlimits", limits)

        assert devices["virtual_source"].motorlimits == limits

        for adev_name in limits:
            if adev_name != "rot":
                assert devices[adev_name].userlimits == limits[adev_name]
            else:
                assert devices["rotation"].userlimits == limits[adev_name]

    @pytest.mark.parametrize(
        "limits",
        [
            pytest.param(
                {
                    "left": (-50, -0.5),  # error limit
                    "right": (0.5, 25.5),
                    "bottom": (-12.5, 12.5),
                    "top": (-12.5, 12.5),
                    "rot": (-1.5, 200),  # error limit
                },
                id="setting limits outside abslimits throws error",
            ),
            pytest.param(
                {
                    "left": (-25.5, -0.5),
                    "right": (0.5, 25.5),
                    "bottom": (12.5, -12.5),  # error limit
                    "top": (-12.5, 12.5),
                    "rot": (-1.5, 16),
                },
                id="error when min > max",
            ),
        ],
    )
    def test_user_cannot_set_invalid_userlimits(
        self, estia_virtual_source_setup, limits
    ):
        devices = estia_virtual_source_setup
        with pytest.raises(InvalidValueError):
            set(devices["virtual_source"], "motorlimits", limits)

    def test_preinit_collects_limits_from_adevs(self, estia_virtual_source_setup):
        devices = estia_virtual_source_setup

        devices["virtual_source"].doPreinit(mode="sim")

        for device in self.adevs:
            if device != "rot":
                assert (
                    devices["virtual_source"].motorlimits[device]
                    == devices[device].userlimits
                )
            else:
                assert (
                    devices["virtual_source"].motorlimits["rot"]
                    == devices["rotation"].userlimits
                )

    # ------ Laser Macro ------ #

    @pytest.mark.parametrize(
        ("v_pos", "r_pos", "map_pos", "msg"),
        [
            pytest.param(
                -12,
                16,
                "On",
                "Laser in Position",
                id="Laser in position",
            ),
            pytest.param(
                -12,
                16,
                "Off",
                "Off",
                id="Laser Reset to last known pos",
            ),
        ],
    )
    def test_laser_moves_to_correct_position(
        self, estia_virtual_source_setup, v_pos, r_pos, map_pos, msg
    ):
        devices = estia_virtual_source_setup
        mapping = devices["laser_ctrl"].mapping
        devices["bottom"].start(v_pos)
        devices["rotation"].start(r_pos)

        move(devices["laser_ctrl"], map_pos)

        assert (
            devices["laser_ctrl"]().startswith(msg)
            and devices["laser_ctrl"]._adevs["blade_v"].read() == mapping[map_pos][0]
            and devices["laser_ctrl"]._adevs["angle"].read() == mapping[map_pos][1]
        )

    def test_laser_updates_off_position_on_move(self, estia_virtual_source_setup):
        devices = estia_virtual_source_setup

        assert devices["laser_ctrl"].mapping == {"On": (11.5, 5), "Off": (0, 0)}

        devices["bottom"].start(-10)
        devices["rotation"].start(-1.5)
        devices["laser_ctrl"]._updateLastKnownPos()

        assert devices["laser_ctrl"].mapping == {"On": (11.5, 5), "Off": (-10, -1.5)}


# ----------Harness Device Setup-------------#


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

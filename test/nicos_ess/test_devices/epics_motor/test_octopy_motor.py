from nicos.core import status
from nicos_ess.devices.epics.pva.octopy_motor import OctopyMotor

MOTOR_PV = "SIM:OCT"


def pv(suffix):
    return f"{MOTOR_PV}{suffix}"


def seed_octopy_pvs(fake_backend):
    defaults = {
        "-position-r": 1.0,
        "-s": 1.0,
        "-halt-s": 0,
        "-velocity-s": 2.0,
        "-enable-s": 1,
        "-home-s": 0,
        "-reset-s": 0,
        "-busy-r": 0,
        "-move_done-r": 1,
    }
    for suffix, value in defaults.items():
        fake_backend.values[pv(suffix)] = value


def create_octopy_pair(device_harness):
    return device_harness.create_pair(
        OctopyMotor,
        name="octopy",
        shared={
            "motorpv": MOTOR_PV,
            "precision": 0.01,
            "speed": 2.0,
            "unit": "mm",
            "warnlimits": (-100.0, 100.0),
            "monitor": True,
        },
    )


class TestOctopyMotor:
    def test_read_respects_maxage_through_public_read(
        self, device_harness, fake_backend
    ):
        seed_octopy_pvs(fake_backend)
        daemon_device, _poller_device = create_octopy_pair(device_harness)

        fake_backend.emit_update(pv("-position-r"), value=4.0)
        fake_backend.values[pv("-position-r")] = 9.0

        assert device_harness.run_daemon(daemon_device.read, None) == 4.0
        assert device_harness.run_daemon(daemon_device.read, 0) == 9.0

    def test_volatile_speed_parameter_reads_hardware(
        self, device_harness, fake_backend
    ):
        seed_octopy_pvs(fake_backend)
        daemon_device, _poller_device = create_octopy_pair(device_harness)

        fake_backend.emit_update(pv("-velocity-s"), value=2.0)
        fake_backend.values[pv("-velocity-s")] = 7.0

        assert device_harness.run_daemon(daemon_device.doReadSpeed) == 7.0

    def test_status_respects_maxage_through_status_hook(
        self, device_harness, fake_backend
    ):
        seed_octopy_pvs(fake_backend)
        daemon_device, _poller_device = create_octopy_pair(device_harness)

        fake_backend.emit_update(pv("-s"), value=5.0)
        fake_backend.emit_update(pv("-busy-r"), value=1)
        fake_backend.emit_update(pv("-move_done-r"), value=0)
        fake_backend.values[pv("-busy-r")] = 0
        fake_backend.values[pv("-move_done-r")] = 1
        fake_backend.values[pv("-s")] = 5.0

        assert device_harness.run_daemon(daemon_device.status, None) == (
            status.BUSY,
            "moving to 5.0",
        )
        assert device_harness.run_daemon(daemon_device.doStatus, 0) == (
            status.OK,
            "ready",
        )

    def test_connection_loss_reports_unknown(self, device_harness, fake_backend):
        seed_octopy_pvs(fake_backend)
        daemon_device, _poller_device = create_octopy_pair(device_harness)

        fake_backend.disconnect_backend()

        assert device_harness.run_daemon(daemon_device.status) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )

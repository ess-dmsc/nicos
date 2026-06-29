import pytest

from nicos.core import status
from nicos_ess.devices.epics import syringe_pump
from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.devices.epics.pva.epics_devices import EpicsMappedReadable
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend

PV_ROOT = "SIM:SYR:"

STATE_CHOICES = [
    "Infusing",
    "Withdrawing",
    "Stopped",
    "Paused",
    "Pause phase",
    "Trigger wait",
    "Purging",
    "Unknown",
]


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(
        epics_common, "create_wrapper", lambda timeout, use_pva: backend
    )

    backend.values[f"{PV_ROOT}STATUS"] = STATE_CHOICES.index("Stopped")
    backend.value_choices[f"{PV_ROOT}STATUS"] = STATE_CHOICES
    backend.values[f"{PV_ROOT}MESSAGE"] = ""
    backend.values[f"{PV_ROOT}START"] = 0
    backend.values[f"{PV_ROOT}STOP"] = 0
    backend.values[f"{PV_ROOT}PURGE"] = 0
    backend.values[f"{PV_ROOT}PAUSE"] = 0
    return backend


@pytest.fixture
def attached_status_device(device_harness, fake_backend):
    del fake_backend
    device_harness.create_pair(
        EpicsMappedReadable,
        name="syringe_status",
        shared={
            "readpv": f"{PV_ROOT}STATUS",
            "monitor": True,
            "pva": True,
        },
    )


class TestSyringePumpControllerHarness:
    def _create_pair(self, device_harness):
        return device_harness.create_pair(
            syringe_pump.SyringePumpController,
            name="syringe_pump",
            shared={
                "start_pv": f"{PV_ROOT}START",
                "stop_pv": f"{PV_ROOT}STOP",
                "purge_pv": f"{PV_ROOT}PURGE",
                "pause_pv": f"{PV_ROOT}PAUSE",
                "message_pv": f"{PV_ROOT}MESSAGE",
                "status": "syringe_status",
                "monitor": True,
                "pva": True,
            },
        )

    def test_initializes(self, device_harness, fake_backend, attached_status_device):
        del fake_backend, attached_status_device
        daemon_device, poller_device = self._create_pair(device_harness)

        assert daemon_device is not None
        assert poller_device is not None

    def test_read_returns_attached_state(
        self, device_harness, fake_backend, attached_status_device
    ):
        del fake_backend, attached_status_device
        daemon_device, _poller_device = self._create_pair(device_harness)

        assert daemon_device.read(0) == "Stopped"

    def test_start_command_writes_start_pv(
        self, device_harness, fake_backend, attached_status_device
    ):
        del attached_status_device
        daemon_device, _poller_device = self._create_pair(device_harness)

        daemon_device.move("start")

        assert fake_backend.values[f"{PV_ROOT}START"] == 1

    def test_error_message_gives_error_status(
        self, device_harness, fake_backend, attached_status_device
    ):
        del attached_status_device
        daemon_device, _poller_device = self._create_pair(device_harness)

        fake_backend.emit_update(f"{PV_ROOT}MESSAGE", value="syringe stuck")

        assert daemon_device.status() == (status.ERROR, "syringe stuck")

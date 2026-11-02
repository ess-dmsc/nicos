import pytest

from nicos.core import MAIN, SIMULATION, SLAVE, status
from nicos_ess.devices import sample_environment
from nicos_ess.devices.sample_environment import (
    SampleEnvironmentPresence,
    presence_signals,
)
from test.nicos_ess.device_harness import UnitTestSession

SETUP_INFO = {
    "lakeshore": {
        "group": "plugplay",
        "extended": {"presence_signal": "pva://LS:KRDG0"},
    },
    "julabo": {
        "group": "plugplay",
        "extended": {"presence_signal": "pva://JUL:TEMP"},
    },
    "secop_box": {
        "group": "plugplay",
        "extended": {"presence_signal": "secop://box:10767"},
    },
    "unsignalled": {"group": "plugplay", "extended": {}},
    "system": {"group": "lowlevel", "extended": {"presence_signal": "pva://SYS"}},
    "broken": None,
}


@pytest.fixture
def fake_backend(monkeypatch, fake_epics_backend_factory):
    monkeypatch.setattr(UnitTestSession, "getSetupInfo", lambda self: SETUP_INFO)
    return fake_epics_backend_factory(sample_environment)


def _monitored_pvs(backend):
    return sorted(token[0] for token in backend.subscriptions)


def _create_pair(device_harness):
    return device_harness.create_pair(SampleEnvironmentPresence, name="se_presence")


def _daemon_read(device_harness, daemon, maxage=None):
    return device_harness.run_daemon(daemon.read, maxage)


def test_presence_signals_are_taken_from_plugplay_setups():
    assert presence_signals(SETUP_INFO) == {
        "lakeshore": "pva://LS:KRDG0",
        "julabo": "pva://JUL:TEMP",
        "secop_box": "secop://box:10767",
    }


def test_only_the_poller_monitors_the_pva_signals(device_harness, fake_backend):
    _create_pair(device_harness)

    assert _monitored_pvs(fake_backend) == ["JUL:TEMP", "LS:KRDG0"]


def test_daemon_reads_what_the_poller_reports(device_harness, fake_backend):
    daemon, _ = _create_pair(device_harness)

    fake_backend.emit_connection("LS:KRDG0", True)
    fake_backend.emit_connection("JUL:TEMP", True)
    assert _daemon_read(device_harness, daemon) == ["julabo", "lakeshore"]

    fake_backend.emit_connection("LS:KRDG0", False)
    assert _daemon_read(device_harness, daemon) == ["julabo"]


def test_daemon_read_without_cache_age_uses_the_poller_value(
    device_harness, fake_backend
):
    daemon, _ = _create_pair(device_harness)

    fake_backend.emit_connection("LS:KRDG0", True)

    assert _daemon_read(device_harness, daemon, maxage=0) == ["lakeshore"]


def test_daemon_reads_never_write_the_cache(device_harness, fake_backend, monkeypatch):
    daemon, _ = _create_pair(device_harness)
    fake_backend.emit_connection("LS:KRDG0", True)
    writes = []
    monkeypatch.setattr(daemon._cache, "put", lambda *args, **kw: writes.append(args))

    _daemon_read(device_harness, daemon)
    _daemon_read(device_harness, daemon, maxage=0)
    device_harness.run_daemon(daemon.status, 0)

    assert writes == []


def test_slave_daemon_sees_the_same_list(device_harness, fake_backend):
    device_harness.create_poller(SampleEnvironmentPresence, "se_presence")
    slave = device_harness.create(
        device_harness.DAEMON_ROLE,
        SampleEnvironmentPresence,
        "se_presence",
        mode=SLAVE,
        sessiontype=MAIN,
    )

    fake_backend.emit_connection("JUL:TEMP", True)

    assert _daemon_read(device_harness, slave) == ["julabo"]


def test_daemon_started_late_reads_the_present_list(device_harness, fake_backend):
    device_harness.create_poller(SampleEnvironmentPresence, "se_presence")
    fake_backend.emit_connection("LS:KRDG0", True)

    daemon = device_harness.create_daemon(SampleEnvironmentPresence, "se_presence")

    assert _daemon_read(device_harness, daemon) == ["lakeshore"]


def test_equipment_coming_back_is_present_again(device_harness, fake_backend):
    daemon, _ = _create_pair(device_harness)

    fake_backend.emit_connection("LS:KRDG0", True)
    fake_backend.emit_connection("LS:KRDG0", False)
    fake_backend.emit_connection("LS:KRDG0", True)

    assert _daemon_read(device_harness, daemon) == ["lakeshore"]


def test_status_is_ok_while_the_poller_runs(device_harness, fake_backend):
    daemon, poller = _create_pair(device_harness)
    device_harness.run_poller(poller.poll)

    assert device_harness.run_daemon(daemon.status, 0) == (status.OK, "")


def test_poller_shutdown_closes_the_monitors(device_harness, fake_backend):
    _, poller = _create_pair(device_harness)

    device_harness.run_poller(poller.shutdown)

    assert fake_backend.subscriptions == []


def test_nothing_is_monitored_in_simulation(device_harness, fake_backend):
    device_harness.create(
        device_harness.POLLER_ROLE, SampleEnvironmentPresence, mode=SIMULATION
    )

    assert fake_backend.subscriptions == []

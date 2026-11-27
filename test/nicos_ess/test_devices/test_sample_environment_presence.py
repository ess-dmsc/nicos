import random
import threading

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


SETUP_BY_PV = {
    f"{name.upper()}:PV": f"setup_{name}"
    for name in ("kappa", "alpha", "omega", "delta", "zeta", "beta", "theta", "eta")
}

MANY_SETUPS = {
    setup: {"group": "plugplay", "extended": {"presence_signal": f"pva://{pv}"}}
    for pv, setup in SETUP_BY_PV.items()
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


def test_poller_poll_keeps_the_present_list(device_harness, fake_backend):
    daemon, poller = _create_pair(device_harness)
    fake_backend.emit_connection("LS:KRDG0", True)
    fake_backend.emit_connection("JUL:TEMP", True)

    device_harness.run_poller(poller.poll)

    assert device_harness.run_poller(poller.read, 0) == ["julabo", "lakeshore"]
    assert _daemon_read(device_harness, daemon) == ["julabo", "lakeshore"]


def test_random_connection_changes_match_a_model(
    device_harness, fake_backend, monkeypatch
):
    monkeypatch.setattr(UnitTestSession, "getSetupInfo", lambda self: MANY_SETUPS)
    rng = random.Random(1)
    daemon, poller = _create_pair(device_harness)
    connected = set()

    for _ in range(500):
        pv = rng.choice(sorted(SETUP_BY_PV))
        is_connected = rng.random() < 0.6
        fake_backend.emit_connection(pv, is_connected)
        if is_connected:
            connected.add(SETUP_BY_PV[pv])
        else:
            connected.discard(SETUP_BY_PV[pv])
        if rng.random() < 0.2:
            device_harness.run_poller(poller.poll)

        # The daemon reads first, because a poller read writes its value to the cache.
        assert _daemon_read(device_harness, daemon, maxage=0) == sorted(connected)
        assert device_harness.run_poller(poller.read, 0) == sorted(connected)


def test_cache_gets_the_latest_list_when_callbacks_overlap(
    device_harness, fake_backend, monkeypatch
):
    daemon, poller = _create_pair(device_harness)
    put = poller._cache.put
    first_put_started = threading.Event()
    release_first_put = threading.Event()

    def blocking_put(*args, **kwargs):
        if not first_put_started.is_set():
            first_put_started.set()
            release_first_put.wait(5)
        put(*args, **kwargs)

    monkeypatch.setattr(poller._cache, "put", blocking_put)

    lakeshore = threading.Thread(
        target=fake_backend.emit_connection, args=("LS:KRDG0", True)
    )
    lakeshore.start()
    first_put_started.wait(5)
    julabo = threading.Thread(
        target=fake_backend.emit_connection, args=("JUL:TEMP", True)
    )
    julabo.start()
    # The julabo callback either finishes or waits for the lakeshore one.
    julabo.join(0.5)
    release_first_put.set()
    lakeshore.join(5)
    julabo.join(5)

    assert _daemon_read(device_harness, daemon) == ["julabo", "lakeshore"]

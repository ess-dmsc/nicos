"""Contracts pinned by the ESS GUI fake daemon.

The fake is allowed to be small, but it must stay compatible with the real
``NicosClient`` and ``ClientTransport`` seams used by the GUI tests.
"""

from __future__ import annotations

import inspect
from logging import INFO
from time import monotonic, sleep

import pytest

from nicos.clients.base import ConnectionData, NicosClient
from nicos.clients.proto.classic import ClientTransport as ClassicClientTransport
from nicos.core import MAINTENANCE, MASTER, params
from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import ClientTransport as BaseClientTransport, STATUS_IDLE
from nicos.protocols.daemon.classic import PROTO_VERSION

from test.nicos_ess.gui.doubles import DeviceSpec, FakeClientTransport


class RecordingClient(NicosClient):
    """Concrete ``NicosClient`` driven only through the production API."""

    def __init__(self):
        self.events = []
        self.log_messages = []
        super().__init__(self.log_messages.append)

    def signal(self, name, *args):
        self.events.append((name, args))


def _connect_client(monkeypatch, fake_daemon, *, eventmask=None):
    monkeypatch.setattr(
        "nicos.clients.base.ClientTransport",
        lambda: FakeClientTransport(fake_daemon),
    )
    client = RecordingClient()
    client.connect(ConnectionData("fake", 0, "test", "test"), eventmask=eventmask)
    return client


def _disconnect_client(client):
    if client.isconnected:
        client.disconnect()
    thread = getattr(client, "event_thread", None)
    if thread is not None:
        thread.join(timeout=1.0)
        assert not thread.is_alive()


def _wait_until(predicate, timeout=2.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.01)
    pytest.fail("condition was not met before timeout")


def _event_payloads(client, name):
    return [args[0] for event_name, args in client.events if event_name == name]


def _motor_spec():
    return DeviceSpec(
        name="motor",
        valuetype=float,
        params={
            "value": 1.5,
            "status": (200, ""),
            "visibility": ("namespace", "devlist"),
            "userlimits": (0.0, 5.5),
            "offset": 0.8,
            "classes": ["nicos.core.device.Moveable"],
        },
        param_info={
            "userlimits": {
                "type": params.limits,
                "unit": "main",
                "userparam": True,
            }
        },
    )


def test_fake_transport_implements_the_client_transport_surface_contract():
    required = {
        name
        for name, member in inspect.getmembers(BaseClientTransport, inspect.isfunction)
        if name != "determine_serializer"
    }
    assert required == {
        "connect",
        "connect_events",
        "disconnect",
        "send_command",
        "recv_reply",
        "recv_event",
    }

    for name in sorted(required):
        fake_sig = inspect.signature(getattr(FakeClientTransport, name))
        assert fake_sig == inspect.signature(getattr(ClassicClientTransport, name))


def test_fake_daemon_satisfies_the_real_client_connection_contract(
    monkeypatch, fake_daemon
):
    client = _connect_client(monkeypatch, fake_daemon, eventmask=("cache", "status"))
    try:
        assert client.isconnected is True
        assert client.daemon_info == {
            "daemon_version": fake_daemon.daemon_version,
            "protocol_version": PROTO_VERSION,
            "pw_hashing": "plain",
        }
        assert client.user_level == fake_daemon.user_level
        assert ("connected", ()) in client.events
        assert fake_daemon.command_log[:2] == [
            (
                "authenticate",
                ({"login": "test", "passwd": "test", "display": ""},),
            ),
            ("eventmask", (("cache", "status"),)),
        ]
    finally:
        _disconnect_client(client)

    assert ("disconnected", ()) in client.events


def test_fake_daemon_satisfies_the_gui_device_query_contract(
    monkeypatch, fake_daemon
):
    motor = fake_daemon.add_device(_motor_spec(), setup="instrument")

    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert client.getDeviceParams("motor") == motor.params
        assert client.getCacheKey("motor/value") == ("motor/value", 1.5)
        assert client.ask(
            "getcachekeys",
            "motor/value,motor/offset,missing",
        ) == [
            ("motor/value", 1.5),
            ("motor/offset", 0.8),
        ]
        assert client.getDeviceParam("motor", "offset") == 0.8
        assert client.getDeviceParamInfo("motor") == motor.param_info
        assert client.getDeviceValuetype("motor") is float
        assert client.getDeviceValue("motor") == 1.5
        assert client.eval("session.getDevice('motor').classes", []) == [
            "nicos.core.device.Moveable"
        ]
        assert client.eval("session.getDevice('motor').valueInfo()", "fallback") is None
        assert (
            client.eval(
                "session.getDevice('motor').pollParams(volatile_only=False)",
                "fallback",
            )
            is None
        )
        assert client.eval("session.getSetupInfo()", {}) == {
            "instrument": {
                "description": "",
                "devices": ["motor"],
                "display_order": 50,
                "extended": {},
            }
        }
    finally:
        _disconnect_client(client)


def test_fake_daemon_supports_console_backlog_and_completion_queries(
    monkeypatch, fake_daemon
):
    backlog = ("nicos", 1.0, INFO, "Backlog line\n", None, 1)
    fake_daemon.add_message(backlog)
    fake_daemon.mode = MAINTENANCE
    fake_daemon.set_completion("move sam", "sam", ["sample"])

    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert client.ask("getstatus")["mode"] == MAINTENANCE
        assert client.ask("getmessages", "10000") == [backlog]
        assert client.ask("complete", "move sam", "sam") == ["sample"]
    finally:
        _disconnect_client(client)


@pytest.mark.parametrize(
    ("event_name", "push_event", "expected_payload"),
    [
        pytest.param(
            "cache",
            lambda daemon: daemon.push_cache("motor/value", 7.5, timestamp=42.0),
            (42.0, "motor/value", OP_TELL, cache_dump(7.5)),
            id="cache",
        ),
        pytest.param(
            "device",
            lambda daemon: daemon.push_device_event("create", ["motor"]),
            ("create", ["motor"]),
            id="device",
        ),
        pytest.param(
            "message",
            lambda daemon: daemon.push_message(("nicos", 0, 30, "hello", None, 1)),
            ("nicos", 0, 30, "hello", None, 1),
            id="message",
        ),
        pytest.param(
            "setup",
            lambda daemon: daemon.push_setup(["instrument"]),
            (["instrument"], ["instrument"]),
            id="setup",
        ),
        pytest.param(
            "status",
            lambda daemon: daemon.push_status((STATUS_IDLE, -1)),
            (STATUS_IDLE, -1),
            id="status",
        ),
        pytest.param(
            "mode",
            lambda daemon: daemon.push_mode(MASTER),
            MASTER,
            id="mode",
        ),
        pytest.param(
            "experiment",
            lambda daemon: daemon.push_experiment(("proposal", "user")),
            ("proposal", "user"),
            id="experiment",
        ),
        pytest.param(
            "simmessage",
            lambda daemon: daemon.push_simmessage(
                ("nicos", 0.0, INFO, "sim line\n", None, "0")
            ),
            ("nicos", 0.0, INFO, "sim line\n", None, "0"),
            id="simmessage",
        ),
    ],
)
def test_fake_daemon_pushes_real_daemon_event_payload_shapes(
    monkeypatch, fake_daemon, event_name, push_event, expected_payload
):
    fake_daemon.add_device(_motor_spec(), setup="instrument")
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        event_count = len(_event_payloads(client, event_name))
        push_event(fake_daemon)

        _wait_until(lambda: len(_event_payloads(client, event_name)) > event_count)

        assert _event_payloads(client, event_name)[-1] == expected_payload
    finally:
        _disconnect_client(client)


def test_fake_daemon_records_unknown_eval_expressions_for_the_fixture_guard(
    monkeypatch, fake_daemon
):
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert client.eval("session.getDevice('motor').does_not_exist()", None) is None
    finally:
        _disconnect_client(client)

    assert fake_daemon.unknown_evals == ["session.getDevice('motor').does_not_exist()"]
    fake_daemon.unknown_evals.clear()


def test_fake_daemon_can_drive_real_client_authentication_failure(
    monkeypatch, fake_daemon
):
    fake_daemon.command_failures["authenticate"] = (False, "denied")

    client = _connect_client(monkeypatch, fake_daemon)

    assert client.isconnected is False
    assert ("error", ("Error from daemon: denied.",)) in client.events
    assert ("disconnected", ()) in client.events


def test_fake_daemon_can_drive_real_client_broken_connection(
    monkeypatch, fake_daemon
):
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        fake_daemon.command_failures["getstatus"] = OSError(0, "socket closed")
        assert client.ask("getstatus") is None
    finally:
        _disconnect_client(client)

    assert client.isconnected is False
    assert ("broken", ("Server connection broken: socket closed.",)) in client.events
    assert ("disconnected", ()) in client.events

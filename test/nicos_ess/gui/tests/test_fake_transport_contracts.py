"""Contracts pinned by the ESS GUI fake transport.

These tests keep the fake aligned with the daemon/client boundary used by the
GUI tests. They intentionally do not test daemon behavior that belongs in the
real daemon test suite.
"""

from __future__ import annotations

import inspect
from time import monotonic, sleep

import pytest

from nicos.clients.base import ConnectionData, NicosClient
from nicos.clients.proto.classic import ClientTransport as ClassicClientTransport
from nicos.core import MASTER
from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import (
    DAEMON_COMMANDS,
    DAEMON_EVENTS,
    ClientTransport as BaseClientTransport,
    STATUS_IDLE,
)
from nicos.protocols.daemon.classic import PROTO_VERSION

from test.nicos_ess.gui.doubles import FakeClientTransport


TRANSPORT_METHODS = (
    "connect",
    "connect_events",
    "disconnect",
    "send_command",
    "recv_reply",
    "recv_event",
)

GUI_COMMAND_CONTRACT = {
    "authenticate",
    "complete",
    "eval",
    "eventmask",
    "eventunmask",
    "getcachekeys",
    "getdataset",
    "getmessages",
    "getstatus",
    "keepalive",
    "queue",
    "quit",
    "start",
}

GUI_EVENT_CONTRACT = {
    "cache",
    "message",
    "mode",
    "setup",
    "simmessage",
    "status",
}

STATUS_KEYS = {
    "current_script",
    "devicefailures",
    "devices",
    "eta",
    "mode",
    "requests",
    "script",
    "setups",
    "status",
    "watch",
}


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


def test_protocol_names_used_by_the_gui_fake_are_real_daemon_contract_names():
    assert GUI_COMMAND_CONTRACT <= set(DAEMON_COMMANDS)
    assert GUI_EVENT_CONTRACT <= set(DAEMON_EVENTS)


def test_fake_transport_implements_the_client_transport_method_contract():
    assert issubclass(FakeClientTransport, BaseClientTransport)

    base_methods = {
        name
        for name, member in inspect.getmembers(BaseClientTransport, inspect.isfunction)
        if name != "determine_serializer"
    }
    assert base_methods == set(TRANSPORT_METHODS)

    for name in TRANSPORT_METHODS:
        assert inspect.signature(getattr(FakeClientTransport, name)) == (
            inspect.signature(getattr(ClassicClientTransport, name))
        )


def test_fake_transport_connect_returns_the_daemon_banner(fake_daemon):
    transport = FakeClientTransport(fake_daemon)

    try:
        transport.connect(ConnectionData("fake", 0, "test", "test"))

        success, banner = transport.recv_reply()
        assert success is True
        assert banner == {
            "daemon_version": "fake-1.0",
            "protocol_version": PROTO_VERSION,
            "pw_hashing": "plain",
        }

        with pytest.raises(RuntimeError, match="no pending command"):
            transport.recv_reply()
    finally:
        transport.disconnect()


def test_fake_daemon_satisfies_the_real_client_connection_contract(
    monkeypatch, fake_daemon
):
    client = _connect_client(monkeypatch, fake_daemon, eventmask=("cache", "status"))
    try:
        assert client.isconnected is True
        assert client.daemon_info == fake_daemon.banner
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


def test_fake_daemon_returns_minimal_expected_command_shapes(
    monkeypatch, fake_daemon
):
    message = ("nicos", 0.0, 20, "backlog line\n", None, 1)
    dataset = {"number": 1}
    fake_daemon.add_setup("instrument", loaded=True)
    fake_daemon.set_cache("device/value", 12.5)
    fake_daemon.datasets.append(dataset)
    fake_daemon.add_message(message)

    client = _connect_client(monkeypatch, fake_daemon)
    try:
        status = client.ask("getstatus")
        assert STATUS_KEYS <= set(status)
        assert status["status"] == (STATUS_IDLE, -1)
        assert status["mode"] == MASTER
        assert status["setups"] == (["instrument"], ["instrument"])

        assert client.ask("getdataset", "*") == [dataset]
        assert client.ask("getmessages", "10000") == [message]
        assert client.ask("getcachekeys", "device/") == [("device/value", 12.5)]
        assert client.ask("complete", "", "") == []
        assert client.eval("session.experiment.get_current_run_number()", None) == 0
        assert client.run("print('first')") == 1
        assert client.run("print('second')") == 2
        assert client.tell("keepalive") is True
    finally:
        _disconnect_client(client)


def test_fake_daemon_delivers_event_payloads_and_masks_per_transport(
    monkeypatch, fake_daemon
):
    masked = _connect_client(monkeypatch, fake_daemon, eventmask=("cache",))
    unmasked = _connect_client(monkeypatch, fake_daemon)
    try:
        fake_daemon.push_cache("motor/value", 7.5, timestamp=42.0)
        first_cache = (42.0, "motor/value", OP_TELL, cache_dump(7.5))

        _wait_until(lambda: first_cache in _event_payloads(unmasked, "cache"))
        assert first_cache not in _event_payloads(masked, "cache")

        fake_daemon.push_status((STATUS_IDLE, -1))
        _wait_until(lambda: (STATUS_IDLE, -1) in _event_payloads(masked, "status"))

        masked.tell("eventunmask", ["cache"])
        fake_daemon.push_cache("motor/value", 8.5, timestamp=43.0)
        second_cache = (43.0, "motor/value", OP_TELL, cache_dump(8.5))

        _wait_until(lambda: second_cache in _event_payloads(masked, "cache"))
    finally:
        _disconnect_client(masked)
        _disconnect_client(unmasked)


def test_unknown_eval_returns_none_and_is_recorded(monkeypatch, fake_daemon):
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert client.eval("unknown.expression", None) is None
    finally:
        _disconnect_client(client)

    assert fake_daemon.unknown_evals == ["unknown.expression"]


def test_unknown_command_returns_error_reply_and_is_recorded(
    monkeypatch, fake_daemon, allow_unknown_fake_daemon_calls
):
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert (
            client.ask("does-not-exist", noerror=True, default="fallback")
            == "fallback"
        )
        assert client.isconnected is True
    finally:
        _disconnect_client(client)

    assert fake_daemon.unknown_commands == ["does-not-exist"]


def test_client_disconnect_stops_the_fake_transport_event_thread(
    monkeypatch, fake_daemon
):
    client = _connect_client(monkeypatch, fake_daemon)
    try:
        thread = client.event_thread
        assert thread.is_alive()

        client.disconnect()
        thread.join(timeout=1.0)

        assert client.isconnected is False
        assert not thread.is_alive()
        assert ("disconnected", ()) in client.events
    finally:
        _disconnect_client(client)

"""Contract tests for GUI test doubles.

These tests are intentionally small and explicit: they pin the subset of the
real NICOS client/transport contract that the ESS GUI test doubles emulate.
If the real client-side contract drifts, these tests should fail close to the
double rather than later in a panel test with a less obvious error.
"""

from __future__ import annotations

import inspect
from time import monotonic, sleep

import pytest

from nicos.clients.base import ConnectionData, NicosClient
from nicos.clients.proto.classic import ClientTransport as ClassicClientTransport
from nicos.clients.proto.zeromq import ClientTransport as ZeroMQClientTransport
from nicos.core import params
from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import ClientTransport as BaseClientTransport
from nicos.protocols.daemon.classic import PROTO_VERSION

from test.nicos_ess.gui.doubles import DeviceSpec, FakeClientTransport, FakeDaemon


class RecordingClient(NicosClient):
    """Concrete NicosClient used to drive the fake through the real API."""

    def __init__(self):
        self.events = []
        self.log_messages = []
        super().__init__(self.log_messages.append)

    def signal(self, name, *args):
        self.events.append((name, args))


def _connect_client(monkeypatch, fake_daemon):
    monkeypatch.setattr(
        "nicos.clients.base.ClientTransport",
        lambda: FakeClientTransport(fake_daemon),
    )
    client = RecordingClient()
    client.connect(ConnectionData("fake", 0, "test", "test"))
    return client


def _disconnect_client(client):
    if not client.isconnected:
        return
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


def test_fake_client_transport_matches_real_client_transport_surface():
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
        assert fake_sig == inspect.signature(getattr(ZeroMQClientTransport, name))


def test_fake_daemon_supports_real_nicos_client_helper_api(monkeypatch, fake_daemon):
    motor = DeviceSpec(
        name="motor",
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
        valuetype=float,
    )
    fake_daemon.add_device(motor, setup="instrument")

    client = _connect_client(monkeypatch, fake_daemon)
    try:
        assert client.isconnected is True
        assert client.daemon_info["protocol_version"] == PROTO_VERSION
        assert client.user_level == fake_daemon.user_level

        assert client.getDeviceParams("motor") == motor.params
        assert client.getCacheKey("motor/value") == ("motor/value", 1.5)
        assert client.getDeviceParam("motor", "offset") == 0.8
        assert client.getDeviceParamInfo("motor") == motor.param_info
        assert client.getDeviceValuetype("motor") is float
        assert client.eval("session.getDevice('motor').classes", []) == [
            "nicos.core.device.Moveable"
        ]
        assert client.eval("session.getSetupInfo()", {}) == {
            "instrument": {
                "description": "",
                "devices": ["motor"],
                "display_order": 50,
                "extended": {},
            }
        }

        signals = [name for name, _args in client.events]
        assert "connected" in signals
        assert fake_daemon.command_log[0][0] == "authenticate"
    finally:
        _disconnect_client(client)

    assert ("disconnected", ()) in client.events


def test_fake_daemon_cache_events_match_real_client_event_loop_contract(
    monkeypatch, fake_daemon
):
    fake_daemon.add_device(
        DeviceSpec(
            name="motor",
            params={
                "value": 1.5,
                "status": (200, ""),
                "visibility": ("namespace", "devlist"),
            },
        ),
        setup="instrument",
    )

    client = _connect_client(monkeypatch, fake_daemon)
    try:
        fake_daemon.push_cache("motor/value", 7.5, timestamp=42.0)

        def saw_cache_event():
            return any(name == "cache" for name, _args in client.events)

        _wait_until(saw_cache_event)

        cache_events = [args[0] for name, args in client.events if name == "cache"]
        assert cache_events[-1] == (42.0, "motor/value", OP_TELL, cache_dump(7.5))
    finally:
        _disconnect_client(client)

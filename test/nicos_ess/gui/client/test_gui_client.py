"""Client-level ESS GUI harness tests."""

from __future__ import annotations

from nicos.clients.gui.client import NicosGuiClient

from test.nicos_ess.gui.doubles import FakeClientTransport


def test_real_client_connect_handshake(gui_window, fake_daemon):
    """The real connect flow runs against the empty-shell base guiconfig."""
    client = gui_window.client
    assert type(client) is NicosGuiClient, (
        "expected the unmodified NicosGuiClient, not a subclass"
    )
    assert client.isconnected is True
    assert client.user_level == 20
    assert client.daemon_info["daemon_version"] == "fake-1.0"
    assert isinstance(client.transport, FakeClientTransport)
    assert client.event_thread.is_alive()
    assert fake_daemon.command_log[0][0] == "authenticate"

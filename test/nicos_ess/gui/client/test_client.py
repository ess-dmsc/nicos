"""Client-level ESS GUI harness tests."""

from __future__ import annotations

import pytest

pytest.importorskip("pytestqt")

from nicos.clients.gui.client import NicosGuiClient

from test.nicos_ess.gui.doubles import FakeClientTransport


guiconfig_name = "devices.py"


def test_guiconfig_name_resolves_inside_shared_guiconfigs(guiconfig_path):
    assert guiconfig_path.name == guiconfig_name


def test_real_client_connect_handshake(gui_window, fake_daemon):
    """The real connect flow ran: banner, auth, event thread, signals."""
    client = gui_window.client
    assert type(client) is NicosGuiClient, (
        "expected the unmodified NicosGuiClient, not a subclass"
    )
    assert client.isconnected is True
    assert client.user_level == 20
    assert client.daemon_info["daemon_version"] == "fake-1.0"
    assert isinstance(client.transport, FakeClientTransport)
    assert client.event_thread.is_alive()
    cmds = [cmd for cmd, _ in fake_daemon.command_log]
    assert cmds[0] == "authenticate"
    assert "getstatus" in cmds  # DevicesPanel.on_client_connected asked for it

# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Tests for the Carbon client and metric path helpers."""

from nicos_ess.telemetry.carbon.client import CarbonTcpClient
from nicos_ess.telemetry.carbon.paths import sanitize_path, sanitize_segment


class FakeClock:
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, delta):
        self.value += float(delta)


class FakeSocket:
    def __init__(self, fail_send=False):
        self.fail_send = fail_send
        self.timeout = None
        self.closed = False
        self.sent_payloads = []

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, payload):
        if self.fail_send:
            raise OSError("send failed")
        self.sent_payloads.append(payload)

    def close(self):
        self.closed = True


def test_sanitize_path_keeps_dot_hierarchy():
    assert sanitize_segment("BIFROST!") == "bifrost"
    assert sanitize_path("nicos.ESS BIFROST.logs") == "nicos.ess_bifrost.logs"
    assert sanitize_path("...") == "unknown"


def test_carbon_tcp_client_retries_after_delay_and_flushes_pending():
    clock = FakeClock(10)
    connect_calls = []
    sockets = []

    def socket_factory(address, timeout):
        connect_calls.append((address, timeout))
        if len(connect_calls) == 1:
            raise OSError("unreachable")
        sock = FakeSocket()
        sockets.append(sock)
        return sock

    client = CarbonTcpClient(
        host="carbon.local",
        port=2003,
        reconnect_delay_s=5,
        socket_factory=socket_factory,
        monotonic_fn=clock,
    )

    client.send_lines(["a.b 1 111\n"])
    assert client.pending_count == 1
    assert len(connect_calls) == 1

    client.flush()
    assert len(connect_calls) == 1
    assert client.pending_count == 1

    clock.advance(5)
    assert client.flush()
    assert len(connect_calls) == 2
    assert client.pending_count == 0
    assert sockets[0].sent_payloads == [b"a.b 1 111\n"]


def test_carbon_tcp_client_queue_max_keeps_latest_entries():
    clock = FakeClock()
    connect_calls = 0
    sock = FakeSocket()

    def socket_factory(*_args, **_kwargs):
        nonlocal connect_calls
        connect_calls += 1
        if connect_calls <= 3:
            raise OSError("offline")
        return sock

    client = CarbonTcpClient(
        host="carbon.local",
        reconnect_delay_s=0,
        queue_max=2,
        socket_factory=socket_factory,
        monotonic_fn=clock,
    )

    client.send_lines(["m.one 1 1\n"])
    client.send_lines(["m.two 2 2\n"])
    client.send_lines(["m.three 3 3\n"])

    assert client.pending_count == 2
    assert client.flush()
    assert sock.sent_payloads == [b"m.two 2 2\nm.three 3 3\n"]

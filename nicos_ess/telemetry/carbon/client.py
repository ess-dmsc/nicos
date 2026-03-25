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
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Buffered TCP sender for Carbon plaintext metrics."""

from __future__ import annotations

import socket
import time
from collections import deque
from threading import Lock
from typing import Callable, Iterable


class CarbonTcpClient:
    """Send Carbon plaintext lines with bounded buffering and simple retry.

    The client accepts complete metric lines ending in ``\\n``. It keeps a
    bounded in-memory queue, retries connections after a cooldown, and drops the
    oldest queued lines when the queue is full.

    Delivery is intentionally conservative: lines are sent one by one. If a
    socket write fails, the line that was in flight is dropped rather than
    retried. This avoids duplicating counters after a partial TCP write, which
    would be worse than losing a single sample.
    """

    def __init__(
        self,
        host: str,
        port: int = 2003,
        reconnect_delay_s: float = 2.0,
        queue_max: int = 10000,
        connect_timeout_s: float = 1.0,
        send_timeout_s: float | None = 1.0,
        socket_factory: Callable[..., socket.socket] = socket.create_connection,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        self.host = str(host).strip()
        self.port = int(port)
        self.reconnect_delay_s = reconnect_delay_s
        self.connect_timeout_s = connect_timeout_s
        self.send_timeout_s = send_timeout_s
        self._socket_factory = socket_factory
        self._monotonic_fn = monotonic_fn
        self._socket: socket.socket | None = None
        self._last_connect_attempt = -self.reconnect_delay_s
        self._pending: deque[str] = deque(maxlen=max(int(queue_max), 1))
        self._lock = Lock()

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def send_lines(self, lines: Iterable[str]) -> bool:
        with self._lock:
            for line in lines:
                self._pending.append(line)
            return self._flush_locked()

    def flush(self) -> bool:
        with self._lock:
            return self._flush_locked()

    def close(self) -> None:
        with self._lock:
            self._flush_locked(force=True)
            self._close_socket()

    def _flush_locked(self, *, force: bool = False) -> bool:
        if not self._pending:
            return True
        if not self._ensure_connected(force=force):
            return False

        while self._pending:
            if self._socket is None:
                return False
            line = self._pending[0]
            try:
                self._socket.sendall(line.encode("utf-8"))
            except OSError:
                # The current line may have been partially delivered already.
                # Drop it to avoid retrying an unknown prefix and duplicating
                # the metric after reconnect.
                self._pending.popleft()
                self._close_socket()
                return False
            self._pending.popleft()
        return True

    def _ensure_connected(self, *, force: bool = False) -> bool:
        if self._socket is not None:
            return True

        now = self._monotonic_fn()
        if not force and now - self._last_connect_attempt < self.reconnect_delay_s:
            return False

        self._last_connect_attempt = now
        try:
            sock = self._socket_factory(
                (self.host, self.port), timeout=self.connect_timeout_s
            )
            if self.send_timeout_s is not None:
                sock.settimeout(self.send_timeout_s)
            self._socket = sock
            return True
        except OSError:
            self._socket = None
            return False

    def _close_socket(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        except OSError:
            pass
        finally:
            self._socket = None

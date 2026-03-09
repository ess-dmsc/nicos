"""Carbon plaintext telemetry helpers."""

from __future__ import annotations

import re
import socket
import time
from collections import deque
from threading import Lock
from typing import Callable, Iterable

_VALID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def sanitize_segment(segment: str) -> str:
    """Convert one metric path segment to a Graphite-safe token."""
    text = _VALID_SEGMENT_RE.sub("_", str(segment).strip().lower())
    text = _MULTI_UNDERSCORE_RE.sub("_", text).strip("_")
    return text or "unknown"


def sanitize_path(path: str) -> str:
    """Sanitize a dot-delimited metric path."""
    parts = [sanitize_segment(part) for part in str(path).split(".") if part]
    return ".".join(parts) if parts else "unknown"


class CarbonTcpClient:
    """Minimal Carbon plaintext sender with reconnect and bounded queue."""

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
        self.host = host
        self.port = int(port)
        self.reconnect_delay_s = max(float(reconnect_delay_s), 0.0)
        self.connect_timeout_s = max(float(connect_timeout_s), 0.0)
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

    def enqueue_lines(self, lines: Iterable[str]) -> None:
        with self._lock:
            for line in lines:
                self._pending.append(line)

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
            self._close_socket()

    def _flush_locked(self) -> bool:
        if not self._pending:
            return True
        if not self._ensure_connected():
            return False

        payload = "".join(self._pending).encode("utf-8")
        try:
            assert self._socket is not None
            self._socket.sendall(payload)
            self._pending.clear()
            return True
        except OSError:
            self._close_socket()
            return False

    def _ensure_connected(self) -> bool:
        if self._socket is not None:
            return True

        now = self._monotonic_fn()
        if now - self._last_connect_attempt < self.reconnect_delay_s:
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

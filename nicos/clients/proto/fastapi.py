"""
FastAPI / WebSocket transport for NICOS **client** side.
"""

from __future__ import annotations

import pickle
import queue
import ssl
import threading
import uuid
from typing import Any

from websockets.sync.client import connect as ws_connect  # type: ignore

from nicos.protocols.daemon import ClientTransport as BaseClientTransport
from nicos.protocols.daemon import ProtocolError
from nicos.utils import createThread

# -----------------------------------------------------------------------------
__all__ = ["ClientTransport"]


class ClientTransport(BaseClientTransport):
    """WebSocket transport that replaces the classic TCP+Pickle client."""

    def __init__(self, serializer=None):
        self.serializer = serializer  # will be set after handshake if None
        self.ws = None  # type: ignore

        # single queues shared by all NicosClient threads
        self._reply_q: "queue.Queue[tuple[bool, Any]]" = queue.Queue()
        self._event_q: "queue.Queue[tuple[str, Any, list[bytes]]]" = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def connect(self, conndata):
        """Establish WebSocket connection **and** read the banner."""
        url = f"wss://{conndata.host}:{conndata.port}/ws"
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations("ssl/ca.pem")
        self.ws = ws_connect(url, open_timeout=30.0, ssl=ssl_ctx)

        self._reader_thread = createThread("ws-receiver", self._receiver_loop)

        # The banner tells us which serializer to use. Fix later
        from nicos.protocols.daemon.classic import SERIALIZERS

        name = "classic"  # hardcoded for now
        self.serializer = SERIALIZERS[name]()

        return True

    def connect_events(self, conndata):
        """No‑op: events arrive over the same WebSocket."""

    def disconnect(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
        self.ws = None

    def send_command(self, cmdname, args):
        if not self.ws:
            raise ProtocolError("not connected")
        frame = pickle.dumps((cmdname, *args))
        self.ws.send(frame)

    def recv_reply(self):
        try:
            return self._reply_q.get(timeout=30.0)
        except queue.Empty:
            raise ProtocolError("timeout awaiting reply") from None

    def recv_event(self):
        """Return (event_name, payload_as_list, blobs) – classic NICOS shape."""
        try:
            evtname, payload_bytes, blobs = self._event_q.get(timeout=None)
        except queue.Empty:  # should never happen
            raise ProtocolError("event queue unexpectedly empty")

        evtname2, payload = self.serializer.deserialize_event(payload_bytes, evtname)
        if evtname2 != evtname:  # sanity-check, remove later probably
            raise ProtocolError(
                f"deserializer returned {evtname2!r}, expected {evtname!r}"
            )

        return evtname, payload, blobs

    def _receiver_loop(self):
        """Background thread: demultiplex frames → reply_q / event_q."""
        while True:
            try:
                frame = self.ws.recv()
            except Exception:
                # push sentinel so waiting calls unblock gracefully
                self._reply_q.put((False, "connection lost"))
                break
            try:
                obj = pickle.loads(frame)
            except Exception as exc:  # noqa: BLE001
                self._reply_q.put((False, f"unpickle error: {exc}"))
                continue

            if isinstance(obj, tuple) and len(obj) >= 1 and obj[0] == "event":
                print(f"Received event: {obj[1]!r}")
                _, evtname, payload, blobs = obj
                self._event_q.put((evtname, payload, blobs))
            elif isinstance(obj, tuple) and len(obj) == 2 and isinstance(obj[0], bool):
                self._reply_q.put(obj)  # (success, payload)
            else:
                self._reply_q.put((False, "malformed frame"))

    def _recv_nowait(self):
        """Read a single frame synchronously (only used in tests)."""
        return pickle.loads(self.ws.recv())

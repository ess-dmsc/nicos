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
from nicos.protocols.daemon.classic import (
    ACK,
    ENQ,
    LENGTH,
    NAK,
    SERIALIZERS,
    STX,
    code2command,
    command2code,
)
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

    def _clear_queues(self):
        while not self._reply_q.empty():
            try:
                self._reply_q.get_nowait()
            except queue.Empty:
                break
        while not self._event_q.empty():
            try:
                self._event_q.get_nowait()
            except queue.Empty:
                break

    def connect(self, conndata):
        """Establish WebSocket connection **and** read the banner."""
        self._clear_queues()
        url = f"wss://{conndata.host}:{conndata.port}/ws"
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations("ssl/ca.pem")
        self.ws = ws_connect(url, open_timeout=30.0, ssl=ssl_ctx)
        self._reader_thread = createThread("ws-receiver", self._receiver_loop)
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
        self._clear_queues()

    def send_command(self, cmdname, args):
        """Serialize *cmdname*/*args* and push one binary WS frame."""
        if not self.ws:
            raise ProtocolError("not connected")

        payload = self.serializer.serialize_cmd(cmdname, args)
        frame = ENQ + command2code[cmdname] + LENGTH.pack(len(payload)) + payload
        self.ws.send(frame)

    def recv_reply(self):
        try:
            return self._reply_q.get(timeout=30.0)
        except queue.Empty:
            raise ProtocolError("timeout awaiting reply") from None

    def recv_event(self):
        try:
            return self._event_q.get(timeout=None)  # (evtname, payload, blobs)
        except queue.Empty:  # pragma: no cover
            raise ProtocolError("event queue unexpectedly empty")

    def _receiver_loop(self):
        """Demultiplex replies vs. events and fill the local queues."""
        while True:
            try:
                frame: bytes = self.ws.recv()
            except Exception:
                self._reply_q.put((False, "connection lost"))
                break

            if not frame:  # never zero-length in our protocol
                self._reply_q.put((False, "empty frame"))
                continue

            lead = frame[:1]

            if lead == ACK:
                self._reply_q.put((True, None))
                continue

            if lead == STX and self.serializer is None:
                declared_len = LENGTH.unpack(frame[1:5])[0]
                serializer_blob = frame[5 : 5 + declared_len]
                try:
                    self.serializer = self.determine_serializer(serializer_blob, True)
                except ProtocolError as exc:
                    self._reply_q.put((False, f"cannot choose serializer: {exc}"))
                    break

            if lead in (STX, NAK):
                success = lead == STX
                declared_len = LENGTH.unpack(frame[1:5])[0]
                serializer_blob = frame[5:]
                if len(serializer_blob) != declared_len:
                    self._reply_q.put((False, "length mismatch"))
                    continue

                try:
                    _ignored, msg = self.serializer.deserialize_reply(
                        serializer_blob, success
                    )
                except Exception as exc:
                    self._reply_q.put((False, f"deserialization error: {exc}"))
                    continue

                if (
                    not isinstance(msg, tuple)
                    or len(msg) != 2
                    or not isinstance(msg[0], bool)
                ):
                    self._reply_q.put((False, "malformed reply envelope"))
                    continue

                okflag, inner = msg

                if not okflag:
                    self._reply_q.put((False, inner))
                    continue

                if (
                    isinstance(inner, tuple)
                    and inner
                    and inner[0] == "event"
                    and len(inner) == 4
                ):
                    _, evtname, evt_blob, blobs = inner
                    _, payload = self.serializer.deserialize_event(evt_blob, evtname)
                    self._event_q.put((evtname, payload, blobs))
                else:
                    self._reply_q.put((True, inner))
                continue

            self._reply_q.put((False, "unknown frame type"))

    def _recv_nowait(self):
        """Read a single frame synchronously (only used in tests)."""
        return pickle.loads(self.ws.recv())

"""
FastAPI / WebSocket transport for NICOS **client** side.
"""

from __future__ import annotations

import collections
import itertools
import pickle
import queue
import ssl
import threading
import time
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
    code2event,
    command2code,
)
from nicos.utils import createThread

# -----------------------------------------------------------------------------
__all__ = ["ClientTransport"]

from nicos.services.daemon.proto.fastapi import BLOB_PRIO, CTRL_PRIO


class ClientTransport(BaseClientTransport):
    """WebSocket transport that replaces the classic TCP+Pickle client."""

    def __init__(self, serializer=None):
        self.serializer = serializer
        self.ws: "ws_connect | None" = None
        self.ws_blob: "ws_connect | None" = None
        self._seq = itertools.count()

        # completed events → consumed by higher‑level NICOS client API
        self._ready_q: queue.PriorityQueue[
            tuple[int, int, tuple[str, Any, list[memoryview]]]
        ] = queue.PriorityQueue(maxsize=200)

        # events waiting for their blobs; oldest first
        self._pending_events: "collections.deque[list]" = collections.deque()
        self._pending_lock = threading.Lock()

        # replies from daemon commands
        self._reply_q: "queue.Queue[tuple[bool, Any]]" = queue.Queue()

        # background threads
        self._ctrl_thread: threading.Thread | None = None
        self._blob_thread: threading.Thread | None = None

    def _clear_queues(self):
        while not self._reply_q.empty():
            try:
                self._reply_q.get_nowait()
            except queue.Empty:
                break
        while not self._ready_q.empty():
            try:
                self._ready_q.get_nowait()
            except queue.Empty:
                break
        with self._pending_lock:
            self._pending_events.clear()

    def connect(self, conndata):
        """Open control + blob channels and start receiver threads."""
        self._reply_q.queue.clear()
        while not self._ready_q.empty():
            self._ready_q.get_nowait()

        self.client_id = uuid.uuid1().bytes

        base_url = f"wss://{conndata.host}:{conndata.port}"
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations("ssl/ca.pem")

        self.ws = ws_connect(
            f"{base_url}/ws", open_timeout=30.0, max_size=None, ssl=ssl_ctx
        )
        self.ws.send(self.client_id)

        self._ctrl_thread = createThread("ws-ctrl-recv", self._ctrl_receiver)
        return True

    def connect_events(self, conndata):
        """Open the second WebSocket that is dedicated to blobs."""
        if self.ws is None:
            raise ProtocolError("control socket not connected")

        base_url = f"wss://{conndata.host}:{conndata.port}"
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations("ssl/ca.pem")
        self.ws_blob = ws_connect(
            f"{base_url}/ws/blob", open_timeout=10.0, max_size=None, ssl=ssl_ctx
        )

        self.ws_blob.send(self.client_id)
        self._blob_thread = createThread("ws-blob-recv", self._blob_receiver)

    def disconnect(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self._ctrl_thread:
            self._ctrl_thread.join(timeout=1.0)
        if self._blob_thread:
            self._blob_thread.join(timeout=1.0)
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
        """Block until the *next complete* event (header + all blobs) is ready."""
        try:
            prio, seq, (evtname, payobj, blobs) = self._ready_q.get(timeout=None)
            print(
                f"Received event: {evtname}, priority: {prio}, sequence: {seq}, blobs: {len(blobs)}"
            )
            return evtname, payobj, blobs
        except queue.Empty:  # pragma: no cover – unreachable (timeout=None)
            raise ProtocolError("timeout awaiting event") from None

    def _ctrl_receiver(self):
        """Read control frames, tag them with control‐priority, and push into _ready_q."""
        while True:
            # if self._ready_q.full():
            #     time.sleep(0.01)
            #     continue

            try:
                frame: bytes = self.ws.recv()
            except Exception:
                self._reply_q.put((False, "control socket lost"))
                break

            if not frame:
                continue

            lead = frame[:1]
            if lead == ACK:
                self._reply_q.put((True, None))
                continue

            if lead == STX and self.serializer is None:
                (decl_len,) = LENGTH.unpack(frame[1:5])
                ser_blob = frame[5 : 5 + decl_len]
                self.serializer = self.determine_serializer(ser_blob, True)

            if lead == STX and frame[1:3] in code2event:
                evtcode = frame[1:3]
                nblobs = frame[3]
                (paylen,) = LENGTH.unpack(frame[4:8])
                payload = frame[8 : 8 + paylen]

                evtname, payobj = self.serializer.deserialize_event(
                    payload, code2event[evtcode]
                )

                if nblobs == 0:
                    prio = CTRL_PRIO
                    seq = next(self._seq)
                    self._ready_q.put((prio, seq, (evtname, payobj, [])))
                else:
                    with self._pending_lock:
                        self._pending_events.append([evtname, payobj, nblobs, []])
                continue

            if lead in (STX, NAK):
                success = lead == STX
                (decl_len,) = LENGTH.unpack(frame[1:5])
                rep_blob = frame[5 : 5 + decl_len]

                _, data = self.serializer.deserialize_reply(rep_blob, success)
                # handle reply‐embedded events exactly like classic client:
                if (
                    isinstance(data, tuple)
                    and len(data) == 2
                    and isinstance(data[0], bool)
                ):
                    okflag, inner = data
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
                        _, payobj = self.serializer.deserialize_event(evt_blob, evtname)
                        prio = CTRL_PRIO if not blobs else BLOB_PRIO
                        seq = next(self._seq)
                        full_blobs = [memoryview(b) for b in blobs]
                        self._ready_q.put((prio, seq, (evtname, payobj, full_blobs)))
                    else:
                        self._reply_q.put((True, inner))
                else:
                    self._reply_q.put((success, data))
                continue

    def _blob_receiver(self):
        """Pull LENGTH+blob frames, attach to pending, then push with blob‐priority."""
        while True:
            if self._ready_q.full():
                print("Blob queue is full, waiting...")
                time.sleep(0.5)
                continue

            try:
                frame = self.ws_blob.recv()
            except Exception:
                break

            if len(frame) < 4:
                continue

            (blen,) = LENGTH.unpack(frame[:4])
            mv = memoryview(frame)[4:]
            if len(mv) != blen:
                continue

            with self._pending_lock:
                if not self._pending_events:
                    continue

                evt = self._pending_events[0]
                evt[3].append(mv)

                if len(evt[3]) == evt[2]:
                    evtname, payobj, _, blobs = evt
                    prio = BLOB_PRIO
                    seq = next(self._seq)
                    self._ready_q.put((prio, seq, (evtname, payobj, blobs)))
                    self._pending_events.popleft()

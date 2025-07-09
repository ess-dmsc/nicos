"""
FastAPI / WebSocket transport plugin
=================================================

"""

from __future__ import annotations

import asyncio
import collections
import heapq
import queue
import socket
import threading
import time
import weakref
from typing import Any, List, Tuple

from nicos.protocols.daemon import (
    DAEMON_EVENTS,
    CloseConnection,
    ProtocolError,
)
from nicos.protocols.daemon import (
    Server as BaseServer,
)
from nicos.protocols.daemon import (
    ServerTransport as BaseServerTransport,
)
from nicos.protocols.daemon.classic import (
    ACK,
    ENQ,
    LENGTH,
    NAK,
    SERIALIZERS,
    STX,
    code2command,
    command2code,
    event2code,
)
from nicos.services.daemon.handler import (
    ConnectionHandler,
    command_wrappers,
    stop_queue,
)
from nicos.utils import createThread

try:
    import uvicorn
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
except ModuleNotFoundError as err:  # pragma: no cover
    raise RuntimeError(
        "FastAPI transport selected but 'fastapi' or 'uvicorn' is not installed"
    ) from err

__all__ = ["Server"]


CTRL_PRIO = 0  # control/metadata
BLOB_PRIO = 10  # image, livedata, … (anything allowed to be dropped)
STOP_PRIO = 99  # sentinel (always delivered last)


Payload = Tuple[str, bytes, List[bytes]]  # (event, data, blobs)
Node = Tuple[int, int, int, Payload]  # (prio, seq, size, payload)


class PrioritySizedQueue(queue.Queue):
    """SizedQueue with priorities but **unchanged public interface**.

    * Every ``put(item)`` works as before; an optional keyword ``priority=``
      lets the caller label items (default = ``BLOB_PRIO``).
    * ``get()`` still returns exactly the original ``item``.
    * When the queue (measured in bytes) is full and a **higher-priority**
      item is offered, the oldest low-priority blob is discarded to make room.
    """

    def __init__(self, max_bytes: int):
        super().__init__(0)
        self._max = max_bytes
        self.queue = []
        self._used = 0
        self._seq = 0

    def _qsize(self) -> int:
        return len(self.queue)

    def _sizeof(self, payload: Any) -> int:
        if isinstance(payload, tuple) and len(payload) == 3:
            _evt, data, blobs = payload
            return len(data) + sum(len(b) for b in blobs)
        return 1  # fallback

    def put(self, item: Payload, block=True, timeout=None, *, priority=BLOB_PRIO):
        """Same signature as ``queue.Queue.put`` plus the *priority* keyword."""
        size = self._sizeof(item)
        if size > self._max:
            raise queue.Full("single item exceeds queue limit")

        with self.not_full:
            endtime = None
            while self._used + size > self._max:
                # try to free space by dumping one low-priority blob
                if priority == CTRL_PRIO or not self._evict_one_blob(priority):
                    if not block:
                        raise queue.Full
                    if timeout is None:
                        self.not_full.wait()
                    else:
                        if endtime is None:
                            endtime = time.monotonic() + timeout
                        remaining = endtime - time.monotonic()
                        if remaining <= 0.0:
                            raise queue.Full
                        self.not_full.wait(remaining)

            heapq.heappush(self.queue, (priority, self._seq, size, item))
            self._seq += 1
            self._used += size
            self.not_empty.notify()

    def _evict_one_blob(self, incoming_prio: int) -> bool:
        """Remove one queued blob with prio ≥ ``incoming_prio``; return True if dropped."""
        # scan from *oldest* (heap keeps smallest first, so start from the end)
        for idx in range(len(self.queue) - 1, -1, -1):
            prio, _seq, sz, payload = self.queue[idx]
            if prio >= incoming_prio:
                del self.queue[idx]
                heapq.heapify(self.queue)
                self._used -= sz
                return True
        return False

    def _get(self) -> Payload:
        prio, _seq, sz, payload = heapq.heappop(self.queue)
        self._used -= sz
        return payload


def _is_blob(evt: str) -> bool:
    return DAEMON_EVENTS.get(evt, (None, False))[1]


def _run_in_loop(loop: asyncio.AbstractEventLoop, coro):
    """Submit *coro* to *loop* from a foreign (thread) context.

    Returns the *Future* so that the caller may add error callbacks.
    """

    return asyncio.run_coroutine_threadsafe(coro, loop)


class ServerTransport(ConnectionHandler, BaseServerTransport):
    """Bridge one **WebSocket** into ConnectionHandler’s sync API.

    A new thread is spawned per handler so that the classic synchronous flow of
    *ConnectionHandler.handle()* remains the same.
    """

    def __init__(
        self,
        daemon,
        websocket: WebSocket,
        server: "Server",
        ident: int,
        client_id: bytes,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Create one handler bound to the *control* WebSocket.

        *client_id* is the 16-byte token that pairs this handler with the optional
        blob channel.
        """
        self.websocket = websocket
        self.loop = loop
        self.serializer = server.serializer

        self.sock = websocket  # aliases kept for compatibility
        self.event_sock = websocket
        self.client_id = client_id

        self.clientnames = [websocket.client.host]
        try:
            host, aliases, addrlist = socket.gethostbyaddr(websocket.client.host)
            self.clientnames = [host] + aliases + addrlist
        except socket.herror:
            pass

        self._in_queue: "queue.Queue[bytes | None]" = queue.Queue()
        self.blob_websocket: WebSocket | None = None

        self._ingest_task = loop.create_task(self._ingest())

        self._closed = False
        self._closed_event = asyncio.Event()

        ConnectionHandler.__init__(self, daemon)
        self.event_queue = PrioritySizedQueue(100 * 1024 * 1024)  # 100 MiB
        self.setIdent(ident)
        server._register_handler(self)

        createThread(f"event_sender-{ident}", self.event_sender)

    async def _ingest(self):
        """Async coroutine: receive WS frames and push raw bytes to queue."""
        try:
            while True:
                data = await self.websocket.receive_bytes()
                self._in_queue.put(data)
        except WebSocketDisconnect:
            self._in_queue.put(None)
        except Exception:  # pragma: no cover – unexpected network error
            self.log.exception("websocket ingest crash")
            self._in_queue.put(None)

    def attach_blob_socket(self, websocket: WebSocket) -> None:
        """Bind the *second* WebSocket that carries only LENGTH+blob frames."""
        self.blob_websocket: WebSocket = websocket
        self.log.info("blob channel established")

        async def _ingest_blob():
            # the daemon never *reads* from the blob socket,
            # but we must watch for disconnects to clean up
            try:
                while True:
                    await websocket.receive_bytes()
            except WebSocketDisconnect:
                self.log.info("blob channel disconnected")
            except Exception:  # pragma: no cover
                self.log.exception("blob ingest crash")

            # if the blob channel dies we close the whole handler
            self.close()

        _run_in_loop(self.loop, _ingest_blob())

    def get_version(self):
        from nicos.protocols.daemon.classic import PROTO_VERSION

        return PROTO_VERSION

    def recv_command(self):
        """Blocking – extract one command from the queue."""
        frame = self._in_queue.get()
        if frame is None:
            raise CloseConnection

        if len(frame) < 7 or frame[:1] != ENQ:
            raise ProtocolError("invalid command header")

        cmdcode = frame[1:3]
        declared_len = LENGTH.unpack(frame[3:7])[0]
        serializer_blob = frame[7:]

        if len(serializer_blob) != declared_len:
            raise ProtocolError("command length mismatch")

        try:
            cmdname = code2command[cmdcode]
        except KeyError:
            raise ProtocolError("unknown command code")

        try:
            return self.serializer.deserialize_cmd(serializer_blob, cmdname)
        except Exception as exc:
            raise ProtocolError("invalid command payload") from exc

    def send_ok_reply(self, payload):
        """Send ACK or STX + payload exactly like the classic daemon."""
        if payload is None:
            blob = ACK
        else:
            # classic protocol: NO extra (True, …) wrapper
            data = self.serializer.serialize_ok_reply(payload)
            blob = STX + LENGTH.pack(len(data)) + data
        _run_in_loop(self.loop, self.websocket.send_bytes(blob))

    def send_error_reply(self, reason):
        """Send NAK + payload exactly like the classic daemon."""
        data = self.serializer.serialize_error_reply(reason)  # no (False, …) wrapper
        blob = NAK + LENGTH.pack(len(data)) + data
        _run_in_loop(self.loop, self.websocket.send_bytes(blob))

    def send_event(self, evtname, payload, blobs):
        """Send one NICOS event.

        *Header* + *payload* always travel over the control socket.

        If the event type allows blobs and the client opened a blob socket,
        raw buffers are streamed over that socket; otherwise they fall back to
        the control socket exactly like in the classic implementation.
        """

        async def _push():
            header = (
                STX
                + event2code[evtname]
                + bytes([len(blobs)])
                + LENGTH.pack(len(payload))
                + payload
            )
            await self.websocket.send_bytes(header)

            # choose the right channel for the blobs
            ws_target = (
                getattr(self, "blob_websocket", None)
                if DAEMON_EVENTS.get(evtname, (None, False))[1] and blobs
                else self.websocket
            )

            if len(blobs) > 0:
                # print to check if we are using the blob channel or # the control channel
                self.log.warning(
                    f"Sending {len(blobs)} blobs over {'blob' if ws_target is self.blob_websocket else 'control'} channel"
                )

            for blob in blobs:
                mv = blob if isinstance(blob, memoryview) else memoryview(blob)
                await ws_target.send_bytes(LENGTH.pack(len(mv)) + mv)

        fut = _run_in_loop(self.loop, _push())
        fut.add_done_callback(lambda f: f.exception())

    async def wait_closed(self):
        """Coroutine used by the blob endpoint to keep the connection alive."""
        await self._closed_event.wait()

    def close(self):
        """Terminate both WebSockets and wake up anyone awaiting `wait_closed()`."""
        if self._closed:
            return
        self._closed = True

        try:
            _run_in_loop(self.loop, self.websocket.close())
        except Exception:
            pass
        if self.blob_websocket is not None:
            try:
                _run_in_loop(self.loop, self.blob_websocket.close())
            except Exception:
                pass

        if not self._ingest_task.done():
            self._ingest_task.cancel()

        try:
            _run_in_loop(self.loop, self._closed_event.set())
        except Exception:
            pass

        ConnectionHandler.close(self)


class Server(BaseServer):
    """NICOS *Server* that serves FastAPI + WebSockets instead of raw TCP."""

    def __init__(self, daemon, address: tuple[str, int], serializer):
        super().__init__(daemon, address, serializer)
        self.serializer = SERIALIZERS["classic"]()

        self._app = FastAPI()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._uvicorn: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

        self._handlers: "weakref.WeakValueDictionary[int, ServerTransport]" = (
            weakref.WeakValueDictionary()
        )
        self._by_host: dict[str, list[ServerTransport]] = {}
        self._by_clientid: dict[tuple[str, bytes], ServerTransport] = {}
        self._ident_lock = threading.Lock()
        self._next_ident = 0

        @self._app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket):  # noqa: D401
            await websocket.accept()

            client_id = await websocket.receive_bytes()
            if len(client_id) != 16:
                await websocket.close(code=4000, reason="invalid client-id")
                return

            host = websocket.client.host
            if len(self._by_host.get(host, [])) >= 10:  # limit per host
                await websocket.close(code=4001, reason="too many connections")
                return

            loop = asyncio.get_running_loop()
            ident = self._new_ident()
            handler = ServerTransport(
                self.daemon,
                websocket,
                self,
                ident,
                client_id,
                loop,
            )

            self._by_clientid[(host, client_id)] = handler

            cmd_thread = createThread(
                f"ws-handler-{ident}", self._run_handler, args=(handler,)
            )
            await asyncio.to_thread(cmd_thread.join)

        @self._app.websocket("/ws/blob")
        async def ws_blob_endpoint(websocket: WebSocket):  # noqa: D401
            await websocket.accept()

            client_id = await websocket.receive_bytes()
            host = websocket.client.host
            handler = self._by_clientid.get((host, client_id))
            if handler is None:
                await websocket.close(code=4002, reason="no control connection")
                return

            handler.attach_blob_socket(websocket)

            await handler.wait_closed()

        @self._app.get("/healthz")
        async def healthz():  # noqa: D401
            return {"status": "ok"}

    def _new_ident(self) -> int:
        with self._ident_lock:
            self._next_ident += 1
            return self._next_ident

    def _register_handler(self, handler: ServerTransport):
        self._handlers[handler.ident] = handler
        self._by_host.setdefault(handler.clientnames[0], []).append(handler)

    def _run_handler(self, handler: ServerTransport):
        try:
            handler.handle()
        except CloseConnection:
            handler.log.info("client requested clean shutdown")
        except Exception:
            handler.log.exception("unexpected error in handler thread")
        finally:
            handler.close()
            self._handlers.pop(handler.ident, None)
            lst = self._by_host.get(handler.clientnames[0], [])
            if handler in lst:
                lst.remove(handler)

    def start(self, interval: float | None = None):  # noqa: D401
        """Start uvicorn in *another* thread so we keep the same blocking API."""

        # host, port = self.server_address
        # use localhost and port 1301 by default
        host, port = "localhost", 1301
        config = uvicorn.Config(
            self._app,
            host=host,
            port=port,
            log_level="info",
            log_config=None,
            ws_max_size=64 << 20,  # 64 MiB
            ssl_certfile="ssl/server.crt",
            ssl_keyfile="ssl/server.key",
        )
        self._uvicorn = uvicorn.Server(config)

        def _serve():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._uvicorn.run()

        self._thread = createThread("fastapi-server", _serve)

        while not self._uvicorn.started:
            time.sleep(0.05)

    def stop(self):
        if self._uvicorn:
            self._uvicorn.should_exit = True
        if self._thread:
            self._thread.join()

    def close(self):
        for hdlr in list(self._handlers.values()):
            hdlr.close()

    def _discard_handler(self, hdlr: ServerTransport) -> None:
        """Remove the handler from all tracking maps and close it."""
        try:
            hdlr.close()
        except Exception:
            pass
        self._handlers.pop(hdlr.ident, None)
        lst = self._by_host.get(hdlr.clientnames[0], [])
        if hdlr in lst:
            lst.remove(hdlr)

    def emit(
        self,
        event: str,
        data: Any,
        blobs: list[bytes],
        handler: ServerTransport | None = None,
    ):
        payload = self.serializer.serialize_event(event, data)
        is_blob = DAEMON_EVENTS.get(event, (None, False))[1]
        prio = BLOB_PRIO if is_blob else CTRL_PRIO

        targets = [handler] if handler else list(self._handlers.values())
        for h in targets:
            if getattr(h, "_closed", False):
                self._discard_handler(h)
                continue
            try:
                h.event_queue.put((event, payload, blobs), priority=prio, block=False)
            except queue.Full:
                if not is_blob:  # control event must succeed
                    self.daemon.log.warning(
                        "control queue full → drop handler %d", h.ident
                    )
                    self._discard_handler(h)
                # blob events silently dropped when full

"""
FastAPI / WebSocket transport plugin
=================================================

"""

from __future__ import annotations

import asyncio
import pickle  # default serializer – may be replaced by MessagePack/ProtoBuf
import queue
import threading
import time
import weakref
from typing import Any

from nicos.protocols.daemon import (
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
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.websocket = websocket
        self.loop = loop
        self.serializer = server.serializer
        self.sock = websocket
        self.event_sock = websocket
        self.clientnames = []

        self._in_queue: "queue.Queue[bytes | None]" = queue.Queue()

        self._ingest_task = loop.create_task(self._ingest())

        ConnectionHandler.__init__(self, daemon)
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
        if payload is None:
            blob = ACK
        else:
            data = self.serializer.serialize_ok_reply((True, payload))
            blob = STX + LENGTH.pack(len(data)) + data
        _run_in_loop(self.loop, self.websocket.send_bytes(blob))

    def send_error_reply(self, reason):
        data = self.serializer.serialize_error_reply((False, reason))
        blob = NAK + LENGTH.pack(len(data)) + data
        _run_in_loop(self.loop, self.websocket.send_bytes(blob))

    def send_event(self, evtname, payload, blobs):
        evt_blob = self.serializer.serialize_event(evtname, payload)
        outer = (True, ("event", evtname, evt_blob, blobs))
        data = self.serializer.serialize_ok_reply(outer)
        blob = STX + LENGTH.pack(len(data)) + data
        fut = _run_in_loop(self.loop, self.websocket.send_bytes(blob))
        fut.add_done_callback(lambda f: f.exception())  # surface async errors

    def close(self):
        try:
            _run_in_loop(self.loop, self.websocket.close())
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
        self._ident_lock = threading.Lock()
        self._next_ident = 0

        @self._app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket):  # noqa: D401
            await websocket.accept()  # JWT gatekeeping can go here ?
            loop = asyncio.get_running_loop()
            ident = self._new_ident()
            handler = ServerTransport(self.daemon, websocket, self, ident, loop)

            cmd_thread = createThread(
                f"ws-handler-{ident}", self._run_handler, args=(handler,)
            )
            await asyncio.to_thread(cmd_thread.join)

        @self._app.get("/healthz")
        async def healthz():  # noqa: D401
            return {"status": "ok"}

    def _new_ident(self) -> int:
        with self._ident_lock:
            self._next_ident += 1
            return self._next_ident

    def _register_handler(self, handler: ServerTransport):
        self._handlers[handler.ident] = handler

    def _run_handler(self, handler: ServerTransport):
        try:
            handler.handle()
        finally:
            handler.close()
            self._handlers.pop(handler.ident, None)

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

    def emit(
        self,
        event: str,
        data: Any,
        blobs: list[bytes],
        handler: ServerTransport | None = None,
    ):
        data = self.serializer.serialize_event(event, data)
        targets = (handler,) if handler else list(self._handlers.values())
        for hdlr in targets:
            try:
                hdlr.event_queue.put((event, data, blobs), timeout=0.1)
            except queue.Full:
                self.daemon.log.warning("handler %d queue full → dropping", hdlr.ident)
                hdlr.close()

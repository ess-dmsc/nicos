"""In-process fake of the NICOS daemon connection for GUI tests.

The real :class:`nicos.clients.gui.client.NicosGuiClient` runs unmodified; only
the :class:`nicos.clients.base.ClientTransport` it constructs is swapped for
:class:`FakeClientTransport`, which talks to an in-memory :class:`FakeDaemon`.
"""

from __future__ import annotations

import ast
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import DAEMON_EVENTS, STATUS_IDLE
from nicos.protocols.daemon.classic import PROTO_VERSION


_EVENT_SENTINEL = object()


@dataclass
class DeviceSpec:
    name: str
    params: dict = field(default_factory=dict)
    param_info: dict = field(default_factory=dict)
    valuetype: Any = str

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass
class SetupSpec:
    name: str
    description: str = ""
    display_order: int = 50
    devices: list = field(default_factory=list)
    extended: dict = field(default_factory=dict)


class FakeDaemon:
    """In-memory daemon state + command dispatch."""

    def __init__(self, *, user_level: int = 20, daemon_version: str = "fake-1.0"):
        self.user_level = user_level
        self.daemon_version = daemon_version
        self.devices: dict[str, DeviceSpec] = {}
        self.setups: dict[str, SetupSpec] = {}
        self.loaded_setups: set[str] = set()
        self.cache: dict[str, Any] = {}
        self.status: tuple = (STATUS_IDLE, -1)
        self.eval_table: dict[str, Any] = {}
        self.eval_fallback: Callable[[str], Any] | None = None
        self.command_log: list[tuple[str, tuple]] = []
        self._next_request_id = 1
        self._transports: list["FakeClientTransport"] = []

    # ------------------------------------------------------------------
    # wiring

    def attach(self, transport: "FakeClientTransport") -> None:
        self._transports.append(transport)

    def detach(self, transport: "FakeClientTransport") -> None:
        if transport in self._transports:
            self._transports.remove(transport)

    def banner(self) -> dict:
        return {
            "daemon_version": self.daemon_version,
            "protocol_version": PROTO_VERSION,
            "pw_hashing": "plain",
        }

    # ------------------------------------------------------------------
    # state setup

    def add_device(self, device: DeviceSpec, *, setup: str | None = None) -> DeviceSpec:
        self.devices[device.key] = device
        if setup is not None:
            self.add_setup(setup)
            if device.name not in self.setups[setup].devices:
                self.setups[setup].devices.append(device.name)
            self.loaded_setups.add(setup)
        for param, value in device.params.items():
            self.cache[f"{device.key}/{param}"] = value
        return device

    def add_setup(self, setup: str | SetupSpec, **kwargs) -> SetupSpec:
        if isinstance(setup, SetupSpec):
            spec = setup
        else:
            spec = SetupSpec(name=setup, **kwargs)
        stored = self.setups.get(spec.name)
        if stored is None:
            self.setups[spec.name] = spec
            stored = spec
        self.loaded_setups.add(stored.name)
        return stored

    def set_cache(self, key: str, value: Any) -> None:
        key = key.lower()
        self.cache[key] = value
        if "/" in key:
            devkey, param = key.split("/", 1)
            dev = self.devices.get(devkey)
            if dev is not None:
                dev.params[param] = value

    # ------------------------------------------------------------------
    # event push helpers (tests drive these)

    def push_cache(
        self, key: str, value: Any, *, timestamp: float = 0.0, op: str = OP_TELL
    ) -> None:
        self.set_cache(key, value)
        dumped = cache_dump(value) if value is not None else ""
        self._push_event("cache", (timestamp, key.lower(), op, dumped))

    def push_device_event(self, action: str, devnames: list | dict) -> None:
        self._push_event("device", (action, devnames))

    def push_setup(self, loaded: list[str] | None = None) -> None:
        if loaded is not None:
            self.loaded_setups = set(loaded)
        lists = (sorted(self.loaded_setups), sorted(self.setups.keys()))
        self._push_event("setup", lists)

    def push_message(self, message: tuple) -> None:
        self._push_event("message", message)

    def push_status(self, status: tuple) -> None:
        self.status = status
        self._push_event("status", status)

    def _push_event(self, name: str, data: Any) -> None:
        if name not in DAEMON_EVENTS:
            raise ValueError(f"unknown event {name!r}")
        for tr in list(self._transports):
            tr.deliver_event(name, data, [])

    # ------------------------------------------------------------------
    # command dispatch

    def handle(self, cmd: str, args: tuple) -> tuple[bool, Any]:
        self.command_log.append((cmd, args))
        handler = _COMMAND_HANDLERS.get(cmd)
        if handler is None:
            return False, f"unknown command: {cmd}"
        return handler(self, args)

    # handlers below are registered via the _command decorator

    def _get_device(self, devname: str) -> DeviceSpec | None:
        return self.devices.get(devname.lower())

    def _match_eval_device(
        self, expr: str, prefix: str, suffix: str
    ) -> DeviceSpec | None:
        if not expr.startswith(prefix) or not expr.endswith(suffix):
            return None
        devname = ast.literal_eval(expr[len(prefix) : -len(suffix)])
        return self._get_device(devname)

    def _cmd_authenticate(self, args):
        return True, {"user_level": self.user_level}

    def _cmd_eventmask(self, args):
        return True, None

    def _cmd_getstatus(self, args):
        devices = []
        failures: dict = {}
        for spec in self.devices.values():
            devices.append(spec.name)
        loaded = sorted(self.loaded_setups)
        all_setups = sorted(self.setups.keys())
        return True, {
            "devices": devices,
            "devicefailures": failures,
            "setups": (loaded, all_setups),
            "status": self.status,
            "mode": "master",
            "requests": [],
            "current_script": [""],
            "watch": {},
            "eta": (0, None),
        }

    def _cmd_getcachekeys(self, args):
        (query,) = args
        query = query.lower()
        if query.endswith("/"):
            return True, sorted(
                (k, v) for k, v in self.cache.items() if k.startswith(query)
            )
        if query in self.cache:
            return True, [(query, self.cache[query])]
        return True, []

    def _cmd_eval(self, args):
        expr, _stringify = args
        if expr in self.eval_table:
            value = self.eval_table[expr]
            return True, value() if callable(value) else value
        if expr == "session.getSetupInfo()":
            return True, {
                name: {
                    "description": spec.description,
                    "devices": list(spec.devices),
                    "display_order": spec.display_order,
                    "extended": dict(spec.extended),
                }
                for name, spec in self.setups.items()
            }
        if expr.endswith(".pollParams()"):
            return True, None
        if expr.startswith(
            "dict((pn, pi.serialize()) for (pn, pi) in session.getDevice("
        ):
            devname = ast.literal_eval(
                expr[
                    len(
                        "dict((pn, pi.serialize()) for (pn, pi) in session.getDevice("
                    ) : -len(").parameters.items())")
                ]
            )
            device = self._get_device(devname)
            return True, {} if device is None else dict(device.param_info)
        device = self._match_eval_device(expr, "session.getDevice(", ").valuetype")
        if device is not None:
            return True, device.valuetype
        device = self._match_eval_device(expr, "session.getDevice(", ").classes")
        if device is not None:
            return True, list(device.params.get("classes", []))
        device = self._match_eval_device(expr, "session.getDevice(", ").valueInfo()")
        if device is not None:
            return True, None
        if self.eval_fallback is not None:
            return True, self.eval_fallback(expr)
        # Unknown eval: return None; the real client's eval() turns this into
        # the caller-supplied default without raising.
        return True, None

    def _cmd_quit(self, args):
        return True, None

    def _cmd_keepalive(self, args):
        return True, None

    def _cmd_queue(self, args):
        request_id = self._next_request_id
        self._next_request_id += 1
        return True, request_id

    def _cmd_start(self, args):
        return self._cmd_queue(args)


_COMMAND_HANDLERS: dict[str, Callable[[FakeDaemon, tuple], tuple[bool, Any]]] = {
    "authenticate": FakeDaemon._cmd_authenticate,
    "eventmask": FakeDaemon._cmd_eventmask,
    "getstatus": FakeDaemon._cmd_getstatus,
    "getcachekeys": FakeDaemon._cmd_getcachekeys,
    "eval": FakeDaemon._cmd_eval,
    "quit": FakeDaemon._cmd_quit,
    "keepalive": FakeDaemon._cmd_keepalive,
    "queue": FakeDaemon._cmd_queue,
    "start": FakeDaemon._cmd_start,
}


class FakeClientTransport:
    """Implements the 6-method :class:`ClientTransport` contract in-process."""

    def __init__(self, daemon: FakeDaemon):
        self.daemon = daemon
        self.serializer = None
        self._events: queue.Queue = queue.Queue()
        self._pending_banner = False
        self._pending_reply: tuple[bool, Any] | None = None
        self._lock = threading.Lock()

    # -- client-side contract ------------------------------------------------

    def connect(self, conndata):
        self.daemon.attach(self)
        self._pending_banner = True

    def connect_events(self, conndata):
        # Event queue is already set up; nothing to do.
        pass

    def disconnect(self):
        self.daemon.detach(self)
        # Unblock recv_event so the real event thread exits cleanly via the
        # self.disconnecting branch in NicosClient.event_handler.
        self._events.put(_EVENT_SENTINEL)

    def send_command(self, cmdname, args):
        with self._lock:
            self._pending_reply = self.daemon.handle(cmdname, args)

    def recv_reply(self):
        if self._pending_banner:
            self._pending_banner = False
            return True, self.daemon.banner()
        with self._lock:
            reply = self._pending_reply
            self._pending_reply = None
        if reply is None:
            raise RuntimeError("recv_reply called with no pending command")
        return reply

    def recv_event(self):
        item = self._events.get()
        if item is _EVENT_SENTINEL:
            raise ConnectionError("fake transport closed")
        return item

    # -- daemon-side helper --------------------------------------------------

    def deliver_event(self, name, data, blobs):
        self._events.put((name, data, blobs))

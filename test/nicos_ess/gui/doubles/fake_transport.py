"""In-process fake of the NICOS daemon connection for GUI tests.

The real :class:`nicos.clients.gui.client.NicosGuiClient` runs unmodified; only
the :class:`nicos.clients.base.ClientTransport` it constructs is swapped for
:class:`FakeClientTransport`, which talks to an in-memory :class:`FakeDaemon`.
"""

from __future__ import annotations

import ast
import queue
from dataclasses import dataclass, field
from typing import Any

from nicos.core import MASTER
from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import DAEMON_EVENTS, STATUS_IDLE
from nicos.protocols.daemon.classic import PROTO_VERSION


_EVENT_SENTINEL = object()
_NO_REPLY = object()
_UNKNOWN_EVAL = object()
_DEFAULT_EVALS = {
    "session.instrument": "",
    "session.experiment.title": "",
    "session.experiment.proposal": "",
    "session.experiment.get_current_run_number()": "",
    "session.experiment.run_title": "",
}


@dataclass
class DeviceSpec:
    name: str
    valuetype: Any
    params: dict[str, Any] = field(default_factory=dict)
    param_info: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass
class SetupSpec:
    name: str
    description: str = ""
    display_order: int = 50
    devices: list[str] = field(default_factory=list)
    extended: dict[str, Any] = field(default_factory=dict)

    def as_setup_info(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "devices": list(self.devices),
            "display_order": self.display_order,
            "extended": dict(self.extended),
        }


class FakeDaemon:
    """In-memory daemon state + command dispatch."""

    def __init__(
        self,
        *,
        user_level: int = 20,
        daemon_version: str = "fake-1.0",
        protocol_version: int = PROTO_VERSION,
    ):
        self.user_level = user_level
        self.daemon_version = daemon_version
        self.protocol_version = protocol_version
        self.devices: dict[str, DeviceSpec] = {}
        self.setups: dict[str, SetupSpec] = {}
        self.loaded_setups: set[str] = set()
        self.cache: dict[str, Any] = {}
        self.status: tuple = (STATUS_IDLE, -1)
        self.mode = MASTER
        self.eval_table: dict[str, Any] = {}
        self.messages: list[tuple] = []
        self.completions: dict[tuple[str, str], list[str]] = {}
        self.command_log: list[tuple[str, tuple]] = []
        self.command_failures: dict[str, tuple[bool, Any] | BaseException] = {}
        self.unknown_evals: list[str] = []
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
            "protocol_version": self.protocol_version,
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

    def add_message(self, message: tuple) -> tuple:
        self.messages.append(message)
        return message

    def set_completion(self, fullstring: str, lastword: str, replies: list[str]) -> None:
        self.completions[(fullstring, lastword)] = list(replies)

    # ------------------------------------------------------------------
    # event push helpers (tests drive these)

    def push_cache(
        self, key: str, value: Any, *, timestamp: float = 0.0, op: str = OP_TELL
    ) -> None:
        self.set_cache(key, value)
        dumped = cache_dump(value) if value is not None else ""
        self._push_event("cache", (timestamp, key.lower(), op, dumped))

    def push_device_event(self, action: str, devnames: Any) -> None:
        """Push a raw daemon-side device event payload into the client."""
        self._push_event("device", (action, devnames))

    def push_setup(self, loaded: list[str] | None = None) -> None:
        if loaded is not None:
            self.loaded_setups = set(loaded)
        lists = (sorted(self.loaded_setups), sorted(self.setups.keys()))
        self._push_event("setup", lists)

    def push_message(self, message: tuple) -> None:
        self.add_message(message)
        self._push_event("message", message)

    def push_status(self, status: tuple) -> None:
        self.status = status
        self._push_event("status", status)

    def push_mode(self, mode: int) -> None:
        self.mode = mode
        self._push_event("mode", mode)

    def push_experiment(self, data: tuple) -> None:
        self._push_event("experiment", data)

    def push_simmessage(self, message: tuple) -> None:
        self._push_event("simmessage", message)

    def _push_event(self, name: str, data: Any) -> None:
        if name not in DAEMON_EVENTS:
            raise ValueError(f"unknown event {name!r}")
        for tr in list(self._transports):
            tr.deliver_event(name, data, [])

    # ------------------------------------------------------------------
    # command dispatch

    def handle(self, cmd: str, args: tuple) -> tuple[bool, Any]:
        self.command_log.append((cmd, args))

        failure = self.command_failures.get(cmd)
        if failure is not None:
            if isinstance(failure, BaseException):
                raise failure
            return failure

        if cmd == "authenticate":
            return True, {"user_level": self.user_level}
        if cmd in {"eventmask", "keepalive", "quit"}:
            return True, None
        if cmd == "getstatus":
            return True, self._status()
        if cmd == "getcachekeys":
            return True, self._cache_keys(args[0])
        if cmd == "getmessages":
            return True, self._messages(args[0])
        if cmd == "complete":
            return True, self._complete(args[0], args[1])
        if cmd == "eval":
            expr, stringify = args
            value = self._eval(expr)
            if stringify and value is not None:
                value = str(value)
            return True, value
        if cmd in {"queue", "start"}:
            return True, self._next_request()
        return False, f"unknown command: {cmd}"

    def _status(self) -> dict[str, Any]:
        return {
            "devices": [spec.name for spec in self.devices.values()],
            "devicefailures": {},
            "setups": (sorted(self.loaded_setups), sorted(self.setups)),
            "status": self.status,
            "mode": self.mode,
            "requests": [],
            "current_script": [""],
            "watch": {},
            "eta": (0, None),
        }

    def _cache_keys(self, query: str) -> list[tuple[str, Any]]:
        query = query.lower()
        if "," in query:
            return [
                (key, self.cache[key]) for key in query.split(",") if key in self.cache
            ]
        if query.endswith("/"):
            return sorted((k, v) for k, v in self.cache.items() if k.startswith(query))
        if query in self.cache:
            return [(query, self.cache[query])]
        return []

    def _messages(self, limit: str | int | None) -> list[tuple]:
        try:
            count = int(limit) if limit is not None else len(self.messages)
        except (TypeError, ValueError):
            count = len(self.messages)
        if count <= 0:
            return []
        return list(self.messages[-count:])

    def _complete(self, fullstring: str, lastword: str) -> list[str]:
        return list(self.completions.get((fullstring, lastword), []))

    def _eval(self, expr: str) -> Any:
        if expr in self.eval_table:
            value = self.eval_table[expr]
            return value() if callable(value) else value
        if expr in _DEFAULT_EVALS:
            return _DEFAULT_EVALS[expr]
        if expr == "session.getSetupInfo()":
            return {name: spec.as_setup_info() for name, spec in self.setups.items()}
        if ".pollParams(" in expr and expr.endswith(")"):
            return None

        value = self._eval_param_info(expr)
        if value is not _UNKNOWN_EVAL:
            return value
        value = self._eval_device_expr(expr)
        if value is not _UNKNOWN_EVAL:
            return value

        self.unknown_evals.append(expr)
        return None

    def _eval_param_info(self, expr: str) -> dict[str, Any] | object:
        prefix = "dict((pn, pi.serialize()) for (pn, pi) in session.getDevice("
        suffix = ").parameters.items())"
        devname = self._expr_arg(expr, prefix, suffix)
        if devname is _UNKNOWN_EVAL:
            return _UNKNOWN_EVAL
        device = self.devices.get(devname.lower())
        if device is None:
            return {}
        return dict(device.param_info)

    def _eval_device_expr(self, expr: str) -> Any:
        lookups = {
            ").classes": lambda device: list(device.params.get("classes", [])),
            ").read()": lambda device: device.params.get("value"),
            ").valueInfo()": lambda device: None,
            ").valuetype": lambda device: device.valuetype,
        }
        for suffix, lookup in lookups.items():
            device = self._device_from_expr(expr, "session.getDevice(", suffix)
            if device is not None:
                return lookup(device)
        return _UNKNOWN_EVAL

    def _device_from_expr(
        self, expr: str, prefix: str, suffix: str
    ) -> DeviceSpec | None:
        devname = self._expr_arg(expr, prefix, suffix)
        if devname is _UNKNOWN_EVAL:
            return None
        return self.devices.get(devname.lower())

    def _expr_arg(self, expr: str, prefix: str, suffix: str) -> str | object:
        if not expr.startswith(prefix) or not expr.endswith(suffix):
            return _UNKNOWN_EVAL
        return ast.literal_eval(expr[len(prefix) : -len(suffix)])

    def _next_request(self) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        return request_id


class FakeClientTransport:
    """Implements the 6-method :class:`ClientTransport` contract in-process."""

    def __init__(self, daemon: FakeDaemon):
        self.daemon = daemon
        self.serializer = None
        self._events: queue.Queue = queue.Queue()
        self._pending_reply: tuple[bool, Any] | object = _NO_REPLY

    # -- client-side contract ------------------------------------------------

    def connect(self, conndata):
        self.daemon.attach(self)
        self._pending_reply = (True, self.daemon.banner())

    def connect_events(self, conndata):
        # Event queue is already set up; nothing to do.
        pass

    def disconnect(self):
        self.daemon.detach(self)
        # Unblock recv_event so the real event thread exits cleanly via the
        # self.disconnecting branch in NicosClient.event_handler.
        self._events.put(_EVENT_SENTINEL)

    def send_command(self, cmdname, args):
        self._pending_reply = self.daemon.handle(cmdname, args)

    def recv_reply(self):
        reply = self._pending_reply
        self._pending_reply = _NO_REPLY
        if reply is _NO_REPLY:
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

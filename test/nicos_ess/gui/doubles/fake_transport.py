"""Small in-process daemon transport for GUI tests."""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nicos.core import MASTER
from nicos.protocols.cache import OP_TELL, cache_dump
from nicos.protocols.daemon import (
    ClientTransport as BaseClientTransport,
    DAEMON_EVENTS,
    STATUS_IDLE,
)
from nicos.protocols.daemon.classic import PROTO_VERSION


_EVENT_SENTINEL = object()
_NO_REPLY = object()
_TEST_DIR = Path(__file__).resolve().parents[3]
_GUI_TEST_ROOT = _TEST_DIR / "root"


@dataclass
class DeviceSpec:
    name: str
    valuetype: Any
    params: dict[str, Any] = field(default_factory=dict)
    param_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class SetupSpec:
    """Subset of NICOS setup metadata exposed over client.eval()."""

    name: str
    description: str = ""
    group: str = "optional"
    display_order: int = 50
    devices: list[str] = field(default_factory=list)


class FakeDaemon:
    """In-memory daemon model for GUI client tests.

    We do not delegate to ``Session.readSetupInfo()`` because that requires
    real setup files; the fake speaks the same wire-shape but reads it from
    in-memory specs.
    """

    def __init__(
        self,
        *,
        user_level: int = 20,
        daemon_version: str = "fake-1.0",
        protocol_version: int = PROTO_VERSION,
    ):
        self.banner = {
            "daemon_version": daemon_version,
            "protocol_version": protocol_version,
            "pw_hashing": "plain",
        }
        self.user_level = user_level
        self.status = (STATUS_IDLE, -1)
        self.mode = MASTER
        self.devices = {}
        self.setups = {}
        self.loaded_setups = set()
        self.cache = {}
        self.messages = []
        self.datasets = []
        self.evals = {}
        self.command_log = []
        self.unknown_evals = []
        self.unknown_commands = []
        self._next_request_id = 1
        self._transports = []
        self._seed_gui_defaults()

    def _seed_gui_defaults(self):
        """Seed exact ``client.eval(...)`` answers used by GUI panels at startup.

        These are wire-level replies from the daemon to the production GUI
        client. They are not shared with UnitTestSession
        (test/nicos_ess/device_harness.py), which models in-process Python
        access for direct device tests.
        """
        session_metadata = {
            "session.instrument": "",
            "session.spMode": False,
            "session.alias_config": {},
        }
        experiment_metadata = {
            "session.experiment.name": "exp",
            "session.experiment.title": "",
            "session.experiment.proposal": "",
            "session.experiment.run_title": "",
            "session.experiment.detectors": [],
            "session.experiment.scriptpath": "",
            "session.experiment.get_current_run_number()": 0,
            "session.experiment._canQueryProposals()": False,
            'session.experiment.propinfo["notif_emails"]': [],
            "session.experiment.get_samples()": [],
            # ExpPanel reads proposal/title/users/localcontact/errorbehavior
            # in one tuple expression.
            "session.experiment.proposal, "
            "session.experiment.title, "
            "session.experiment.users, "
            "session.experiment.localcontact, "
            "session.experiment.errorbehavior": ("", "", [], [], "abort"),
        }
        config_defaults = {
            "config.nicos_root": str(_GUI_TEST_ROOT),
            "config.logging_path": "log",
        }

        self.evals.update(session_metadata)
        self.evals.update(experiment_metadata)
        self.evals.update(config_defaults)
        self._refresh_state_evals()

    def _refresh_state_evals(self):
        self.evals["session.loaded_setups"] = set(self.loaded_setups)
        self.evals["session.devices"] = dict(self.devices)
        self.evals["session.getSetupInfo()"] = {
            name: {
                "description": setup.description,
                "devices": list(setup.devices),
                "display_order": setup.display_order,
                "extended": {},
            }
            for name, setup in self.setups.items()
        }
        self.evals["session.readSetupInfo()"] = {
            name: {
                "description": setup.description,
                "devices": {
                    devname: (
                        "",
                        {
                            "visibility": self.devices.get(
                                devname, DeviceSpec(devname, object)
                            ).params.get("visibility", ("devlist",))
                        },
                    )
                    for devname in setup.devices
                },
                "display_order": setup.display_order,
                "includes": [],
                "excludes": [],
                "modules": [],
                "alias_config": {},
                "startupcode": "",
                "sysconfig": {},
                "extended": {},
                "group": setup.group,
            }
            for name, setup in self.setups.items()
        }
        self.evals[
            '{d.name: d.alias for d in session.devices.values() '
            'if "alias" in d.parameters}'
        ] = {}

    def attach(self, transport):
        self._transports.append(transport)

    def detach(self, transport):
        if transport in self._transports:
            self._transports.remove(transport)

    def add_device(self, device, *, setup=None, load_setup=False):
        self.devices[device.name] = device
        if setup is not None:
            setup_spec = self.add_setup(setup, loaded=load_setup)
            if device.name not in setup_spec.devices:
                setup_spec.devices.append(device.name)
        for param, value in device.params.items():
            self.set_cache(f"{device.name.lower()}/{param}", value)
            self.evals[f"{device.name}.{param}"] = value
        self.evals[f"{device.name}.pollParams()"] = None
        self.evals[f"session.getDevice({device.name!r}).read()"] = (
            device.params.get("value")
        )
        self.evals[f"session.getDevice({device.name!r}).valuetype"] = device.valuetype
        self.evals[
            "dict((pn, pi.serialize()) for (pn, pi) in "
            f"session.getDevice({device.name!r}).parameters.items())"
        ] = dict(device.param_info)
        self._refresh_state_evals()
        return device

    def add_setup(self, setup, *, loaded=False, **kwargs):
        if not isinstance(setup, SetupSpec):
            setup = SetupSpec(setup, **kwargs)
        self.setups.setdefault(setup.name, setup)
        if loaded:
            self.loaded_setups.add(setup.name)
        self._refresh_state_evals()
        return self.setups[setup.name]

    def set_cache(self, key, value):
        self.cache[key.lower()] = value

    def add_message(self, message):
        self.messages.append(message)
        return message

    def handle(self, command, args):
        self.command_log.append((command, args))

        if command == "authenticate":
            return True, {"user_level": self.user_level}
        if command in {"eventmask", "eventunmask", "keepalive", "quit"}:
            return True, None
        if command in {"queue", "start"}:
            request_id = self._next_request_id
            self._next_request_id += 1
            return True, request_id
        if command == "getstatus":
            return True, {
                "devices": list(self.devices),
                "devicefailures": {},
                "setups": (sorted(self.loaded_setups), sorted(self.setups)),
                "script": "",
                "status": self.status,
                "mode": self.mode,
                "requests": [],
                "current_script": [""],
                "watch": {},
                "eta": (0, None),
            }
        if command == "getdataset":
            return True, list(self.datasets)
        if command == "getmessages":
            return True, list(self.messages)
        if command == "getcachekeys":
            return True, self._cache_reply(args[0])
        if command == "complete":
            return True, []
        if command == "eval":
            expr, stringify = args
            if expr not in self.evals:
                self.unknown_evals.append(expr)
                return True, None
            value = self.evals[expr]
            return True, str(value) if stringify and value is not None else value

        self.unknown_commands.append(command)
        return False, f"unexpected command: {command}"

    def _cache_reply(self, query):
        query = query.lower()
        keys = query.split(",") if "," in query else [query]
        if len(keys) > 1:
            return [(key, self.cache[key]) for key in keys if key in self.cache]
        if query.endswith("/"):
            return sorted((k, v) for k, v in self.cache.items() if k.startswith(query))
        if query in self.cache:
            return [(query, self.cache[query])]
        return []

    def push(self, event, data, blobs=None):
        if event not in DAEMON_EVENTS:
            raise ValueError(f"unknown event {event!r}")
        for transport in list(self._transports):
            transport.deliver_event(event, data, blobs or [])

    def push_cache(self, key, value, *, timestamp=0.0, op=OP_TELL):
        self.set_cache(key, value)
        dumped = cache_dump(value) if value is not None else ""
        self.push("cache", (timestamp, key.lower(), op, dumped))

    def push_setup(self, loaded=None):
        if loaded is not None:
            self.loaded_setups = set(loaded)
            self._refresh_state_evals()
        self.push("setup", (sorted(self.loaded_setups), sorted(self.setups)))

    def push_message(self, message):
        self.add_message(message)
        self.push("message", message)

    def push_status(self, status):
        self.status = status
        self.push("status", status)

    def push_mode(self, mode):
        self.mode = mode
        self.push("mode", mode)

    def push_simmessage(self, message):
        self.push("simmessage", message)


class FakeClientTransport(BaseClientTransport):
    def __init__(self, daemon):
        self.daemon = daemon
        self.serializer = None
        self._event_mask = set()
        self._events = queue.Queue()
        self._pending_reply = _NO_REPLY

    def connect(self, conndata):
        self.daemon.attach(self)
        self._pending_reply = (True, self.daemon.banner)

    def connect_events(self, conndata):
        pass

    def disconnect(self):
        self.daemon.detach(self)
        self._events.put(_EVENT_SENTINEL)

    def send_command(self, cmdname, args):
        if cmdname == "eventmask" and args:
            self._event_mask.update(args[0])
        elif cmdname == "eventunmask" and args:
            self._event_mask.difference_update(args[0])
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

    def deliver_event(self, name, data, blobs):
        if name not in self._event_mask:
            self._events.put((name, data, blobs))

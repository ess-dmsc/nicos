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

"""Helpers for fast, isolated unit tests of NICOS devices.

The harnesses in this module deliberately monkeypatch the module-level
``nicos.session`` singleton used by NICOS devices. The patching is scoped to
context managers and always restored before control returns to the caller.
"""

from collections import defaultdict
from contextlib import contextmanager
from logging import DEBUG, NullHandler, getLogger
from time import monotonic
from types import SimpleNamespace

from nicos import session as nicos_session
from nicos.core import (
    MASTER,
    MAIN,
    POLLER,
    SIMULATION,
    AccessError,
    CacheLockError,
    ConfigurationError,
    UsageError,
)


class _UnitClock:
    def __init__(self):
        self.time = monotonic()

    def tick(self, dt):
        self.time += max(0.0, float(dt))

    def wait(self, until):
        self.time = max(self.time, float(until))


class InMemoryCache:
    """Subset of CacheClient API used by NICOS devices in unit tests.

    Method signatures intentionally mirror ``CacheClient`` even when some
    arguments are unused in this in-memory implementation.
    """

    def __init__(self):
        self._data = {}
        self._history = defaultdict(list)
        self._callbacks = defaultdict(list)
        self._locks = set()
        self._rewrites = {}
        self._raw = {}

    def _cache_key(self, dev, key):
        return f"{dev}/{key}".lower()

    def addCallback(self, dev, key, function):
        self._callbacks[self._cache_key(dev, key)].append(function)

    def removeCallback(self, dev, key, function):
        cache_key = self._cache_key(dev, key)
        callbacks = self._callbacks.get(cache_key, [])
        if function in callbacks:
            callbacks.remove(function)
        if not callbacks and cache_key in self._callbacks:
            del self._callbacks[cache_key]

    def get(self, dev, key, default=None, mintime=None):
        cache_key = self._cache_key(dev, key)
        value = self._data.get(cache_key)
        if value is None:
            return default
        cached_value, timestamp = value
        if mintime is not None and timestamp < mintime:
            return default
        return cached_value

    def put(self, dev, key, value, time=None, ttl=None, flag=""):
        del ttl, flag
        timestamp = monotonic() if time is None else float(time)
        cache_key = self._cache_key(dev, key)
        self._data[cache_key] = (value, timestamp)
        self._history[cache_key].append((timestamp, value))
        for callback in list(self._callbacks.get(cache_key, ())):
            callback(cache_key, value, timestamp)

    def put_raw(self, key, value, time=None, ttl=None, flag=""):
        del ttl, flag
        timestamp = monotonic() if time is None else float(time)
        self._raw[key] = (value, timestamp)

    def clear(self, dev, exclude=()):
        prefix = f"{dev}/".lower()
        excluded = {str(name).lower() for name in exclude}
        for cache_key in list(self._data):
            if not cache_key.startswith(prefix):
                continue
            if cache_key.rsplit("/", 1)[-1] in excluded:
                continue
            del self._data[cache_key]

    def invalidate(self, dev, key):
        self._data.pop(self._cache_key(dev, key), None)

    def history(self, dev, key, fromtime, totime, interval=None):
        del interval
        cache_key = self._cache_key(dev, key)
        return [
            (timestamp, value)
            for timestamp, value in self._history.get(cache_key, ())
            if fromtime <= timestamp <= totime
        ]

    def lock(self, key, ttl=None, unlock=False, sessionid=None):
        del ttl, sessionid
        if unlock:
            self._locks.discard(key)
            return
        if key in self._locks:
            raise CacheLockError("already locked")
        self._locks.add(key)

    def unlock(self, key, sessionid=None):
        del sessionid
        self._locks.discard(key)

    def setRewrite(self, to_prefix, from_prefix):
        self._rewrites[to_prefix.lower()] = from_prefix.lower()

    def unsetRewrite(self, to_prefix):
        self._rewrites.pop(to_prefix.lower(), None)

    def put_aged(
        self, dev, key, value, age_seconds, *, now=None, ttl=None, flag=""
    ):
        """Convenience helper for maxage tests that need stale cache entries."""
        reference_time = monotonic() if now is None else float(now)
        stale_time = reference_time - max(0.0, float(age_seconds))
        self.put(dev, key, value, time=stale_time, ttl=ttl, flag=flag)


class UnitTestSession:
    """Minimal session implementation for direct device unit tests.

    Method signatures intentionally mirror ``Session`` so NICOS device code can
    run unchanged inside harness tests.
    """

    sessiontype = MAIN

    def __init__(self):
        self.devices = {}
        self.device_case_map = {}
        self.explicit_devices = set()
        self.configured_devices = {}
        self.alias_config = {}
        self.dynamic_devices = {}
        self.loaded_setups = set()
        self.namespace = {}
        self._mode = SIMULATION
        self.clock = _UnitClock()
        self.cache = InMemoryCache()
        self.sessionid = "unit-test-session"
        self._loggers = {}
        self.log = getLogger("nicos.unit")
        if not self.log.handlers:
            self.log.addHandler(NullHandler())
        self.log.setLevel(DEBUG)
        self.log.propagate = False
        self.instrument = SimpleNamespace(name="instrument", instrument="instrument")
        self.experiment = SimpleNamespace(
            proposal="",
            propinfo={},
            run_title="",
            title="",
            sample=SimpleNamespace(get_samples=lambda: []),
            get_current_run_number=lambda: 0,
            proposalpath_of=lambda proposal: "",
        )
        self.daemon_device = SimpleNamespace(
            current_script=lambda: SimpleNamespace(user=SimpleNamespace(level=999))
        )

    @property
    def mode(self):
        return self._mode

    def setMode(self, mode):
        self._mode = mode.lower() if isinstance(mode, str) else mode

    def getLogger(self, name):
        if name in self._loggers:
            return self._loggers[name]
        logger = self.log.getChild(name)
        logger.setLevel(DEBUG)
        self._loggers[name] = logger
        return logger

    def getDevice(self, dev, cls=None, source=None, replace_classes=None):
        del replace_classes
        if isinstance(dev, str):
            if dev in self.devices:
                dev = self.devices[dev]
            else:
                raise ConfigurationError(source, f"device {dev!r} not found")
        if cls is not None and not isinstance(dev, cls):
            raise UsageError(source, f"device must be a {cls}")
        return dev

    def delay(self, secs):
        self.clock.tick(secs)

    def checkParallel(self):
        return False

    def checkAccess(self, required):
        mode = required.get("mode")
        if mode and mode != self.mode:
            raise AccessError(f"mode {mode!r} is required")

    def getExecutingUser(self):
        return SimpleNamespace(level=999)

    def checkUserLevel(self, level=0, user=None):
        user = user or self.getExecutingUser()
        return user.level >= level

    # No-op hooks required by device code paths; keep full Session-compatible
    # signatures and explicitly discard unused parameters.
    def elogEvent(self, eventtype, data):
        del eventtype, data

    def updateLiveData(self, parameters, databuffer, labelbuffers):
        del parameters, databuffer, labelbuffers

    def getSetupInfo(self):
        return {}

    def pnpEvent(self, event, setup_name, description):
        del event, setup_name, description

    def experimentCallback(self, proposal, metadata):
        del proposal, metadata

    def beginActionScope(self, what):
        del what

    def endActionScope(self):
        pass

    def action(self, what):
        del what

    def breakpoint(self, level=0):
        del level


def _auto_value(param_name, param_info):
    candidates = [
        param_info.default,
        f"{param_name}_test",
        1,
        1.0,
        True,
        [],
        {},
        (),
        None,
        "",
    ]
    for candidate in candidates:
        try:
            return param_info.type(candidate)
        except Exception:
            continue
    try:
        return param_info.type()
    except Exception as err:
        raise ValueError(
            f"cannot auto-fill mandatory parameter {param_name!r}; "
            "pass it explicitly in create(...)."
        ) from err


def _capture_current_state():
    """Snapshot the current ``nicos.session`` object state.

    We capture both ``__class__`` and ``__dict__`` because the harness swaps the
    concrete session class (``Session`` vs ``UnitTestSession``), not just fields.
    """
    return {
        "class": nicos_session.__class__,
        "dict": dict(nicos_session.__dict__),
    }


def _restore_state(state):
    """Restore ``nicos.session`` from a snapshot created by ``_capture_current_state``."""
    nicos_session.__class__ = state["class"]
    nicos_session.__dict__.clear()
    nicos_session.__dict__.update(state["dict"])


class DaemonDeviceHarness:
    """Factory for building devices in an isolated daemon-like unit-test session."""

    def __init__(self, session):
        self.session = session
        self._counter = 0

    def mandatory_config(self, devcls):
        config = {}
        for param_name, param_info in devcls.parameters.items():
            if param_name == "name":
                continue
            if param_info.mandatory:
                config[param_name] = _auto_value(param_name, param_info)
        return config

    @contextmanager
    def in_mode(self, mode=None, sessiontype=None):
        old_mode = self.session.mode
        old_sessiontype = self.session.sessiontype
        if mode is not None:
            self.session.setMode(mode)
        if sessiontype is not None:
            self.session.sessiontype = sessiontype
        try:
            yield
        finally:
            self.session.setMode(old_mode)
            self.session.sessiontype = old_sessiontype

    def create(
        self,
        devcls,
        name=None,
        *,
        auto_params=True,
        attached=None,
        mode=None,
        sessiontype=None,
        **config,
    ):
        if auto_params:
            merged = self.mandatory_config(devcls)
            merged.update(config)
        else:
            merged = dict(config)
        if attached:
            merged.update(attached)
        if name is None:
            name = f"{devcls.__name__.lower()}_{self._counter}"
            self._counter += 1
        with self.in_mode(mode=mode, sessiontype=sessiontype):
            return devcls(name, **merged)

    def create_master(self, devcls, name=None, **config):
        """Create a device in master mode (daemon-like single-session tests)."""
        mode = config.pop("mode", MASTER)
        sessiontype = config.pop("sessiontype", MAIN)
        return self.create(
            devcls,
            name,
            mode=mode,
            sessiontype=sessiontype,
            **config,
        )

    def create_sim(self, devcls, name=None, **config):
        """Create a device in simulation mode."""
        mode = config.pop("mode", SIMULATION)
        return self.create(devcls, name, mode=mode, **config)

    def shutdown_all(self):
        for devname in reversed(list(self.session.devices)):
            device = self.session.devices.get(devname)
            if device is None:
                continue
            try:
                device.shutdown()
            except Exception:
                continue


@contextmanager
def isolated_daemon_device_harness():
    """Yield a daemon-style harness backed by a temporary ``UnitTestSession``.

    The global ``nicos.session`` object is replaced in-place for the duration of
    the context and fully restored afterwards, even on exceptions.
    """
    old_class = nicos_session.__class__
    old_dict = dict(nicos_session.__dict__)
    # Swap the singleton to a unit-test session object without changing import sites.
    nicos_session.__class__ = UnitTestSession
    UnitTestSession.__init__(nicos_session)
    harness = DaemonDeviceHarness(nicos_session)
    try:
        yield harness
    finally:
        harness.shutdown_all()
        nicos_session.__class__ = old_class
        nicos_session.__dict__.clear()
        nicos_session.__dict__.update(old_dict)


class DeviceHarness:
    """Two-session harness with explicit daemon/poller role activation.

    Each role stores an independent snapshot of a ``UnitTestSession`` state.
    ``activate(role)`` swaps that snapshot into ``nicos.session`` so device code
    sees the expected role-specific session while keeping tests single-process.
    """

    DAEMON_ROLE = "daemon"
    POLLER_ROLE = "poller"
    ROLE_SESSIONTYPES = {
        DAEMON_ROLE: MAIN,
        POLLER_ROLE: POLLER,
    }

    def __init__(self, role_states):
        self._role_states = role_states
        self._counter = 0

    @contextmanager
    def activate(self, role):
        """Temporarily expose one role state as the active ``nicos.session``."""
        if role not in self._role_states:
            raise KeyError(f"unknown role {role!r}")
        # Preserve whatever session state is currently active for nested usage.
        old = _capture_current_state()
        _restore_state(self._role_states[role])
        try:
            yield nicos_session
        finally:
            # Persist role-side mutations, then restore the previously active state.
            self._role_states[role] = _capture_current_state()
            _restore_state(old)

    def mandatory_config(self, devcls):
        config = {}
        for param_name, param_info in devcls.parameters.items():
            if param_name == "name":
                continue
            if param_info.mandatory:
                config[param_name] = _auto_value(param_name, param_info)
        return config

    def create(
        self,
        role,
        devcls,
        name=None,
        *,
        auto_params=True,
        attached=None,
        mode=None,
        sessiontype=None,
        **config,
    ):
        """Create a device under a specific role context.

        ``mode`` and ``sessiontype`` are temporary constructor-time overrides:
        they are applied while the device is instantiated and then reset on the
        active role session to avoid leaking settings into later calls.
        """
        if auto_params:
            merged = self.mandatory_config(devcls)
            merged.update(config)
        else:
            merged = dict(config)
        if attached:
            merged.update(attached)
        if name is None:
            name = f"{devcls.__name__.lower()}_{self._counter}"
            self._counter += 1
        with self.activate(role) as active_session:
            old_mode = active_session.mode
            old_sessiontype = active_session.sessiontype
            if mode is not None:
                active_session.setMode(mode)
            if sessiontype is not None:
                active_session.sessiontype = sessiontype
            try:
                return devcls(name, **merged)
            finally:
                active_session.setMode(old_mode)
                active_session.sessiontype = old_sessiontype

    def run(self, role, func, *args, **kwargs):
        """Run ``func`` while a specific role snapshot is active."""
        with self.activate(role):
            return func(*args, **kwargs)

    def run_daemon(self, func, *args, **kwargs):
        return self.run(self.DAEMON_ROLE, func, *args, **kwargs)

    def run_poller(self, func, *args, **kwargs):
        return self.run(self.POLLER_ROLE, func, *args, **kwargs)

    def get_device(self, role, name):
        with self.activate(role):
            return nicos_session.getDevice(name)

    def create_master(self, role, devcls, name=None, **config):
        """Create a role-specific device in master mode with matching sessiontype."""
        mode = config.pop("mode", MASTER)
        sessiontype = config.pop("sessiontype", self.ROLE_SESSIONTYPES[role])
        return self.create(
            role,
            devcls,
            name,
            mode=mode,
            sessiontype=sessiontype,
            **config,
        )

    def create_daemon(self, devcls, name=None, **config):
        return self.create_master(self.DAEMON_ROLE, devcls, name=name, **config)

    def create_poller(self, devcls, name=None, **config):
        return self.create_master(self.POLLER_ROLE, devcls, name=name, **config)

    def create_pair(self, devcls, name=None, *, shared=None, daemon=None, poller=None):
        """Create daemon+poller copies with shared defaults and per-role overrides."""
        daemon_kwargs = dict(shared or {})
        daemon_kwargs.update(daemon or {})
        poller_kwargs = dict(shared or {})
        poller_kwargs.update(poller or {})
        daemon_dev = self.create_daemon(devcls, name=name, **daemon_kwargs)
        poller_dev = self.create_poller(devcls, name=name, **poller_kwargs)
        return daemon_dev, poller_dev

    def shutdown_all(self):
        for role in list(self._role_states):
            with self.activate(role) as active_session:
                for devname in reversed(list(active_session.devices)):
                    device = active_session.devices.get(devname)
                    if device is None:
                        continue
                    try:
                        device.shutdown()
                    except Exception:
                        continue


@contextmanager
def isolated_device_harness():
    """Yield a daemon+poller harness that shares one in-memory cache.

    The daemon and poller sessions are initialized once, then stored as role
    snapshots inside ``DeviceHarness``. The caller interacts through role-aware
    create/run helpers while this context keeps global session state isolated.
    """
    old = _capture_current_state()
    shared_cache = InMemoryCache()

    daemon = UnitTestSession()
    daemon.cache = shared_cache
    daemon.sessionid = "unit-daemon"
    daemon.setMode(MASTER)
    daemon.sessiontype = MAIN

    poller = UnitTestSession()
    poller.cache = shared_cache
    poller.sessionid = "unit-poller"
    poller.setMode(MASTER)
    poller.sessiontype = POLLER

    role_states = {
        "daemon": {"class": daemon.__class__, "dict": dict(daemon.__dict__)},
        "poller": {"class": poller.__class__, "dict": dict(poller.__dict__)},
    }
    harness = DeviceHarness(role_states)
    try:
        yield harness
    finally:
        harness.shutdown_all()
        _restore_state(old)

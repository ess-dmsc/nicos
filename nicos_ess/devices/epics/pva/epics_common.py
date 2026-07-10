"""Channel-table based EPICS device bases.

The channel table is the ``_epics_channels`` dict on a device class. It maps a
logical channel name such as ``"readback"`` to an :class:`EpicsChannelInfo`
that describes the PV suffix, the cache key and the update policy. Devices
declare the table, :class:`EpicsChannelComponent` talks to EPICS, and
:class:`EpicsDeviceBase` turns monitor updates into cache writes.

See ``nicos_ess/devices/epics/epics_integration_guide.md`` for a walkthrough.
"""

import os
import threading
import time
from collections.abc import Iterable
from contextlib import suppress
from copy import copy
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    CommunicationError,
    ConfigurationError,
    InvalidValueError,
    Override,
    Param,
    PositionError,
    ProgrammingError,
    floatrange,
    none_or,
    oneof,
    pvname,
    status,
)
from nicos_ess.devices.mixins import HasNexusConfig

DEFAULT_EPICS_PROTOCOL = os.environ.get("DEFAULT_EPICS_PROTOCOL", "pva")


def _wrapper_errors():
    # Exceptions raised by protocol wrappers: bare TimeoutError (p4p and
    # caproto) and p4p's RemoteError for server-rejected operations.
    errors = [TimeoutError]
    with suppress(ImportError):
        from p4p.client.thread import RemoteError

        errors.append(RemoteError)
    return tuple(errors)


_WRAPPER_ERRORS = _wrapper_errors()

# Canonical disconnect status, used by both the monitor-callback path and the
# fresh status path so a lost connection reports the same way either way.
LOST_CONNECTION_STATUS = (status.UNKNOWN, "lost connection to EPICS")


class EpicsChannelKind(Enum):
    READBACK = "readback"
    SETPOINT = "setpoint"
    STATUS = "status"
    COMMAND = "command"


@dataclass(frozen=True)
class EpicsChannelInfo:
    # "" means "cache under the channel name"; None means "do not cache".
    cache_key: Optional[str]
    pv_suffix: str
    kind: EpicsChannelKind
    as_string: bool = False
    subscribe: bool = True
    # Non-primary channels can opt into connection-loss status handling.
    affects_status: bool = False
    # True when monitor updates should recompute NICOS status.
    refresh_status_on_update: bool = False
    # PV source. Default is device._default_pv_prefix_attr + pv_suffix.
    # pv_prefix_attr overrides the root; pv_name_attr names a complete PV.
    pv_prefix_attr: Optional[str] = None
    pv_name_attr: Optional[str] = None
    allow_missing_pv: bool = False
    connect_on_startup: bool = True
    # Cache key for the display limits delivered with updates on this
    # channel (e.g. "abslimits" on a write channel).
    limits_cache_key: Optional[str] = None
    # True for EPICS enum PVs. Readbacks are delivered as choice strings.
    is_enum: bool = False

    def __post_init__(self):
        if self.is_enum:
            object.__setattr__(self, "as_string", True)
        if self.pv_name_attr and self.pv_suffix:
            raise ValueError(
                "pv_name_attr names a complete PV; use pv_suffix='' or "
                "pv_prefix_attr for prefix + suffix PVs"
            )
        if self.pv_name_attr and self.pv_prefix_attr:
            raise ValueError("pv_name_attr and pv_prefix_attr are mutually exclusive")
        if self.kind == EpicsChannelKind.COMMAND and self.cache_key is not None:
            raise ValueError("command channels must not cache values")
        if self.kind == EpicsChannelKind.COMMAND and (
            self.subscribe or self.connect_on_startup
        ):
            raise ValueError(
                "command channels must not subscribe or connect at startup"
            )


@dataclass(frozen=True)
class ChannelUpdate:
    channel: str
    value: object
    units: str = ""
    limits: Optional[tuple] = None
    severity: int = status.OK
    message: str = ""
    pv_name: str = ""
    source_id: Optional[str] = None


@dataclass(frozen=True)
class ConnectionUpdate:
    channel: str
    is_connected: bool
    pv_name: str = ""
    source_id: Optional[str] = None


class EpicsEnumParam(oneof):
    """Marker for a oneof whose choices come from an EPICS enum PV."""

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.__doc__ = f"EPICS enum choices from channel {channel!r}"

    def __call__(self, val=None):
        return val if not self.vals else super().__call__(val)

    def set_choices(self, choices):
        self.vals = tuple(choices)
        self.__doc__ = "one of " + ", ".join(map(repr, self.vals))


class EpicsParameters(HasNexusConfig):
    parameters = {
        "epicstimeout": Param(
            "Timeout for getting EPICS PVs",
            type=none_or(floatrange(0.1, 60)),
            userparam=False,
            mandatory=False,
            default=3.0,
        ),
        "monitor": Param("Use a PV monitor", type=bool, default=True),
        "pva": Param("Use pva", type=bool, default=DEFAULT_EPICS_PROTOCOL == "pva"),
    }
    parameter_overrides = {
        "pollinterval": Override(default=None),
        "maxage": Override(default=None),
    }
    hardware_access = True

    def _format_float_as_string(self, value, fmtstr):
        if abs(value) >= 1e10:
            return f"{value:.2g}"
        return fmtstr % value

    def format(self, value, unit=False):
        if isinstance(value, list):
            value = tuple(value)

        try:
            if isinstance(value, float):
                ret = self._format_float_as_string(value, self.fmtstr)
            else:
                ret = self.fmtstr % value
        except (TypeError, ValueError):
            ret = str(value)

        if unit and self.unit:
            return ret + " " + self.unit
        return ret

    def formatParam(self, param, value, use_repr=True):
        fmtstr = self._getParamConfig(param).fmtstr
        if fmtstr == "%r" and not use_repr:
            fmtstr = "%s"
        if fmtstr == "main":
            fmtstr = self.fmtstr

        if isinstance(value, float):
            try:
                return self._format_float_as_string(value, fmtstr)
            except (TypeError, ValueError):
                return repr(value)

        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            new_value = []
            for item in value:
                try:
                    if isinstance(item, float):
                        new_value.append(self._format_float_as_string(item, fmtstr))
                    else:
                        new_value.append(fmtstr % item)
                except (TypeError, ValueError):
                    new_value.append(repr(item))
            return "(" + ", ".join(new_value) + ")"

        try:
            return fmtstr % value
        except (TypeError, ValueError):
            return repr(value)


def create_wrapper(timeout, use_pva):
    if use_pva:
        from nicos.devices.epics.pva.p4p import P4pWrapper

        return P4pWrapper(timeout)
    else:
        from nicos.devices.epics.pva.caproto import CaprotoWrapper

        return CaprotoWrapper(timeout)


def get_from_cache_or(device, cache_key, func, maxage=None):
    if cache_key is None:
        return func()
    if not getattr(device, "monitor", False) or not getattr(device, "_cache", None):
        return func()
    if maxage == 0:
        return func()

    mintime = None if maxage is None else time.time() - maxage
    # Ellipsis sentinel, not None: a cached value can legitimately be None.
    result = device._cache.get(device._name, cache_key, Ellipsis, mintime=mintime)
    if result is not Ellipsis:
        return result
    return func()


def resolve_channel_pv_names(device, epics_channels, default_pv_prefix_attr=None):
    """Resolve logical channel names to PV names."""
    names = {}
    for channel, info in epics_channels.items():
        if info.pv_name_attr:
            names[channel] = getattr(device, info.pv_name_attr, None)
        else:
            pv_prefix_attr = (
                default_pv_prefix_attr
                if info.pv_prefix_attr is None
                else info.pv_prefix_attr
            )
            prefix = getattr(device, pv_prefix_attr, None) if pv_prefix_attr else None
            names[channel] = None if prefix is None else f"{prefix}{info.pv_suffix}"
        if names[channel] is None and not info.allow_missing_pv:
            raise ConfigurationError(
                device,
                f"EPICS channel {channel!r} resolved to no PV; set its "
                "pv_name_attr/pv_prefix_attr or mark it allow_missing_pv=True",
            )
    return names


def worst_status(*candidates):
    """Return the (severity, message) candidate with the highest severity."""
    if not candidates:
        return status.OK, ""
    return max(candidates, key=lambda candidate: candidate[0])


def readback_channel(
    pv_suffix,
    cache_key="",
    *,
    as_string=False,
    primary=False,
    subscribe=True,
    connect_on_startup=True,
    affects_status=None,
    refresh_status=None,
    pv_prefix_attr=None,
    pv_name_attr=None,
    allow_missing_pv=False,
    limits_cache_key=None,
    is_enum=False,
):
    if affects_status is None:
        affects_status = primary
    if refresh_status is None:
        refresh_status = primary
    return EpicsChannelInfo(
        cache_key,
        pv_suffix,
        EpicsChannelKind.READBACK,
        as_string=as_string,
        subscribe=subscribe,
        affects_status=affects_status,
        refresh_status_on_update=refresh_status,
        pv_prefix_attr=pv_prefix_attr,
        pv_name_attr=pv_name_attr,
        allow_missing_pv=allow_missing_pv,
        connect_on_startup=connect_on_startup,
        limits_cache_key=limits_cache_key,
        is_enum=is_enum,
    )


def setpoint_channel(
    pv_suffix,
    cache_key="target",
    *,
    as_string=False,
    subscribe=True,
    connect_on_startup=True,
    refresh_status=False,
    pv_prefix_attr=None,
    pv_name_attr=None,
    allow_missing_pv=False,
    limits_cache_key=None,
    is_enum=False,
):
    return EpicsChannelInfo(
        cache_key,
        pv_suffix,
        EpicsChannelKind.SETPOINT,
        as_string=as_string,
        subscribe=subscribe,
        refresh_status_on_update=refresh_status,
        pv_prefix_attr=pv_prefix_attr,
        pv_name_attr=pv_name_attr,
        allow_missing_pv=allow_missing_pv,
        connect_on_startup=connect_on_startup,
        limits_cache_key=limits_cache_key,
        is_enum=is_enum,
    )


def status_channel(
    pv_suffix,
    cache_key="",
    *,
    as_string=False,
    connect_on_startup=True,
    affects_status=True,
    refresh_status=True,
    pv_prefix_attr=None,
    pv_name_attr=None,
    allow_missing_pv=False,
    is_enum=False,
):
    return EpicsChannelInfo(
        cache_key,
        pv_suffix,
        EpicsChannelKind.STATUS,
        as_string=as_string,
        affects_status=affects_status,
        refresh_status_on_update=refresh_status,
        pv_prefix_attr=pv_prefix_attr,
        pv_name_attr=pv_name_attr,
        allow_missing_pv=allow_missing_pv,
        connect_on_startup=connect_on_startup,
        is_enum=is_enum,
    )


def command_channel(
    pv_suffix,
    *,
    pv_prefix_attr=None,
    pv_name_attr=None,
    allow_missing_pv=False,
    is_enum=False,
):
    return EpicsChannelInfo(
        None,
        pv_suffix,
        EpicsChannelKind.COMMAND,
        subscribe=False,
        pv_prefix_attr=pv_prefix_attr,
        pv_name_attr=pv_name_attr,
        allow_missing_pv=allow_missing_pv,
        connect_on_startup=False,
        is_enum=is_enum,
    )


def enum_readback_channel(pv_suffix, cache_key="", **kwargs):
    return readback_channel(pv_suffix, cache_key=cache_key, is_enum=True, **kwargs)


def enum_setpoint_channel(pv_suffix, cache_key="target", **kwargs):
    return setpoint_channel(pv_suffix, cache_key=cache_key, is_enum=True, **kwargs)


def enum_status_channel(pv_suffix, cache_key="", **kwargs):
    return status_channel(pv_suffix, cache_key=cache_key, is_enum=True, **kwargs)


def enum_command_channel(pv_suffix, **kwargs):
    return command_channel(pv_suffix, is_enum=True, **kwargs)


def make_read_channels(*, as_string=False):
    """Channel table for a plain readable: one 'read' channel on readpv."""
    return {
        "read": readback_channel(
            "",
            cache_key="value",
            primary=True,
            as_string=as_string,
            pv_name_attr="readpv",
        ),
    }


def make_rw_channels(
    *,
    as_string=False,
    write_refresh_status=False,
    write_limits_cache_key=None,
):
    """Channel table for read/write/target devices (readpv/writepv/targetpv)."""
    channels = make_read_channels(as_string=as_string)
    channels["write"] = setpoint_channel(
        "",
        "target",
        as_string=as_string,
        pv_name_attr="writepv",
        refresh_status=write_refresh_status,
        limits_cache_key=write_limits_cache_key,
    )
    channels["target"] = setpoint_channel(
        "",
        "target",
        as_string=as_string,
        pv_name_attr="targetpv",
        allow_missing_pv=True,
        refresh_status=write_refresh_status,
    )
    return channels


class EpicsChannelComponent:
    """Owns the EPICS wrapper: connect, subscribe, blocking get/put.

    The ``get_*``/``put_*``/``wait_for`` calls block on the caller's thread
    (daemon/GUI request threads). The monitor callbacks registered via
    ``subscribe_channels`` run on the wrapper's own callback thread(s); this
    component never touches the NICOS cache itself - it only marshals wrapper
    data into ``ChannelUpdate``/``ConnectionUpdate`` and hands them to the
    device-supplied callbacks.
    """

    def __init__(
        self,
        epics_channels,
        pv_names_by_channel,
        *,
        timeout=3.0,
        use_pva=True,
        wrapper=None,
    ):
        self.epics_channels = epics_channels
        self.pv_names_by_channel = pv_names_by_channel
        self.timeout = timeout
        self.use_pva = use_pva
        self.wrapper = wrapper
        self._wrapper_injected = wrapper is not None
        self._connected_pvs = set()
        self._simulation = False
        self.subscriptions = []
        self._lock = threading.Lock()

    def pv_name_for(self, channel):
        return self.pv_names_by_channel.get(channel)

    def cache_key_for(self, channel):
        info = self.epics_channels.get(channel)
        if info is None:
            return channel
        if info.kind == EpicsChannelKind.COMMAND:
            return None
        if info.cache_key is None:
            return None
        return info.cache_key or channel

    def pvs_to_connect(self):
        names = []
        for channel in self.epics_channels:
            info = self.epics_channels[channel]
            if info.kind == EpicsChannelKind.COMMAND or not info.connect_on_startup:
                continue
            pv_name = self.pv_name_for(channel)
            if pv_name and pv_name not in names:
                names.append(pv_name)
        return names

    def connect(self, pvs_to_connect=None, simulation=False):
        self.shutdown()
        if not self._wrapper_injected:
            self.wrapper = create_wrapper(self.timeout, self.use_pva)
        self._simulation = simulation
        if simulation:
            return
        if pvs_to_connect is None:
            pvs_to_connect = self.pvs_to_connect()
        for pv in pvs_to_connect:
            self.wrapper.connect_pv(pv)
            with self._lock:
                self._connected_pvs.add(pv)

    def subscribe_channels(self, change_callback, connection_callback=None):
        for channel in self.subscribed_channels():
            self.subscribe_channel(channel, change_callback, connection_callback)

    def subscribed_channels(self):
        return [
            channel
            for channel, info in self.epics_channels.items()
            if info.kind != EpicsChannelKind.COMMAND and info.subscribe
        ]

    def subscribe_channel(
        self,
        channel,
        update_callback,
        connection_callback=None,
        as_string=None,
        source_id=None,
    ):
        """Subscribe one channel.

        ``as_string=None`` uses the channel table's ``as_string``; pass True
        or False to override it for this subscription.
        """
        pv = self.pv_name_for(channel)
        if not pv:
            return None
        if as_string is None:
            as_string = self.epics_channels[channel].as_string
        return self._subscribe_pv(
            pv, channel, update_callback, connection_callback, as_string, source_id
        )

    def _subscribe_pv(
        self,
        pv,
        channel,
        update_callback,
        connection_callback,
        as_string,
        source_id=None,
    ):
        def _on_change(pv_name, param, value, units, limits, severity, message, **kw):
            update_callback(
                ChannelUpdate(
                    channel=channel,
                    value=value,
                    units=units,
                    limits=limits,
                    severity=severity,
                    message=message,
                    pv_name=pv_name,
                    source_id=source_id,
                )
            )

        _on_connection = None
        if connection_callback is not None:

            def _on_connection(pv_name, param, is_connected, **kw):
                connection_callback(
                    ConnectionUpdate(
                        channel=channel,
                        is_connected=is_connected,
                        pv_name=pv_name,
                        source_id=source_id,
                    )
                )

        sub = self.wrapper.subscribe(
            pv, channel, _on_change, _on_connection, as_string=as_string
        )
        with self._lock:
            self.subscriptions.append(sub)
        return sub

    def close_subscription(self, subscription):
        if subscription is None:
            return
        if self.wrapper is not None:
            self.wrapper.close_subscription(subscription)
        with self._lock, suppress(ValueError):
            self.subscriptions.remove(subscription)

    def shutdown(self):
        # The wrapper Context is a process-wide singleton (p4p._CONTEXT); don't
        # close it, only release this component's subscriptions and bookkeeping.
        with self._lock:
            subs = list(self.subscriptions)
            self.subscriptions.clear()
            self._connected_pvs.clear()
        if self.wrapper is not None:
            for sub in subs:
                self.wrapper.close_subscription(sub)
        if not self._wrapper_injected:
            self.wrapper = None

    @staticmethod
    def _ask_wrapper(action, func):
        # Translate wrapper-specific failures into a NICOS error that user
        # scripts and the GUI can handle consistently.
        try:
            return func()
        except CommunicationError:
            raise
        except _WRAPPER_ERRORS as err:
            raise CommunicationError(f"{action}: {str(err) or 'timed out'}") from err

    def _ensure_connected(self, pv_name):
        if self._simulation or not pv_name:
            return
        with self._lock:
            if pv_name in self._connected_pvs:
                return
            self.wrapper.connect_pv(pv_name)
            self._connected_pvs.add(pv_name)

    def _on_pv(self, pv_name, action, func):
        self._ensure_connected(pv_name)
        return self._ask_wrapper(f"error {action} PV {pv_name}", lambda: func(pv_name))

    def get_channel_value(self, channel, as_string=None):
        """Blocking read of a channel's PV.

        ``as_string=None`` uses the channel table's ``as_string``; pass True
        or False to override it for this read.
        """
        if as_string is None:
            info = self.epics_channels.get(channel)
            as_string = info.as_string if info is not None else False
        return self.get_pv_value(self.pv_name_for(channel), as_string)

    def get_pv_value(self, pv_name, as_string=False):
        return self._on_pv(
            pv_name, "reading", lambda pv: self.wrapper.get_pv_value(pv, as_string)
        )

    def get_channel_alarm(self, channel):
        return self._on_pv(
            self.pv_name_for(channel),
            "reading alarm of",
            lambda pv: self.wrapper.get_alarm_status(pv),
        )

    def get_channel_limits(self, channel, default_low=-1e308, default_high=1e308):
        return self._on_pv(
            self.pv_name_for(channel),
            "reading limits of",
            lambda pv: self.wrapper.get_limits(pv, default_low, default_high),
        )

    def get_channel_units(self, channel, default=""):
        return self._on_pv(
            self.pv_name_for(channel),
            "reading units of",
            lambda pv: self.wrapper.get_units(pv, default),
        )

    def get_channel_value_choices(self, channel):
        return self._on_pv(
            self.pv_name_for(channel),
            "reading choices of",
            lambda pv: self.wrapper.get_value_choices(pv),
        )

    def put_channel_value(self, channel, value):
        self._on_pv(
            self.pv_name_for(channel),
            f"writing {value!r} to",
            lambda pv: self.wrapper.put_pv_value(pv, value),
        )

    def wait_for(self, channel, expected, timeout=5.0, precision=None):
        # This opens a second monitor on (pv, channel). The wrapper refcounts
        # connection state per (pvname, pvparam), so while this wait is in
        # flight the primary monitor's disconnect callback is suppressed. The
        # suppression window lasts as long as the wait: keep timeouts on the
        # default few-second scale and never wait for a whole movement here.
        event = threading.Event()

        def matches(value):
            if precision is not None and isinstance(value, (int, float)):
                return abs(value - expected) <= precision
            return value == expected

        def callback(update):
            if matches(update.value):
                event.set()

        sub = self.subscribe_channel(channel, callback)
        try:
            if matches(self.get_channel_value(channel)):
                return
            if not event.wait(timeout):
                raise CommunicationError(
                    f"timeout waiting for {channel} to become {expected}"
                )
        finally:
            self.close_subscription(sub)


class EpicsDeviceBase(EpicsParameters):
    """Turns EPICS monitor callbacks into cache writes; reads from the cache.

    Only the POLLER session subscribes (see ``doInit``), so
    ``_dispatch_channel_update`` / ``_on_connection_change`` run on the wrapper's
    callback thread inside the poller. They write the NICOS cache, which is the
    single synchronisation point - every other session (daemon/GUI) reads those
    values back through the cache via ``get_from_cache_or`` and never sees the
    callback thread. ``doRead``/``doStatus`` with ``maxage=0`` deliberately
    bypass the cache and do a blocking get on the caller's thread instead.

    Subclasses must provide a channel table, in one of two ways:

    * set the ``_epics_channels`` class attribute (channels known statically), or
    * override ``_build_epics_channels()`` (channels that depend on parameters,
      e.g. an optional ``targetpv``); start from ``super()._build_epics_channels()``.

    Subclasses may override:

    * ``_compute_status(maxage)``: the device/movement status hook (e.g. report
      BUSY while moving). Connection-loss and status caching are layered on top
      by ``doStatus`` / ``_status_snapshot``, which should not be overridden.
    * ``_after_subscribe(mode)``: extra initialisation once monitors are wired.

    Read a channel's value with ``_read_channel_cached(channel, maxage)``: it
    honours the cache/poller model above. The ``self._epics.get_*`` methods
    always bypass the cache and block on a direct IOC read.
    """

    _primary_channel = "read"
    _epics_channels = None
    _default_pv_prefix_attr = None
    # Channels currently seen disconnected (replaced by a per-instance set in
    # doPreinit). The class default keeps _status_snapshot working for test
    # doubles that bypass doPreinit; they never fire connection callbacks, so
    # the shared empty frozenset is only ever read, never mutated.
    _disconnected = frozenset()
    # Channels whose PVs are probed at connect time as a startup canary; None
    # means probe all connect_on_startup channels.
    #
    # listing a single channel here asserts that every channel of this
    # device lives on the *same* IOC, so one reachable PV proves the device is
    # there. This holds for a single record (e.g. a motor) but not for composite
    # devices whose channels are served by different IOCs - those must either
    # leave this None or list one channel per IOC, otherwise the device reports
    # connected while half its PVs are dead. Note this only governs the startup
    # probe; live connection loss is still tracked per channel via
    # _on_connection_change / the _disconnected set.
    _connect_channels = None

    def init(self):
        self._clone_epics_enum_params()
        super().init()

    def doPreinit(self, mode):
        self._alarm_state = {}
        self._disconnected = set()
        epics_channels = self._build_epics_channels()
        if not epics_channels:
            raise ProgrammingError(
                self,
                "define _epics_channels (class attribute) or override "
                "_build_epics_channels()",
            )
        self._epics_channels = dict(epics_channels)
        self._epics = self._create_epics_component()
        self._epics.connect(self._pvs_to_connect(), simulation=mode == SIMULATION)
        self._read_epics_enum_param_choices(mode)

    def _clone_epics_enum_params(self):
        """Give this instance its own copy of every EpicsEnumParam type.

        EPICS enum choices are live IOC metadata, so each device must validate
        against the choices of its own IOC. Parameters are declared at class
        level, though, so the EpicsEnumParam (a ``oneof``) is shared by every
        instance. Without this clone, the per-instance ``set_choices()`` in
        _read_epics_enum_param_choices() would mutate that shared object and
        instances would clobber each other's choice lists.

        This relies on NICOS validating parameters against ``self.parameters``
        at runtime rather than a class-creation snapshot, so we override ``init``
        to install the per-instance dict before that validation runs. The
        ordering is guarded by
        test_instances_keep_independent_enum_choice_objects.
        """
        cloned = {}
        enums = []
        for name, info in self.parameters.items():
            if isinstance(info.type, EpicsEnumParam):
                info = copy(info)
                info.type = copy(info.type)
                enums.append(info.type)
            cloned[name] = info
        if enums:
            self.__dict__["parameters"] = cloned
            self._epics_enum_params = enums

    def _read_epics_enum_param_choices(self, mode):
        if mode == SIMULATION:
            return
        for enum in getattr(self, "_epics_enum_params", ()):
            enum.set_choices(self._epics.get_channel_value_choices(enum.channel))

    def _build_epics_channels(self):
        return self._epics_channels

    def _create_epics_component(self):
        return EpicsChannelComponent(
            self._epics_channels,
            resolve_channel_pv_names(
                self, self._epics_channels, self._default_pv_prefix_attr
            ),
            timeout=self.epicstimeout,
            use_pva=self.pva,
        )

    def doInit(self, mode):
        stale = set(self._epics_channels) - set(self._epics.pv_names_by_channel)
        if stale:
            raise ProgrammingError(
                self,
                f"EPICS channels {sorted(stale)} were added after the EPICS "
                "component was created; extend _build_epics_channels() instead",
            )
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._epics.subscribe_channels(
                self._dispatch_channel_update, self._on_connection_change
            )
        self._after_subscribe(mode)

    def doShutdown(self):
        epics = getattr(self, "_epics", None)
        if epics is not None:
            epics.shutdown()

    def _pvs_to_connect(self):
        if self._connect_channels:
            return [
                self._epics.pv_name_for(channel) for channel in self._connect_channels
            ]
        return self._epics.pvs_to_connect()

    def _after_subscribe(self, mode):
        pass

    def _dispatch_channel_update(self, update):
        # Exceptions in monitor callbacks otherwise remain in the wrapper's
        # callback thread, leaving stale values in the cache.
        try:
            self._on_channel_update(update)
        except Exception as err:
            message = (
                f"error handling update for EPICS channel {update.channel!r} "
                f"(PV {update.pv_name}): {err}"
            )
            self._cache.put(
                self._name,
                "status",
                (status.UNKNOWN, message),
                time.time(),
            )
            self.log.warning(
                "error handling update for EPICS channel %r (PV %s)",
                update.channel,
                update.pv_name,
                exc_info=True,
            )

    def _on_channel_update(self, update):
        ts = time.time()
        info = self._epics_channels.get(update.channel)
        if info and info.refresh_status_on_update:
            self._log_alarm_once(update.channel, update.severity, update.message)
        cache_key = self._epics.cache_key_for(update.channel)
        if cache_key is not None:
            self._cache.put(self._name, cache_key, update.value, ts)
        if info and info.limits_cache_key and update.limits:
            self._cache.put(self._name, info.limits_cache_key, update.limits, ts)
        if update.channel == self._primary_channel:
            self._cache.put(self._name, "unit", update.units, ts)
            self._cache.put(
                self._name, "value_status", (update.severity, update.message), ts
            )
        if info and info.refresh_status_on_update:
            self._refresh_status(ts)

    def _connection_change_affects_status(self, change):
        info = self._epics_channels.get(change.channel)
        return change.channel == self._primary_channel or (
            info is not None and info.affects_status
        )

    def _on_connection_change(self, change):
        if not self._connection_change_affects_status(change):
            return
        key = (change.channel, change.source_id)
        if change.is_connected:
            self.log.debug("%s connected!", change.pv_name)
            self._disconnected.discard(key)
        else:
            self.log.warning("%s disconnected!", change.pv_name)
            self._disconnected.add(key)
        self._refresh_status(time.time())

    def _refresh_status(self, ts):
        self._cache.put(self._name, "status", self._status_snapshot(maxage=None), ts)

    def _status_snapshot(self, maxage):
        # Track the set of disconnected channels rather than last-writer-wins on
        # "status", so one PV reconnecting cannot mask another still down.
        hardware = self._compute_status(maxage)
        if self._disconnected:
            return worst_status(hardware, LOST_CONNECTION_STATUS)
        return hardware

    def _read_channel_cached(self, channel, as_string=None, maxage=None):
        """Read a channel from the monitor-fed cache, else ask the IOC.

        For ``doRead<Param>`` of a ``volatile=True`` parameter use
        ``self._epics.get_channel_value()`` instead: volatile means the value
        must come from hardware, and a cached read just after a write can
        return the old value. ``as_string=None`` uses the channel table's
        ``as_string``.
        """
        return get_from_cache_or(
            self,
            self._epics.cache_key_for(channel),
            lambda: self._epics.get_channel_value(channel, as_string),
            maxage=maxage,
        )

    def _read_primary_alarm(self, maxage=0):
        def _read_alarm():
            try:
                return self._epics.get_channel_alarm(self._primary_channel)
            except (TimeoutError, CommunicationError):
                return LOST_CONNECTION_STATUS

        return get_from_cache_or(self, "value_status", _read_alarm, maxage=maxage)

    def _compute_status(self, maxage=0):
        return self._read_primary_alarm(maxage=maxage)

    def doRead(self, maxage=0):
        return self._read_channel_cached(self._primary_channel, maxage=maxage)

    def doStatus(self, maxage=0):
        return get_from_cache_or(
            self, "status", lambda: self._status_snapshot(maxage), maxage=maxage
        )

    def doReadUnit(self):
        return self._epics.get_channel_units(self._primary_channel)

    def _log_alarm_once(self, name, severity, message):
        if not hasattr(self, "_alarm_state"):
            self._alarm_state = {}
        if self._alarm_state.get(name) == (severity, message):
            return
        self._alarm_state[name] = (severity, message)
        if severity in (status.ERROR, status.UNKNOWN):
            self.log.error("%s (%s)", name, message)
        elif severity == status.WARN:
            self.log.warning("%s (%s)", name, message)


class EpicsReadWriteBase(EpicsDeviceBase):
    """EpicsDeviceBase for read/write devices: ``readpv`` + ``writepv``, with an
    optional ``targetpv`` readback.

    Subclasses must implement ``doStart(value)`` (write the target via
    ``self._startRaw(value)``).

    Subclasses may override ``_compute_status(maxage)``; the default reports
    BUSY after a start until the readback reaches the target, but only when
    ``wait_for_readback`` is set (leave it False for command-style PVs).
    """

    parameters = {
        "readpv": Param(
            "PV for reading device value", type=pvname, mandatory=True, userparam=False
        ),
        "writepv": Param(
            "PV for writing device target", type=pvname, mandatory=True, userparam=False
        ),
        "targetpv": Param(
            "Optional target readback PV.",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
        "wait_for_readback": Param(
            "Report BUSY after start until the readback equals the target. "
            "Leave False for command-style PVs; set True for true "
            "setpoint/readback devices so a move is not reported done while "
            "the readback still lags.",
            type=bool,
            default=False,
            mandatory=False,
            userparam=False,
        ),
    }

    def _build_epics_channels(self):
        epics_channels = dict(self._epics_channels)
        if self.targetpv and "write" in epics_channels:
            epics_channels["write"] = replace(epics_channels["write"], cache_key=None)
        return epics_channels

    def _startRaw(self, value):
        self._epics.put_channel_value("write", value)

    def _cached_raw_target(self, maxage=None):
        def _read():
            return self._epics.get_channel_value("target" if self.targetpv else "write")

        return get_from_cache_or(self, "target", _read, maxage=maxage)

    def doReadAbslimits(self):
        low, high = self._epics.get_channel_limits("write")
        if low == 0 and high == 0:
            return -1e308, 1e308
        return low, high

    def _readback_completion_candidates(self, maxage):
        target = self.target if self.wait_for_readback else None
        if target is None:
            return []
        try:
            at_target = self.isAtTarget(self.doRead(maxage), target)
        except PositionError:
            at_target = False
        except (TimeoutError, CommunicationError):
            return [LOST_CONNECTION_STATUS]
        if at_target:
            return []
        return [(status.BUSY, f"moving to {target}")]

    def _compute_status(self, maxage=0):
        return worst_status(
            self._read_primary_alarm(maxage=maxage),
            *self._readback_completion_candidates(maxage),
        )


class EpicsMappedChoiceSupport:
    """Mixin for devices whose mapping comes from IOC enum choices.

    Must come before the EPICS base class in the bases list: its ``doRead``,
    ``_readRaw`` and ``_on_channel_update`` cooperate with the base through
    ``super()``.
    """

    _mapping_channel = "read"

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))

    def _readRaw(self, maxage=0):
        value = get_from_cache_or(
            self,
            self._epics.cache_key_for("read"),
            lambda: self._epics.get_channel_value("read"),
            maxage=maxage,
        )
        return self._normalize_readback(value)

    def _mapReadValue(self, value):
        return value

    def _update_mapped_choices(self):
        channel = self._mapping_channel
        choices = self._epics.get_channel_value_choices(channel)
        if not choices:
            raise ConfigurationError(
                self,
                f"PV {self._epics.pv_name_for(channel)} has no value choices",
            )
        new_mapping = {choice: i for i, choice in enumerate(choices)}
        self._setROParam("mapping", new_mapping)
        self._inverse_mapping = {v: k for k, v in new_mapping.items()}

    def _mapTargetValue(self, target):
        if not self.relax_mapping and target not in self.mapping:
            positions = ", ".join(repr(pos) for pos in self.mapping)
            raise InvalidValueError(
                self,
                f"{target!r} is an invalid position for this device; valid "
                f"positions are {positions}",
            )
        return self.mapping.get(target, target)

    def _normalize_readback(self, value):
        if not hasattr(self, "_inverse_mapping"):
            self._inverse_mapping = {}
        if isinstance(value, str):
            if self._mapping_channel != "read" or value in self.mapping:
                return value
            self._update_mapped_choices()
            if value in self.mapping:
                return value
            raise PositionError(self, f"unknown unmapped position {value!r}")

        if value in self._inverse_mapping:
            return self._inverse_mapping[value]
        if self._mapping_channel == "read":
            self._update_mapped_choices()
            if value in self._inverse_mapping:
                return self._inverse_mapping[value]
        else:
            choices = self._epics.get_channel_value_choices("read")
            try:
                return choices[value]
            except (IndexError, TypeError):
                pass
        raise PositionError(self, f"unknown unmapped position {value!r}")

    def _on_channel_update(self, update):
        if self._epics.cache_key_for(update.channel) == "value":
            update = replace(update, value=self._normalize_readback(update.value))
        super()._on_channel_update(update)

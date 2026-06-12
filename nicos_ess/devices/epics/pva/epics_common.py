import os
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    ConfigurationError,
    InvalidValueError,
    Override,
    Param,
    PositionError,
    ProgrammingError,
    floatrange,
    none_or,
    pvname,
    status,
)
from nicos_ess.devices.mixins import HasNexusConfig

DEFAULT_EPICS_PROTOCOL = os.environ.get("DEFAULT_EPICS_PROTOCOL", "pva")


class EpicsChannelRole(Enum):
    """Whether a channel feeds the device value, its status, or both.

    STATUS/VALUE_AND_STATUS channels trigger a status recompute on updates.
    """

    VALUE = 1
    STATUS = 2
    VALUE_AND_STATUS = 3


@dataclass(frozen=True)
class EpicsChannelInfo:
    cache_key: str
    pv_suffix: str
    role: EpicsChannelRole
    as_string: bool = False
    pv_root_attr: Optional[str] = None
    pv_attr: Optional[str] = None
    subscribe: bool = True
    # Optional channels may resolve to no PV (e.g. a none_or(pvname)
    # parameter left unset); they are skipped by connect/subscribe.
    optional: bool = False


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


def create_wrapper(timeout, use_pva):
    if use_pva:
        from nicos.devices.epics.pva.p4p import P4pWrapper

        return P4pWrapper(timeout)
    else:
        from nicos.devices.epics.pva.caproto import CaprotoWrapper

        return CaprotoWrapper(timeout)


def get_from_cache_or(device, cache_key, func, maxage=None):
    # Deliberately gates on ``monitor`` and never writes back: the poller's
    # monitor callbacks fill the cache, every other session only reads it.
    if not getattr(device, "monitor", False) or not getattr(device, "_cache", None):
        return func()
    if maxage == 0:
        return func()

    mintime = None if maxage is None else time.time() - maxage
    result = device._cache.get(device._name, cache_key, Ellipsis, mintime=mintime)
    if result is not Ellipsis:
        return result
    return func()


def resolve_channel_pv_names(device, epics_channels, default_pv_root_attr=None):
    """Resolve each logical channel to a full PV name.

    A channel that resolves to no PV is a configuration error unless it is
    marked ``optional``; optional channels resolve to None.
    """
    names = {}
    for channel, info in epics_channels.items():
        if info.pv_attr:
            names[channel] = getattr(device, info.pv_attr, None)
        else:
            pv_root_attr = (
                default_pv_root_attr if info.pv_root_attr is None else info.pv_root_attr
            )
            root = getattr(device, pv_root_attr, None) if pv_root_attr else None
            names[channel] = None if root is None else f"{root}{info.pv_suffix}"
        if names[channel] is None and not info.optional:
            raise ConfigurationError(
                device,
                f"EPICS channel {channel!r} resolved to no PV; set its "
                "pv_attr/pv_root_attr or mark it optional=True",
            )
    return names


def status_from_candidates(base_alarm, candidates):
    """Combine an EPICS alarm with extra status candidates; highest wins.

    Note BUSY outranks WARN in NICOS, deliberately: reporting WARN while
    moving would complete waits prematurely.
    """
    severity, msg = base_alarm
    options = list(candidates)
    if severity != status.OK:
        options.append((severity, msg))
    if options:
        return max(options, key=lambda candidate: candidate[0])
    return status.OK, msg


class MappedChoiceSource(str, Enum):
    READ = "read"
    WRITE = "write"


def _update_mapped_choices(
    mapped_device, source=MappedChoiceSource.READ, *, publish=True
):
    if source == MappedChoiceSource.WRITE:
        selected_channel = "write"
        selected_pv = mapped_device.writepv
        mapping_attr = "_write_mapping"
        inverse_attr = "_write_inverse_mapping"
    else:
        selected_channel = "read"
        selected_pv = mapped_device.readpv
        mapping_attr = "_read_mapping"
        inverse_attr = "_read_inverse_mapping"

    choices = mapped_device._epics.get_channel_value_choices(selected_channel)
    if not choices:
        raise ConfigurationError(
            mapped_device, f"PV {selected_pv} has no value choices"
        )

    new_mapping = {choice: i for i, choice in enumerate(choices)}
    setattr(mapped_device, mapping_attr, new_mapping)
    setattr(mapped_device, inverse_attr, {v: k for k, v in new_mapping.items()})
    if not publish:
        return
    mapped_device._setROParam("mapping", new_mapping)
    mapped_device._inverse_mapping = {v: k for k, v in new_mapping.items()}


class EpicsChannelComponent:
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
        self.subscriptions = []

    def pv_name_for(self, channel):
        return self.pv_names_by_channel.get(channel)

    def cache_key_for(self, channel):
        info = self.epics_channels.get(channel)
        if info is not None and info.cache_key:
            return info.cache_key
        return channel

    def pvs_to_connect(self):
        names = []
        for channel in self.epics_channels:
            pv_name = self.pv_name_for(channel)
            if pv_name and pv_name not in names:
                names.append(pv_name)
        return names

    def connect(self, pvs_to_connect=None, simulation=False):
        self.subscriptions.clear()
        if not self._wrapper_injected:
            self.wrapper = create_wrapper(self.timeout, self.use_pva)
        if simulation:
            return
        if pvs_to_connect is None:
            pvs_to_connect = self.pvs_to_connect()
        for pv in pvs_to_connect:
            self.wrapper.connect_pv(pv)

    def subscribe_channels(self, change_callback, connection_callback=None):
        for channel in self.subscribed_channels():
            self.subscribe_channel(channel, change_callback, connection_callback)

    def subscribed_channels(self):
        return [
            channel for channel, info in self.epics_channels.items() if info.subscribe
        ]

    def subscribe_channel(
        self,
        channel,
        change_callback,
        connection_callback=None,
        subscription_param=None,
        as_string=None,
    ):
        pv = self.pv_name_for(channel)
        if not pv:
            return None
        if as_string is None:
            as_string = self.epics_channels[channel].as_string
        sub = self.wrapper.subscribe(
            pv,
            channel if subscription_param is None else subscription_param,
            change_callback,
            connection_callback,
            as_string=as_string,
        )
        self.subscriptions.append(sub)
        return sub

    def close_subscription(self, subscription):
        if subscription is None:
            return
        if self.wrapper is not None:
            self.wrapper.close_subscription(subscription)
        with suppress(ValueError):
            self.subscriptions.remove(subscription)

    def shutdown(self):
        if self.wrapper is None:
            return
        for sub in list(self.subscriptions):
            self.close_subscription(sub)

    def get_channel_value(self, channel, as_string=None):
        if as_string is None:
            info = self.epics_channels.get(channel)
            as_string = info.as_string if info is not None else False
        return self.wrapper.get_pv_value(self.pv_name_for(channel), as_string)

    def get_pv_value(self, pv_name, as_string=False):
        return self.wrapper.get_pv_value(pv_name, as_string)

    def get_channel_alarm(self, channel):
        return self.wrapper.get_alarm_status(self.pv_name_for(channel))

    def get_channel_limits(self, channel, default_low=-1e308, default_high=1e308):
        return self.wrapper.get_limits(
            self.pv_name_for(channel), default_low, default_high
        )

    def get_channel_units(self, channel, default=""):
        return self.wrapper.get_units(self.pv_name_for(channel), default)

    def get_channel_value_choices(self, channel):
        return self.wrapper.get_value_choices(self.pv_name_for(channel))

    def put_channel_value(self, channel, value):
        self.wrapper.put_pv_value(self.pv_name_for(channel), value)

    def wait_for(self, channel, expected, timeout=5.0, precision=None):
        """Block until *channel* reaches *expected* within *precision*."""
        event = threading.Event()

        def matches(value):
            if precision is not None and isinstance(value, (int, float)):
                return abs(value - expected) <= precision
            return value == expected

        def callback(pv_name, channel, value, units, limits, severity, message, **kw):
            if matches(value):
                event.set()

        sub = self.subscribe_channel(channel, callback)
        try:
            if matches(self.get_channel_value(channel)):
                return
            if not event.wait(timeout):
                raise TimeoutError(
                    f"timeout waiting for {channel} to become {expected}"
                )
        finally:
            self.close_subscription(sub)


class EpicsDeviceBase(EpicsParameters):
    """NICOS glue for an ``EpicsChannelComponent``.

    Owns the lifecycle (component creation/connect at preinit, poller-side
    subscription at init, teardown at shutdown) and the cache/status policy:
    monitor callbacks fill the device cache, reads prefer the cache, status
    is recomputed on STATUS/VALUE_AND_STATUS channel changes.

    Declare the channel table as a class-level ``_epics_channels`` dict or by
    overriding ``_build_epics_channels()`` (required when channels depend on
    parameters). The table must be complete before preinit finishes -- the
    component resolves channel->PV names exactly once.

    ``_compute_status`` must read channels/alarms only; calling
    ``self.doStatus()`` from it would recurse.
    """

    _primary_channel = "read"
    _epics_channels = None
    _default_pv_root_attr = None

    def doPreinit(self, mode):
        epics_channels = self._build_epics_channels()
        if epics_channels is None:
            epics_channels = self._epics_channels
        if not epics_channels:
            raise ProgrammingError(
                self,
                "define _epics_channels (class attribute) or override "
                "_build_epics_channels()",
            )
        self._epics_channels = dict(epics_channels)
        self._epics = self._create_epics_component()
        self._epics.connect(self._pvs_to_connect(), simulation=mode == SIMULATION)

    def _build_epics_channels(self):
        return None

    def _create_epics_component(self):
        return EpicsChannelComponent(
            self._epics_channels,
            resolve_channel_pv_names(
                self, self._epics_channels, self._default_pv_root_attr
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
                self._value_change_callback, self._connection_change_callback
            )
        self._after_subscribe(mode)

    def doShutdown(self):
        epics = getattr(self, "_epics", None)
        if epics is not None:
            epics.shutdown()

    def _pvs_to_connect(self):
        return self._epics.pvs_to_connect()

    def _after_subscribe(self, mode):
        pass

    def _value_change_callback(
        self, pv_name, channel, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        self._cache.put(self._name, self._epics.cache_key_for(channel), value, ts)
        if pv_name == self._epics.pv_name_for(self._primary_channel):
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "value_status", (severity, message), ts)
        info = self._epics_channels.get(channel)
        if info and info.role in (
            EpicsChannelRole.STATUS,
            EpicsChannelRole.VALUE_AND_STATUS,
        ):
            self._refresh_status(ts)

    def _connection_change_callback(self, pv_name, channel, is_connected, **kwargs):
        if pv_name != self._epics.pv_name_for(self._primary_channel):
            return
        if is_connected:
            self.log.debug("%s connected!", pv_name)
        else:
            self.log.warning("%s disconnected!", pv_name)
            self._cache.put(
                self._name,
                "status",
                (status.UNKNOWN, "lost connection to EPICS"),
                time.time(),
            )

    def _refresh_status(self, ts):
        self._cache.put(self._name, "status", self._compute_status(maxage=None), ts)

    def _read_channel_cached(self, channel, as_string=None, maxage=None):
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
            except TimeoutError:
                return status.UNKNOWN, "lost connection to EPICS"

        return get_from_cache_or(self, "value_status", _read_alarm, maxage=maxage)

    def _compute_status(self, maxage=0):
        return self._read_primary_alarm(maxage=maxage)

    def doStatus(self, maxage=0):
        return get_from_cache_or(
            self, "status", lambda: self._compute_status(maxage), maxage=maxage
        )

    def doReadUnit(self):
        return self._epics.get_channel_units(self._primary_channel)


class EpicsReadWriteBase(EpicsDeviceBase):
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
    }

    def _value_change_callback(
        self, pv_name, channel, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        # Separate ifs: read and write may subscribe to the same PV.
        if channel == "read":
            self._cache.put(self._name, "value", value, ts)
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "value_status", (severity, message), ts)
        if channel == "write":
            if limits:
                self._cache.put(self._name, "abslimits", limits, ts)
            if not self.target:
                self._cache.put(self._name, "target", value, ts)
        if channel == "target":
            self._cache.put(self._name, "target", value, ts)
        info = self._epics_channels.get(channel)
        if info and info.role in (
            EpicsChannelRole.STATUS,
            EpicsChannelRole.VALUE_AND_STATUS,
        ):
            self._refresh_status(ts)

    def _cached_raw_target(self, maxage=None):
        def _read():
            return self._epics.get_channel_value("target" if self.targetpv else "write")

        return get_from_cache_or(self, "target", _read, maxage=maxage)

    def doReadAbslimits(self):
        low, high = self._epics.get_channel_limits("write")
        if low == 0 and high == 0:
            return -1e308, 1e308
        return low, high


class EpicsMappedChoiceSupport:
    """Choice validation + mapping refresh for enum (mbbi/bi) PVs."""

    _publish_read_choices = True

    def _read_choice_mapping(self):
        return getattr(self, "_read_mapping", self.mapping)

    def _write_choice_mapping(self):
        return getattr(self, "_write_mapping", self.mapping)

    def _validate_mapped_choice(self, value):
        if value not in self._read_choice_mapping():
            _update_mapped_choices(self, publish=self._publish_read_choices)
        if value not in self._read_choice_mapping():
            raise PositionError(self, f"unknown unmapped position {value!r}")
        return value

    def _mapTargetValue(self, target):
        mapping = self._write_choice_mapping()
        if not self.relax_mapping and target not in mapping:
            positions = ", ".join(repr(pos) for pos in mapping)
            raise InvalidValueError(
                self,
                "%r is an invalid position for this device; valid positions "
                "are %s" % (target, positions),
            )
        return mapping.get(target, target)

    def _read_mapped_choice(self, maxage=0):
        def _read_epics_choice():
            try:
                return self._epics.get_channel_value("read")
            except (IndexError, KeyError):
                _update_mapped_choices(self, publish=self._publish_read_choices)
                try:
                    return self._epics.get_channel_value("read")
                except (IndexError, KeyError):
                    return self._epics.get_channel_value("read", as_string=False)

        value = get_from_cache_or(
            self,
            self._epics_channels["read"].cache_key,
            _read_epics_choice,
            maxage=maxage,
        )
        return self._validate_mapped_choice(value)

    def _value_change_callback(
        self, pv_name, channel, value, units, limits, severity, message, **kwargs
    ):
        if self._epics.cache_key_for(channel) == "value":
            value = self._validate_mapped_choice(value)
        super()._value_change_callback(
            pv_name, channel, value, units, limits, severity, message, **kwargs
        )

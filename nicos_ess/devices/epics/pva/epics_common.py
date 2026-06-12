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


class RecordType(Enum):
    """Whether a field feeds the device value, its status, or both.

    STATUS/BOTH fields trigger a status recompute when their monitor fires.
    """

    VALUE = 1
    STATUS = 2
    BOTH = 3


@dataclass(frozen=True)
class RecordInfo:
    cache_key: str
    pv_suffix: str
    record_type: RecordType
    as_string: bool = False
    root_attr: Optional[str] = None
    monitor: bool = True


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


def resolve_pv_names(device, record_fields, root_attr=None):
    """Resolve each field to a full PV name."""
    names = {}
    for field, info in record_fields.items():
        field_root_attr = root_attr if info.root_attr is None else info.root_attr
        if field_root_attr:
            root = getattr(device, field_root_attr, None)
            names[field] = None if root is None else f"{root}{info.pv_suffix}"
        else:
            names[field] = getattr(device, field, None)
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


class PvReadOrWrite(str, Enum):
    readpv = "readpv"
    writepv = "writepv"


def _update_mapped_choices(mapped_device, pv=PvReadOrWrite.readpv, *, publish=True):
    if pv == PvReadOrWrite.writepv:
        selected_field = "writepv"
        selected_pv = mapped_device.writepv
        mapping_attr = "_write_mapping"
        inverse_attr = "_write_inverse_mapping"
    else:
        selected_field = "readpv"
        selected_pv = mapped_device.readpv
        mapping_attr = "_read_mapping"
        inverse_attr = "_read_inverse_mapping"

    choices = mapped_device._epics.get_value_choices(selected_field)
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


class EpicsRecordComponent:
    def __init__(
        self,
        record_fields,
        pv_names,
        *,
        timeout=3.0,
        use_pva=True,
        wrapper=None,
    ):
        self.record_fields = record_fields
        self.pv_names = pv_names
        self.timeout = timeout
        self.use_pva = use_pva
        self.wrapper = wrapper
        self._wrapper_injected = wrapper is not None
        self.subscriptions = []

    def pv_name(self, field):
        return self.pv_names.get(field)

    def resolve_cache_key(self, field):
        info = self.record_fields.get(field)
        if info is not None and info.cache_key:
            return info.cache_key
        return field

    def pvs_to_connect(self):
        names = []
        for field in self.record_fields:
            name = self.pv_name(field)
            if name and name not in names:
                names.append(name)
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

    def subscribe_fields(self, change_callback, connection_callback=None):
        for field in self.monitor_fields():
            self.subscribe_field(field, change_callback, connection_callback)

    def monitor_fields(self):
        return [field for field, info in self.record_fields.items() if info.monitor]

    def subscribe_field(
        self,
        field,
        change_callback,
        connection_callback=None,
        param=None,
        as_string=None,
    ):
        pv = self.pv_name(field)
        if not pv:
            return None
        if as_string is None:
            as_string = self.record_fields[field].as_string
        sub = self.wrapper.subscribe(
            pv,
            field if param is None else param,
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

    def get_pv(self, field, as_string=None):
        if as_string is None:
            info = self.record_fields.get(field)
            as_string = info.as_string if info is not None else False
        return self.wrapper.get_pv_value(self.pv_name(field), as_string)

    def get_pv_value(self, pv, as_string=False):
        return self.wrapper.get_pv_value(pv, as_string)

    def get_alarm_status(self, field):
        return self.wrapper.get_alarm_status(self.pv_name(field))

    def get_limits(self, field, default_low=-1e308, default_high=1e308):
        return self.wrapper.get_limits(self.pv_name(field), default_low, default_high)

    def get_units(self, field, default=""):
        return self.wrapper.get_units(self.pv_name(field), default)

    def get_value_choices(self, field):
        return self.wrapper.get_value_choices(self.pv_name(field))

    def put_pv(self, field, value):
        self.wrapper.put_pv_value(self.pv_name(field), value)

    def wait_for(self, field, expected, timeout=5.0, precision=None):
        """Block until *field* reaches *expected* (within *precision*)."""
        event = threading.Event()

        def matches(value):
            if precision is not None and isinstance(value, (int, float)):
                return abs(value - expected) <= precision
            return value == expected

        def callback(name, param, value, units, limits, severity, message, **kw):
            if matches(value):
                event.set()

        sub = self.subscribe_field(field, callback)
        try:
            if matches(self.get_pv(field)):
                return
            if not event.wait(timeout):
                raise TimeoutError(f"timeout waiting for {field} to become {expected}")
        finally:
            self.close_subscription(sub)


class EpicsDeviceBase(EpicsParameters):
    """NICOS glue for an ``EpicsRecordComponent``.

    Owns the lifecycle (component creation/connect at preinit, poller-side
    subscription at init, teardown at shutdown) and the cache/status policy:
    monitor callbacks fill the device cache, reads prefer the cache, status
    is recomputed on STATUS/BOTH field changes.

    Declare the field table as a class-level ``_record_fields`` dict or by
    overriding ``_build_record_fields()`` (required when fields depend on
    parameters). The table must be complete before preinit finishes -- the
    component resolves field->PV names exactly once.

    ``_compute_status`` must read fields/alarms only; calling
    ``self.doStatus()`` from it would recurse.
    """

    _primary_field = "readpv"
    _record_fields = None
    _default_root_attr = None

    def doPreinit(self, mode):
        record_fields = self._build_record_fields()
        if record_fields is None:
            record_fields = self._record_fields
        if not record_fields:
            raise ProgrammingError(
                self,
                "define _record_fields (class attribute) or override "
                "_build_record_fields()",
            )
        self._record_fields = dict(record_fields)
        self._epics = self._create_epics_component()
        self._epics.connect(self._pvs_to_connect(), simulation=mode == SIMULATION)

    def _build_record_fields(self):
        return None

    def _create_epics_component(self):
        return EpicsRecordComponent(
            self._record_fields,
            resolve_pv_names(self, self._record_fields, self._default_root_attr),
            timeout=self.epicstimeout,
            use_pva=self.pva,
        )

    def doInit(self, mode):
        stale = set(self._record_fields) - set(self._epics.pv_names)
        if stale:
            raise ProgrammingError(
                self,
                f"record fields {sorted(stale)} were added after the EPICS "
                "component was created; extend _build_record_fields() instead",
            )
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._epics.subscribe_fields(
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
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        self._cache.put(self._name, self._epics.resolve_cache_key(param), value, ts)
        if name == self._epics.pv_name(self._primary_field):
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "value_status", (severity, message), ts)
        info = self._record_fields.get(param)
        if info and info.record_type in (RecordType.STATUS, RecordType.BOTH):
            self._refresh_status(ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if name != self._epics.pv_name(self._primary_field):
            return
        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.UNKNOWN, "lost connection to EPICS"),
                time.time(),
            )

    def _refresh_status(self, ts):
        self._cache.put(self._name, "status", self._compute_status(maxage=None), ts)

    def _read_cached(self, field, as_string=None, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.resolve_cache_key(field),
            lambda: self._epics.get_pv(field, as_string),
            maxage=maxage,
        )

    def _read_primary_alarm(self, maxage=0):
        def _read_alarm():
            try:
                return self._epics.get_alarm_status(self._primary_field)
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
        return self._epics.get_units(self._primary_field)


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
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        # Separate ifs: readpv and writepv may be the same PV.
        if name == self.readpv:
            self._cache.put(self._name, "value", value, ts)
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "value_status", (severity, message), ts)
        if name == self.writepv:
            if limits:
                self._cache.put(self._name, "abslimits", limits, ts)
            if not self.target:
                self._cache.put(self._name, "target", value, ts)
        if name == self.targetpv:
            self._cache.put(self._name, "target", value, ts)
        info = self._record_fields.get(param)
        if info and info.record_type in (RecordType.STATUS, RecordType.BOTH):
            self._refresh_status(ts)

    def _cached_raw_target(self, maxage=None):
        def _read():
            return self._epics.get_pv("targetpv" if self.targetpv else "writepv")

        return get_from_cache_or(self, "target", _read, maxage=maxage)

    def doReadAbslimits(self):
        low, high = self._epics.get_limits("writepv")
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
                return self._epics.get_pv("readpv")
            except (IndexError, KeyError):
                _update_mapped_choices(self, publish=self._publish_read_choices)
                try:
                    return self._epics.get_pv("readpv")
                except (IndexError, KeyError):
                    return self._epics.get_pv("readpv", as_string=False)

        value = get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            _read_epics_choice,
            maxage=maxage,
        )
        return self._validate_mapped_choice(value)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if self._epics.resolve_cache_key(param) == "value":
            value = self._validate_mapped_choice(value)
        super()._value_change_callback(
            name, param, value, units, limits, severity, message, **kwargs
        )

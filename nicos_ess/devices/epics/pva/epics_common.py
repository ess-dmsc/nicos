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
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************

"""Shared EPICS PVA parameters, record metadata, wrappers, and base classes."""

import os
import time
from collections import namedtuple
from enum import Enum

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    ConfigurationError,
    Override,
    Param,
    PositionError,
    ProgrammingError,
    dictof,
    floatrange,
    none_or,
    pvname,
    status,
)
from nicos_ess.devices.mixins import HasNexusConfig

DEFAULT_EPICS_PROTOCOL = os.environ.get("DEFAULT_EPICS_PROTOCOL", "pva")


RecordInfo = namedtuple(
    "RecordInfo",
    ("cache_key", "pv_suffix", "record_type", "as_string"),
    defaults=(False,),
)


class RecordType(Enum):
    VALUE = 1
    STATUS = 2
    BOTH = 3


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
    if not getattr(device, "monitor", False) or not getattr(device, "_cache", None):
        return func()
    if maxage == 0:
        return func()

    mintime = None if maxage is None else time.time() - maxage
    result = device._cache.get(device._name, cache_key, Ellipsis, mintime=mintime)
    if result is not Ellipsis:
        return result
    return func()


class PvReadOrWrite(str, Enum):
    readpv = "readpv"
    writepv = "writepv"


def _update_mapped_choices(mapped_device, pv=PvReadOrWrite.readpv):
    if pv == PvReadOrWrite.writepv:
        selected_pv = mapped_device.writepv
    else:
        selected_pv = mapped_device.readpv
    choices = mapped_device._epics_wrapper.get_value_choices(selected_pv)
    if not choices:
        raise ConfigurationError(
            mapped_device, f"PV {selected_pv} has no value choices"
        )

    new_mapping = {choice: i for i, choice in enumerate(choices)}
    mapped_device._setROParam("mapping", new_mapping)
    mapped_device._inverse_mapping = {v: k for k, v in new_mapping.items()}


class EpicsDeviceBase(EpicsParameters):
    """Shared EPICS monitor lifecycle for the ESS PVA devices."""

    _primary_field = "readpv"
    _record_fields = None
    _default_root_attr = None

    def _pv_name(self, field):
        info = self._record_fields.get(field)
        if info is not None and info.pv_suffix and self._default_root_attr:
            root = getattr(self, self._default_root_attr, None)
            return None if root is None else f"{root}{info.pv_suffix}"
        return getattr(self, field, None)

    def _pvs_to_connect(self):
        names = []
        for field in self._record_fields:
            name = self._pv_name(field)
            if name and name not in names:
                names.append(name)
        return names

    def doPreinit(self, mode):
        if not self._record_fields:
            raise ProgrammingError(
                self,
                "_record_fields must be defined (class- or instance-level) "
                "before calling EpicsDeviceBase.doPreinit()",
            )
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        if mode == SIMULATION:
            return
        for pv in self._pvs_to_connect():
            self._epics_wrapper.connect_pv(pv)

    def doInit(self, mode):
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            self._subscribe_fields()
        self._after_subscribe(mode)

    def doShutdown(self):
        for sub in self._epics_subscriptions:
            self._epics_wrapper.close_subscription(sub)
        self._epics_subscriptions = []

    def _subscribe_fields(self):
        for field in self._record_fields:
            pv = self._pv_name(field)
            if not pv:
                continue
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    pv,
                    field,
                    self._value_change_callback,
                    self._connection_change_callback,
                    as_string=self._record_fields[field].as_string,
                )
            )

    def _after_subscribe(self, mode):
        pass

    def _get_cached_pv_or_ask(self, field, as_string=None, maxage=None):
        return get_from_cache_or(
            self,
            self._resolve_cache_key(field),
            lambda: self._get_pv(field, as_string),
            maxage=maxage,
        )

    def _get_pv(self, field, as_string=None):
        if as_string is None:
            info = self._record_fields.get(field)
            as_string = info.as_string if info is not None else False
        return self._epics_wrapper.get_pv_value(self._pv_name(field), as_string)

    def _put_pv(self, field, value):
        self._epics_wrapper.put_pv_value(self._pv_name(field), value)

    def _resolve_cache_key(self, param):
        info = self._record_fields.get(param)
        if info is not None and info.cache_key:
            return info.cache_key
        return param

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        self._default_value_change(
            name, param, value, units, limits, severity, message, **kwargs
        )

    def _default_value_change(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        self._cache.put(
            self._name,
            self._resolve_cache_key(param),
            value,
            ts,
        )
        if name == self._pv_name(self._primary_field):
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "value_status", (severity, message), ts)
        info = self._record_fields.get(param)
        if info and info.record_type in (RecordType.STATUS, RecordType.BOTH):
            self._refresh_cached_status(ts)

    def _refresh_cached_status(self, ts):
        self._cache.put(self._name, "status", self._compute_status(maxage=None), ts)

    def doStatus(self, maxage=0):
        return get_from_cache_or(
            self, "status", lambda: self._compute_status(maxage), maxage=maxage
        )

    def doReadUnit(self):
        return self._epics_wrapper.get_units(self._pv_name(self._primary_field))

    def _read_primary_alarm(self, maxage=0):
        def _read_alarm():
            try:
                return self._epics_wrapper.get_alarm_status(
                    self._pv_name(self._primary_field)
                )
            except TimeoutError:
                return status.ERROR, "timeout reading status"

        return get_from_cache_or(self, "value_status", _read_alarm, maxage=maxage)

    def _compute_status(self, maxage=0):
        return self._read_primary_alarm(maxage=maxage)

    def _status_from_candidates(self, base_alarm, candidates):
        severity, msg = base_alarm
        options = list(candidates)
        if severity != status.OK:
            options.append((severity, msg))
        if options:
            return max(options, key=lambda candidate: candidate[0])
        return status.OK, msg

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if name != self._pv_name(self._primary_field):
            return
        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.ERROR, "communication failure"),
                time.time(),
            )


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
            self._refresh_cached_status(ts)

    def _cached_raw_target(self, maxage=None):
        def _read():
            return self._get_pv("targetpv" if self.targetpv else "writepv")

        return get_from_cache_or(self, "target", _read, maxage=maxage)

    def doReadAbslimits(self):
        low, high = self._epics_wrapper.get_limits(self.writepv)
        if low == 0 and high == 0:
            return -1e308, 1e308
        return low, high


class EpicsMultiSourceBase(EpicsDeviceBase):
    """Base for devices exposing one field table across multiple PV prefixes."""

    parameters = {
        "sources": Param(
            "Mapping of source id to PV prefix.",
            type=dictof(str, pvname),
            mandatory=True,
            userparam=False,
        ),
    }

    def _source_pv(self, source_id, field):
        return f"{self.sources[source_id]}{self._record_fields[field].pv_suffix}"

    def _source_key(self, source_id, field):
        info = self._record_fields[field]
        return f"{source_id}/{info.cache_key or field}"

    def _pvs_to_connect(self):
        return [
            self._source_pv(source_id, field)
            for source_id in self.sources
            for field in self._record_fields
        ]

    def _subscribe_fields(self):
        for source_id in self.sources:
            for field, info in self._record_fields.items():
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self._source_pv(source_id, field),
                        (source_id, field),
                        self._value_change_callback,
                        self._connection_change_callback,
                        as_string=info.as_string,
                    )
                )

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        source_id, field = param
        ts = time.time()
        self._cache.put(self._name, self._source_key(source_id, field), value, ts)
        if self._record_fields[field].record_type in (
            RecordType.STATUS,
            RecordType.BOTH,
        ):
            self._refresh_cached_status(ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)

    def _get_source(self, source_id, field, maxage=None):
        info = self._record_fields[field]
        return get_from_cache_or(
            self,
            self._source_key(source_id, field),
            lambda: self._epics_wrapper.get_pv_value(
                self._source_pv(source_id, field), info.as_string
            ),
            maxage=maxage,
        )

    def _put_source(self, source_id, field, value):
        self._epics_wrapper.put_pv_value(self._source_pv(source_id, field), value)

    def doReadUnit(self):
        return self._config.get("unit", "") or self._params.get("unit", "")

    def _compute_status(self, maxage=0):
        return status.OK, ""


class EpicsMappedChoiceSupport:
    """Choice validation + mapping refresh for enum (mbbi/bi) PVs."""

    def _validate_mapped_choice(self, value):
        if value not in self.mapping:
            _update_mapped_choices(self)
        if value not in self.mapping:
            raise PositionError(self, f"unknown unmapped position {value!r}")
        return value

    def _read_mapped_choice(self, maxage=0):
        def _read_epics_choice():
            try:
                return self._get_pv("readpv")
            except (IndexError, KeyError):
                _update_mapped_choices(self)
                try:
                    return self._get_pv("readpv")
                except (IndexError, KeyError):
                    return self._get_pv("readpv", as_string=False)

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
        if self._resolve_cache_key(param) == "value":
            value = self._validate_mapped_choice(value)
        super()._value_change_callback(
            name, param, value, units, limits, severity, message, **kwargs
        )

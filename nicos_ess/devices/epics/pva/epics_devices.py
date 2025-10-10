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

"""
This module contains some classes for NICOS - EPICS integration.
"""

import os
import time
from collections import namedtuple
from enum import Enum

import numpy

from nicos import session
from nicos.core import (
    POLLER,
    HasLimits,
    HasPrecision,
    Moveable,
    Override,
    Param,
    Readable,
    anytype,
    dictof,
    floatrange,
    listof,
    none_or,
    pvname,
    status,
    tupleof,
)
from nicos.devices.abstract import MappedMoveable, MappedReadable

DEFAULT_EPICS_PROTOCOL = os.environ.get("DEFAULT_EPICS_PROTOCOL", "ca")


RecordInfo = namedtuple("RecordInfo", ("cache_key", "pv_suffix", "record_type"))


class RecordType(Enum):
    VALUE = 1
    STATUS = 2
    BOTH = 3


class EpicsParameters:
    parameters = {
        "epicstimeout": Param(
            "Timeout for getting EPICS PVs",
            type=none_or(floatrange(0.1, 60)),
            userparam=False,
            mandatory=False,
            default=3.0,
        ),
        "monitor": Param("Use a PV monitor", type=bool, default=True),
        "pva": Param("Use pva", type=bool, default=True),
        "to_forward": Param(
            "Associated PVs that should be forward by the forwarder",
            type=listof(tupleof(str, str, str, str, int)),
            default=[],
            userparam=False,
        ),
        "nexus_config": Param(
            "Nexus structure group definition",
            type=listof(dictof(str, anytype)),
            default=[],
            userparam=False,
        ),
    }
    parameter_overrides = {
        "pollinterval": Override(default=None),
        "maxage": Override(default=None),
    }


def create_wrapper(timeout, use_pva):
    if use_pva:
        from nicos.devices.epics.pva.p4p import P4pWrapper

        return P4pWrapper(timeout)
    else:
        from nicos.devices.epics.pva.caproto import CaprotoWrapper

        return CaprotoWrapper(timeout)


def get_from_cache_or(device, cache_key, func):
    if device.monitor:
        result = device._cache.get(device._name, cache_key)
        if result is not None:
            return result
    return func()


class EpicsReadable(EpicsParameters, Readable):
    parameters = {
        "readpv": Param(
            "PV for reading device value", type=pvname, mandatory=True, userparam=False
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _record_fields = {
        "readpv": RecordInfo("value", "", RecordType.BOTH),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv),
        )

    def doReadUnit(self):
        return get_from_cache_or(
            self, "unit", lambda: self._epics_wrapper.get_units(self.readpv)
        )

    def doStatus(self, maxage=0):
        def _func():
            try:
                severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
            except TimeoutError:
                return status.ERROR, "timeout reading status"
            if severity in [status.ERROR, status.WARN]:
                return severity, msg
            return status.OK, msg

        return get_from_cache_or(self, "status", _func)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        self._cache.put(self._name, param, value, time_stamp)
        self._cache.put(self._name, "unit", units, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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


class EpicsStringReadable(EpicsReadable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv, as_string=True),
        )

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if isinstance(value, numpy.ndarray):
            # It is a char waveform
            value = "".join(chr(x) for x in value)
        EpicsReadable._value_change_callback(
            self, name, param, value, units, limits, severity, message, **kwargs
        )


class EpicsAnalogMoveable(EpicsParameters, HasPrecision, HasLimits, Moveable):
    """
    Handles EPICS devices which can set and read a floating value.
    """

    valuetype = float

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

    parameter_overrides = {
        "abslimits": Override(mandatory=False, volatile=True),
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _record_fields = {
        "readpv": RecordInfo("value", "", RecordType.BOTH),
        "writepv": RecordInfo("target", "", RecordType.VALUE),
        "targetpv": RecordInfo("target", "", RecordType.VALUE),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        if self.targetpv:
            self._epics_wrapper.connect_pv(self.targetpv)

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            if self.targetpv:
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self.targetpv,
                        self._record_fields["targetpv"].cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv),
        )

    def doReadUnit(self):
        return get_from_cache_or(
            self, "unit", lambda: self._epics_wrapper.get_units(self.readpv)
        )

    def _do_status(self):
        try:
            severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if severity in [status.ERROR, status.WARN]:
            return severity, msg

        at_target = HasPrecision.doIsAtTarget(self, self.doRead(), self.doReadTarget())
        if not at_target:
            return status.BUSY, f"moving to {self.target}"
        return status.OK, msg

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def doReadAbslimits(self):
        low, high = get_from_cache_or(
            self, "abslimits", lambda: self._epics_wrapper.get_limits(self.writepv)
        )
        if low == 0 and high == 0:
            # No limits set on PV, so use defaults
            return -1e308, 1e308
        return low, high

    def doReadTarget(self, maxage=0):
        def _func():
            if self.targetpv:
                return self._epics_wrapper.get_pv_value(self.targetpv)
            else:
                return self._epics_wrapper.get_pv_value(self.writepv)

        return get_from_cache_or(self, "target", _func)

    def doStart(self, value):
        self._epics_wrapper.put_pv_value(self.writepv, value)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if name == self.readpv:
            self._cache.put(self._name, param, value, time_stamp)
            self._cache.put(self._name, "unit", units, time_stamp)
        if name == self.writepv and limits:
            self._cache.put(self._name, "abslimits", limits, time_stamp)
        if name == self.writepv and not self.target:
            self._cache.put(self._name, param, value, time_stamp)
        if name == self.targetpv:
            self._cache.put(self._name, param, value, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if param == "value":
            self._cache.put(self._name, "value_status", (severity, message), time_stamp)
        else:
            self._cache.put(self._name, param, value, time_stamp)
        self._cache.put(self._name, "status", self._do_status(), time_stamp)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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


class EpicsDigitalMoveable(EpicsAnalogMoveable):
    """
    Handles EPICS devices which can set and read an integer value.
    """

    valuetype = int

    parameter_overrides = {
        "fmtstr": Override(default="%d"),
    }


class EpicsStringMoveable(EpicsParameters, Moveable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

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

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _record_fields = {
        "readpv": RecordInfo("value", "", RecordType.BOTH),
        "writepv": RecordInfo("target", "", RecordType.VALUE),
        "targetpv": RecordInfo("target", "", RecordType.VALUE),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        if self.targetpv:
            self._epics_wrapper.connect_pv(self.targetpv)

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            if self.targetpv:
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self.targetpv,
                        self._record_fields["targetpv"].cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv, as_string=True),
        )

    def doStatus(self, maxage=0):
        def _func():
            try:
                return self._epics_wrapper.get_alarm_status(self.readpv)
            except TimeoutError:
                return status.ERROR, "timeout reading status"

        return get_from_cache_or(self, "status", _func)

    def doStart(self, value):
        self._epics_wrapper.put_pv_value(self.writepv, value)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if name == self.readpv:
            self._cache.put(self._name, param, value, time_stamp)
            self._cache.put(self._name, "unit", units, time_stamp)
        if name == self.writepv and not self.target:
            self._cache.put(self._name, param, value, time_stamp)
        if name == self.targetpv:
            self._cache.put(self._name, param, value, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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


def _update_mapped_choices(mapped_device):
    choices = mapped_device._epics_wrapper.get_value_choices(mapped_device.readpv)
    new_mapping = {}
    for i, choice in enumerate(choices):
        new_mapping[choice] = i
    mapped_device._setROParam("mapping", new_mapping)
    mapped_device._inverse_mapping = {}
    for k, v in mapped_device.mapping.items():
        mapped_device._inverse_mapping[v] = k


class EpicsMappedReadable(EpicsReadable, MappedReadable):
    valuetype = str

    parameter_overrides = {
        # MBBI, BI, etc. do not have units
        "unit": Override(mandatory=False, settable=False, volatile=False),
        # Mapping values are read from EPICS
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    def doInit(self, mode):
        EpicsReadable.doInit(self, mode)

        if session.sessiontype != POLLER and not self.monitor:
            _update_mapped_choices(self)
        MappedReadable.doInit(self, mode)

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv, as_string=True),
        )

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        if not self.mapping:
            _update_mapped_choices(self)
        time_stamp = time.time()
        self._cache.put(
            self._name,
            param,
            self._inverse_mapping.get(value, value),
            time_stamp,
        )


class EpicsMappedMoveable(EpicsParameters, MappedMoveable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

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

    parameter_overrides = {
        # MBBI, BI, etc. do not have units
        "unit": Override(mandatory=False, settable=False, volatile=False),
        # Mapping values are read from EPICS
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    _record_fields = {
        "readpv": RecordInfo("value", "", RecordType.BOTH),
        "writepv": RecordInfo("target", "", RecordType.VALUE),
        "targetpv": RecordInfo("target", "", RecordType.VALUE),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        if self.targetpv:
            self._epics_wrapper.connect_pv(self.targetpv)

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            if self.targetpv:
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self.targetpv,
                        self._record_fields["targetpv"].cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

        if session.sessiontype != POLLER and not self.monitor:
            _update_mapped_choices(self)
        MappedMoveable.doInit(self, mode)

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv, as_string=True),
        )

    def doStatus(self, maxage=0):
        def _func():
            try:
                return self._epics_wrapper.get_alarm_status(self.readpv)
            except TimeoutError:
                return status.ERROR, "timeout reading status"

        return get_from_cache_or(self, "status", _func)

    def doStart(self, value):
        self._epics_wrapper.put_pv_value(self.writepv, self.mapping[value])

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if name == self.readpv:
            if not self.mapping:
                _update_mapped_choices(self)
            self._cache.put(
                self._name,
                param,
                self._inverse_mapping.get(value, value),
                time_stamp,
            )
            self._cache.put(self._name, "unit", units, time_stamp)
        if name == self.writepv and not self.target:
            self._cache.put(self._name, param, value, time_stamp)
        if name == self.targetpv:
            self._cache.put(self._name, param, value, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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


class EpicsManualMappedAnalogMoveable(
    EpicsParameters, HasPrecision, HasLimits, MappedMoveable
):
    """
    Acts as a moveable device, which reads and writes to EPICS PVs but it
    has a configurable mapping. Used for example to map allowed chopper speeds
    instead of allowing all values in a range.
    """

    parameters = {
        "readpv": Param(
            "PV for reading device value", type=pvname, mandatory=True, userparam=False
        ),
        "writepv": Param(
            "PV for writing device target", type=pvname, mandatory=True, userparam=False
        ),
        "targetpv": Param(
            "Optional target readback PV.", type=none_or(pvname), userparam=False
        ),
    }

    parameter_overrides = {
        "abslimits": Override(mandatory=False, volatile=True),
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _record_fields = {
        "readpv": RecordInfo("value", "", RecordType.BOTH),
        "writepv": RecordInfo("target", "", RecordType.VALUE),
        "targetpv": RecordInfo("target", "", RecordType.VALUE),
    }

    valuetype = anytype

    def doPreinit(self, mode):
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)
        self._epics_wrapper.connect_pv(self.writepv)
        if self.targetpv:
            self._epics_wrapper.connect_pv(self.targetpv)

    def doInit(self, mode):
        MappedMoveable.doInit(self, mode)

        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            if self.targetpv:
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self.targetpv,
                        self._record_fields["targetpv"].cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

    def _readRaw(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv),
        )

    def _startRaw(self, raw_value):
        self._epics_wrapper.put_pv_value(self.writepv, raw_value)

    def doStart(self, value):
        raw_target = self.mapping.get(value, value)
        try:
            raw_now = self.read(0)
        except Exception:
            raw_now = None

        # probably don't need this check
        # if raw_now is not None and abs(raw_now - raw_target) <= self.precision:
        #     return

        self._cache.put(
            self._name, "status", (status.BUSY, f"moving to {value}"), time.time()
        )

        super().doStart(value)

    def doRead(self, maxage=0):
        return get_from_cache_or(
            self,
            self._record_fields["readpv"].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self.readpv),
        )

    def doReadUnit(self):
        return get_from_cache_or(
            self, "unit", lambda: self._epics_wrapper.get_units(self.readpv)
        )

    def doReadAbslimits(self):
        lo, hi = get_from_cache_or(
            self, "abslimits", lambda: self._epics_wrapper.get_limits(self.writepv)
        )
        return (-1e308, 1e308) if (lo == 0 and hi == 0) else (lo, hi)

    def doReadTarget(self, maxage=0):
        def _func():
            raw_value = self._epics_wrapper.get_pv_value(self.targetpv or self.writepv)
            if hasattr(self, "_inverse_mapping"):
                return self._inverse_mapping.get(raw_value, None)
            # if inverse mapping not built, access it manually
            for k, v in self.mapping.items():
                if v == raw_value:
                    return k
            return None

        return get_from_cache_or(
            self,
            "target",
            _func,
        )

    def _do_status(self):
        try:
            severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if severity in (status.ERROR, status.WARN):
            return severity, msg

        try:
            raw_pos = self._epics_wrapper.get_pv_value(self.readpv)
            raw_tgt = self._epics_wrapper.get_pv_value(self.targetpv or self.writepv)
            at_target = HasPrecision.doIsAtTarget(self, raw_pos, raw_tgt)
        except Exception:
            at_target = False

        if not at_target:
            return status.BUSY, f"moving to {self.target}"
        return status.OK, msg

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def doIsAtTarget(self, pos=None, target=None):
        if target is None:
            target = self.target
        if pos is None:
            pos = self.read(0)
        raw_target = self.mapping.get(target, target)
        try:
            return HasPrecision.doIsAtTarget(self, pos, raw_target)
        except Exception:
            return False

    def doIsCompleted(self):
        return self.isAtTarget()

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            return
        ts = time.time()
        if name == self.readpv:
            self._cache.put(self._name, param, value, ts)
            self._cache.put(self._name, "unit", units, ts)
            self._cache.put(self._name, "status", self._do_status(), ts)
        if name == self.writepv and limits:
            self._cache.put(self._name, "abslimits", limits, ts)
        if name == self.writepv and not self.target:
            self._cache.put(self._name, param, value, ts)
            self._cache.put(self._name, "status", self._do_status(), ts)
        if name == self.targetpv:
            self._cache.put(self._name, param, value, ts)
            self._cache.put(self._name, "status", self._do_status(), ts)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            return
        self._cache.put(self._name, "status", self._do_status(), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["readpv"].cache_key:
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

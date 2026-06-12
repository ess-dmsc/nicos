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

"""Concrete ESS EPICS PVA devices."""

import time

from nicos.core import (
    SIMULATION,
    HasLimits,
    HasPrecision,
    Moveable,
    Override,
    Param,
    PositionError,
    Readable,
    anytype,
    pvname,
    status,
)
from nicos.devices.abstract import MappedMoveable, MappedReadable
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
    EpicsMappedChoiceSupport,
    EpicsParameters,  # noqa: F401  (re-export for existing importers)
    EpicsReadWriteBase,
    MappedChoiceSource,  # noqa: F401  (re-export for existing importers)
    _update_mapped_choices,
    create_wrapper,  # noqa: F401  (re-export for existing importers)
    get_from_cache_or,  # noqa: F401  (re-export for existing importers)
    status_from_candidates,
)


class EpicsReadable(EpicsDeviceBase, Readable):
    parameters = {
        "readpv": Param(
            "PV for reading device value", type=pvname, mandatory=True, userparam=False
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _primary_channel = "read"
    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            pv_attr="readpv",
        ),
    }

    def doRead(self, maxage=0):
        return self._read_channel_cached("read", maxage=maxage)


class EpicsStringReadable(EpicsReadable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            as_string=True,
            pv_attr="readpv",
        ),
    }


class EpicsAnalogMoveable(EpicsReadWriteBase, HasPrecision, HasLimits, Moveable):
    """
    Handles EPICS devices which can set and read a floating value.
    """

    valuetype = float

    parameter_overrides = {
        "abslimits": Override(mandatory=False, volatile=True),
        "unit": Override(mandatory=False, settable=False, volatile=True),
    }

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            pv_attr="readpv",
        ),
        "write": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.STATUS,
            pv_attr="writepv",
        ),
        "target": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.STATUS,
            pv_attr="targetpv",
            optional=True,
        ),
    }

    def doRead(self, maxage=0):
        return self._read_channel_cached("read", maxage=maxage)

    def _compute_status(self, maxage=0):
        candidates = []
        target = self._cached_raw_target(maxage)
        if not HasPrecision.doIsAtTarget(self, self.doRead(maxage), target):
            candidates.append((status.BUSY, f"moving to {target}"))
        return status_from_candidates(
            self._read_primary_alarm(maxage=maxage), candidates
        )

    def doReadTarget(self):
        return self._cached_raw_target()

    def doStart(self, value):
        self._epics.put_channel_value("write", value)


class EpicsDigitalMoveable(EpicsAnalogMoveable):
    """
    Handles EPICS devices which can set and read an integer value.
    """

    valuetype = int

    parameter_overrides = {
        "fmtstr": Override(default="%d"),
    }


class EpicsStringMoveable(EpicsReadWriteBase, Moveable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            as_string=True,
            pv_attr="readpv",
        ),
        "write": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.VALUE,
            as_string=True,
            pv_attr="writepv",
        ),
        "target": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.VALUE,
            as_string=True,
            pv_attr="targetpv",
            optional=True,
        ),
    }

    def doRead(self, maxage=0):
        return self._read_channel_cached("read", maxage=maxage)

    def doStart(self, value):
        self._epics.put_channel_value("write", value)


class EpicsMappedReadable(EpicsMappedChoiceSupport, EpicsReadable, MappedReadable):
    valuetype = str

    parameter_overrides = {
        # MBBI, BI, etc. do not have units
        "unit": Override(mandatory=False, settable=False, volatile=False),
        # Mapping values are read from EPICS
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            as_string=True,
            pv_attr="readpv",
        ),
    }

    def _after_subscribe(self, mode):
        if mode != SIMULATION:
            _update_mapped_choices(self)
        MappedReadable.doInit(self, mode)

    def doRead(self, maxage=0):
        return self._read_mapped_choice(maxage=maxage)


class EpicsMappedMoveable(EpicsMappedChoiceSupport, EpicsReadWriteBase, MappedMoveable):
    """
    This device handles string PVs, also when they are implemented as
    character waveforms.
    """

    valuetype = str

    parameter_overrides = {
        # MBBI, BI, etc. do not have units
        "unit": Override(mandatory=False, settable=False, volatile=False),
        # Mapping values are read from EPICS
        "mapping": Override(internal=True, mandatory=False, settable=False),
    }

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            as_string=True,
            pv_attr="readpv",
        ),
        "write": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.VALUE,
            as_string=True,
            pv_attr="writepv",
        ),
        "target": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.VALUE,
            as_string=True,
            pv_attr="targetpv",
            optional=True,
        ),
    }

    def _after_subscribe(self, mode):
        if mode != SIMULATION:
            _update_mapped_choices(self)
        MappedMoveable.doInit(self, mode)

    def doRead(self, maxage=0):
        return self._read_mapped_choice(maxage=maxage)

    def _startRaw(self, value):
        self._epics.put_channel_value("write", value)


class EpicsManualMappedAnalogMoveable(
    EpicsReadWriteBase, HasPrecision, HasLimits, MappedMoveable
):
    """
    Acts as a moveable device, which reads and writes to EPICS PVs but it
    has a configurable mapping. Used for example to map allowed chopper speeds
    instead of allowing all values in a range.
    """

    parameter_overrides = {
        "abslimits": Override(mandatory=False, volatile=True),
        "unit": Override(mandatory=False, settable=False, volatile=True),
        "mapping": Override(settable=True),
    }

    valuetype = anytype

    _epics_channels = {
        "read": EpicsChannelInfo(
            "value",
            "",
            EpicsChannelRole.VALUE_AND_STATUS,
            pv_attr="readpv",
        ),
        "write": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.STATUS,
            pv_attr="writepv",
        ),
        "target": EpicsChannelInfo(
            "target",
            "",
            EpicsChannelRole.STATUS,
            pv_attr="targetpv",
            optional=True,
        ),
    }

    def _after_subscribe(self, mode):
        MappedMoveable.doInit(self, mode)

    def _readRaw(self, maxage=0):
        return self._read_channel_cached("read", maxage=maxage)

    def _startRaw(self, raw_value):
        self._epics.put_channel_value("write", raw_value)

    def doStart(self, value):
        self._cache.put(
            self._name, "status", (status.BUSY, f"moving to {value}"), time.time()
        )

        super().doStart(value)

    def doRead(self, maxage=0):
        return self._readRaw(maxage=maxage)

    def doReadTarget(self):
        return self._map_target_readback(self._cached_raw_target())

    def _map_target_readback(self, value):
        if value in self.mapping:
            return value
        if not hasattr(self, "_inverse_mapping"):
            MappedReadable.doInit(self, getattr(self, "_mode", None))
        try:
            return MappedReadable._mapReadValue(self, value)
        except PositionError:
            pass
        return None

    def _raw_target(self, maxage=0):
        target = self._cached_raw_target(maxage)
        return self.mapping.get(target, target)

    def _compute_status(self, maxage=0):
        candidates = []
        try:
            raw_pos = self._readRaw(maxage)
            raw_tgt = self._raw_target(maxage)
            at_target = HasPrecision.doIsAtTarget(self, raw_pos, raw_tgt)
        except Exception:
            at_target = False

        if not at_target:
            candidates.append((status.BUSY, f"moving to {self.target}"))
        return status_from_candidates(
            self._read_primary_alarm(maxage=maxage), candidates
        )

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

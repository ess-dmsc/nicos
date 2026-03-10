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

"""Small reusable doubles for harness tests."""

from nicos.core import Moveable, Param, Readable, status
from nicos.devices.abstract import MappedMoveable


class HarnessReadable(Readable):
    """Simple read-only device with a fixed value."""

    parameters = {
        "initial": Param(
            "Initial value for harness tests",
            type=str,
            default="",
            mandatory=False,
            userparam=False,
        ),
    }

    def doRead(self, maxage=0):
        del maxage
        return self.initial

    def doStatus(self, maxage=0):
        del maxage
        return status.OK, ""


class HarnessMoveable(Moveable):
    """Simple moveable used as attached device in harness tests."""

    parameters = {
        "initial": Param(
            "Initial value for harness tests",
            type=float,
            default=0.0,
            mandatory=False,
            userparam=False,
        ),
    }

    def doInit(self, mode):
        del mode
        self._value = float(self.initial)

    def doRead(self, maxage=0):
        del maxage
        return self._value

    def doStart(self, target):
        self._value = target

    def doStatus(self, maxage=0):
        del maxage
        return status.OK, ""


class HarnessMappedMoveable(MappedMoveable):
    """Minimal mapped moveable with in-memory raw value."""

    def doInit(self, mode):
        self._raw_value = next(iter(self.mapping.values()))
        super().doInit(mode)

    def _readRaw(self, maxage=0):
        del maxage
        return self._raw_value

    def _startRaw(self, target):
        self._raw_value = target

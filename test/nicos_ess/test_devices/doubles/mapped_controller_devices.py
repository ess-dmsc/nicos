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
#   NICOS contributors
#
# *****************************************************************************

"""Reusable moveable doubles for mapped-controller harness tests."""

from nicos.core import HasLimits, HasPrecision, Moveable, Param, status


class HarnessLinearAxis(HasPrecision, HasLimits, Moveable):
    """Simple numeric axis with limits, precision and controllable status."""

    parameters = {
        "initial_value": Param(
            "Initial position for harness tests",
            type=float,
            default=0.0,
            mandatory=False,
            userparam=False,
        ),
    }

    def doInit(self, mode):
        del mode
        self._value = float(self.initial_value)
        self._status = (status.OK, "idle")
        self._started_targets = []

    def doRead(self, maxage=0):
        del maxage
        return self._value

    def doStart(self, value):
        self._started_targets.append(value)
        self._value = value
        self._status = (status.OK, "idle")

    def doStatus(self, maxage=0):
        del maxage
        return self._status

    def set_readback(self, value):
        self._value = value

    def set_status(self, state, message):
        self._status = (state, message)


class HarnessMoveableNoPrecision(HasLimits, Moveable):
    """Simple numeric axis without precision support."""

    parameters = {
        "initial_value": Param(
            "Initial position for harness tests",
            type=float,
            default=0.0,
            mandatory=False,
            userparam=False,
        ),
    }

    def doInit(self, mode):
        del mode
        self._value = float(self.initial_value)
        self._status = (status.OK, "idle")
        self._started_targets = []

    def doRead(self, maxage=0):
        del maxage
        return self._value

    def doStart(self, value):
        self._started_targets.append(value)
        self._value = value
        self._status = (status.OK, "idle")

    def doStatus(self, maxage=0):
        del maxage
        return self._status

    def set_readback(self, value):
        self._value = value

    def set_status(self, state, message):
        self._status = (state, message)

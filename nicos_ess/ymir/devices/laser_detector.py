#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
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
from nicos.core.params import Attach
from nicos import session
from nicos.core import Param, Value, status, tupleof
from nicos.core.constants import LIVE
from nicos.core.device import Measurable, Readable
from nicos.devices.epics import pvget


class LaserDetector(Measurable):
    parameters = {
        'curstatus': Param('Store the current device status',
                           internal=True, type=tupleof(int, str),
                           default=(status.OK, ""),
                           settable=True),
        'answer': Param('Store the current device status',
                        internal=True, type=float,
                        default=0,
                        settable=True),
    }
    attached_devices = {
        'laser': Attach('the underlying laser device', Readable),
    }

    def doPrepare(self):
        self.curstatus = status.BUSY, "Preparing"
        self.curstatus = status.OK, ""

    def doStart(self):
        max_pow = 0
        results = []
        for _ in range(5):
            session.delay(0.1)
            val = self._attached_laser.doRead()
            max_pow = max(val, max_pow)
            results.append(val)
        self.answer = sum(results) / len(results)

    def doRead(self, maxage=0):
        return [self.answer]

    def doFinish(self):
        self._stop_processing()

    def _stop_processing(self):
        self.curstatus = status.OK, ""

    def doSetPreset(self, t, **preset):
        self.curstatus = status.BUSY, "Preparing"

    def doStop(self):
        # Treat like a finish
        self._stop_processing()

    def doStatus(self, maxage=0):
        return self._attached_laser.doStatus(maxage)

    def duringMeasureHook(self, elapsed):
        return LIVE

    def valueInfo(self):
        return Value(self.name, unit=self.unit),

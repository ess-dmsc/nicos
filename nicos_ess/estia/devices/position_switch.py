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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
"""
This module contains ESS specific Base classes for EPICS.
"""

from nicos.core import Param, pvname
from nicos_ess.devices.epics.base import EpicsReadableEss


class EpicsPositionSwitch(EpicsReadableEss):
    parameters = {
        "readpv": Param(
            "Name of the status PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        )
    }

    def doInit(self, mode):
        EpicsReadableEss.doInit(self, mode)

    def doRead(self, maxage=0):
        deci_status = self._get_pv("readpv")
        hex_status = hex(deci_status)
        bit0 = hex_status[-1]
        bit1 = hex_status[-2]
        if bit0:
            return "collisionBwd"
        if bit1:
            return "collisionFwd"

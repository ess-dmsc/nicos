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
#   Kenan Muric <kenan.muric@ess.eu>
#
# *****************************************************************************
from nicos.core import Param, pvname
from nicos_ess.devices.epics.pva.epics_devices import EpicsStringReadable


class ChopperStatus(EpicsStringReadable):
    """
    This device handles chopper alarms as strings.
    """
    parameters = {
        'readpv': Param('PV for reading device value',
                        type=pvname, mandatory=True, userparam=False),
        'pv_root': Param('PV root for device', type=str, mandatory=True,
                         userparam=False),
    }
    _alarm_status_pvs = ['Comm_alrm',
                         'CpuTmp_Stat',
                         'HW_Alrm',
                         'SW_Alrm',
                         'nTmp_Alrm',
                         'ILck_Alrm',
                         'Pos_Alrm',
                         'Ref_Alrm',
                         'V_Alrm',
                         'SIM_Alrm']

    def doStatus(self, maxage=0):
        pass

#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2023 by the NICOS contributors (see AUTHORS)
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
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************
import time

from nicos.core import SIMULATION, Override, Param, pvname, status
from nicos.devices.abstract import MappedMoveable

from nicos.devices.epics.pva import EpicsDevice


class RheometerControl(EpicsDevice, MappedMoveable):
    parameters = {
        "pv_root": Param(
            "The PV root for the rheometer.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        'unit':
            Override(mandatory=False, settable=False, userparam=False),
        'mapping':
            Override(mandatory=False,
                     settable=False,
                     userparam=False,
                     volatile=False),
    }

    _record_fields = {}

    def doPreinit(self, mode):
        self._set_custom_record_fields()
        EpicsDevice.doPreinit(self, mode)

    def doInit(self, mode):
        if mode == SIMULATION:
            return
        MappedMoveable.doInit(self, mode)

    def _set_custom_record_fields(self):
        self._record_fields['set_config'] = 'LoadMeasConfig-S.VAL$'
        self._record_fields['read_config'] = 'LoadMeasConfig-RB'
        self._record_fields['start'] = 'Start'
        self._record_fields['proc_start'] = 'MeasHeader-R.PROC'

    def _get_pv_parameters(self):
        return set(self._record_fields)

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doStatus(self, maxage=0):
        return status.OK, ""

    def doRead(self, maxage=0):
        return self._get_pv('read_config')

    def doStop(self):
        pass

    def doStart(self, target=None):
        CONFIG = ':PROG["Test",TEST[(PART[(NUMB[5,LAST],DTIM[1,1,REL]),(),(),(),(SRAT[1,FUNC[LOG,(1,10)]]),(),(),,(DAPT[TEMP[2,??T]],DAPT[TORQ[1,??T]],DAPT[SPEE[1,??T]],DAPT[EXCU[1,??T]],DAPT[FORC[1,??T]],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],DAPT[EXCE[1,??T]],DAPT[ETRQ[1,??T]]),(GENP[0,(IFDT[EX])],SETV[0,(IFST[IN,(16)])]),(EXCU[1,!?])],PART[(NUMB[10,LAST],DTIM[FUNC[LIN,(1,1.888888889)],2,REL]),(),(),(),(STRA[1,OSCI[FUNC[LIN,(0.03,0.07)],FUNC[LOG,(0.3183098862,1.432394488)],SIN]]),(),(),VALF[STRA[1,?&]],(VALF[STRA[1,?&]],DAPT[TEMP[2,??T]],COMP[MODU[1,??F],1,PHAS],COMP[TORQ[1,??F],0,CABS],COMP[TORQ[1,??F],1,CABS],DAPT[KFAC[1,??T]],COMP[SPEE[1,??F],0,CABS],COMP[EXCU[1,??F],0,CABS],COMP[EXCU[1,??F],1,CABS],COMP[FORC[1,??F],0,REAL],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],COMP[EXCE[1,??F],0,CABS],COMP[EXCE[1,??F],1,CABS],COMP[ETRQ[1,??F],0,CABS],COMP[ETRQ[1,??F],1,CABS]),(GENP[0,(IFDT[EX])],SETV[0,(IFST[IN,(16)])]),()],PART[(NUMB[12,LAST]),(),(),(),(SRAT[1,FUNC[LIN,(1,5)]]),(),(),,(DAPT[TEMP[2,??T]],DAPT[TORQ[1,??T]],DAPT[SPEE[1,??T]],DAPT[EXCU[1,??T]],DAPT[FORC[1,??T]],DAPT[VOLT[1,??T]],DAPT[DIST[1,??T]],GSTR[STAT[1,??T]],DAPT[VELO[1,??T]],DAPT[DGAP[1,??T]],DAPT[TIMA[1,??T]],DAPT[TIMP[1,??T]],DAPT[EXCE[1,??T]],DAPT[ETRQ[1,??T]]),(GENP[0,(IFST[IN,(17)])],SETV[0,(IFST[IN,(16)])]),()])],EXIT[()],CANC[()]]'
        conf_list_with_q = [*CONFIG]
        conf_list_ascii = [ord(c) for c in conf_list_with_q]
        self._put_pv('set_config', conf_list_ascii)
        time.sleep(2)
        self._put_pv('proc_start', 1)
        time.sleep(1)
        self._put_pv('start', 1)

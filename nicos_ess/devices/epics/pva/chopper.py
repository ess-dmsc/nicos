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
from nicos import session
from nicos.core import Param, pvname, status
from nicos_ess.devices.epics.pva.epics_devices import EpicsStringReadable


class ChopperAlarms(EpicsStringReadable):
    """
    This device handles chopper alarms.
    """
    parameters = {
        'readpv': Param('PV for reading device value',
                        type=pvname, mandatory=True, userparam=False),
        'pv_stem': Param('PV stem for device', type=str, mandatory=True,
                         userparam=False),
    }
    _chopper_alarm_names = {'Comm_alrm', 'CpuTmp_Stat', 'HW_Alrm',
                            'SW_Alrm', 'nTmp_Alrm', 'ILck_Alrm',
                            'Pos_Alrm', 'Ref_Alrm', 'V_Alrm', 'SIM_Alrm'}
    _chopper_alarm_pvs = []
    _alarm_state = {}
    _alarm_severity_field = 'SEVR'
    _alarm_status_field = 'STAT'

    def doPreinit(self, mode):
        super().doPreinit(mode)
        self._chopper_alarm_pvs = [':'.join([getattr(self, 'pv_stem'), name])
                                   for name in self._chopper_alarm_names]
        self._alarm_state = dict(zip(self._chopper_alarm_pvs,
                                     [{'severity': status.OK,
                                       'status': 'NO_ALARM'}]
                                     * len(self._chopper_alarm_pvs)))

    def doStatus(self, maxage=0):
        alarm_msg = ''
        for alarm_pv in self._chopper_alarm_pvs:
            session.log.error(alarm_pv)
            alarm_value = self._read_process_variable(alarm_pv)
            if alarm_value:
                alarm_severity = self._read_process_variable(
                    '.'.join([alarm_pv, self._alarm_severity_field]))
                alarm_status = self._read_process_variable(
                    '.'.join([alarm_pv, self._alarm_status_field]))
                alarm_msg = self._create_alarm_message(alarm_value,
                                                       alarm_severity,
                                                       alarm_status)
                self._alarm_state[alarm_pv]['severity'] = \
                    self._convert_to_nicos_status(alarm_severity)
                self._alarm_state[alarm_pv]['status'] = alarm_status
                self._write_alarm_to_log(alarm_msg,
                                         self._alarm_state[alarm_pv]['severity'])

        return self._alarm_state[alarm_pv]['severity'], alarm_msg

    def _create_alarm_message(self, alarm_value, alarm_severity, alarm_status):
        return f'Value of alarm: {alarm_value}, ' \
               f'alarm severity: {alarm_severity}, ' \
               f'alarm status: {alarm_status}'

    @staticmethod
    def _convert_to_nicos_status(alarm_severity):
        """
        Converts EPICS errors to corresponding NICOS status.
        """
        if alarm_severity == 'MAJOR':
            return status.ERROR
        elif alarm_severity == 'MINOR':
            return status.WARN
        elif alarm_severity == 'INVALID':
            return status.UNKNOWN
        return status.OK

    @staticmethod
    def _write_alarm_to_log(msg, alarm_severity):
        if alarm_severity is status.ERROR:
            session.log.error(msg)
        elif alarm_severity is status.WARN:
            session.log.warning(msg)
        else:
            session.log.info(msg)

    def _read_process_variable(self, pv, as_string=False):
        session.log.error(pv)
        return self._epics_wrapper.get_pv_value(pv, timeout=self.epicstimeout,
                                                as_string=as_string)

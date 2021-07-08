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

    def doInit(self, mode):
        EpicsStringReadable.doInit(self, mode)
        self._chopper_alarm_pvs = [':'.join([getattr(self, 'pv_stem'), name])
                                   for name in self._chopper_alarm_names]
        self._alarm_state = dict(zip(self._chopper_alarm_pvs,
                                     [{'severity': status.OK,
                                       'status': 'NO_ALARM'}]
                                     * len(self._chopper_alarm_pvs)))

    def doStatus(self, maxage=0):
        """
        Goes through all alarms in the chopper and returns the alarm encountered
        with the highest severity. All alarms are printed in the session log.
        """
        displayed_alarm_msg = ''
        displayed_alarm_severity = status.OK
        for alarm_pv in self._chopper_alarm_pvs:
            alarm_value = self._read_process_variable(alarm_pv)
            alarm_status = self._read_process_variable(
                '.'.join([alarm_pv, 'STAT']))
            if alarm_value:
                alarm_severity = self._read_process_variable(
                    '.'.join([alarm_pv, 'SEVR']))
                pv_msg_txt = self._read_process_variable(
                    '-'.join([alarm_pv, 'MsgTxt']))
                alarm_msg = self._create_alarm_message(pv_msg_txt,
                                                       alarm_pv)
                self._alarm_state[alarm_pv]['severity'] = \
                    self._convert_to_nicos_status(alarm_severity)
                self._alarm_state[alarm_pv]['status'] = alarm_status
                self._write_alarm_to_log(alarm_msg,
                                         self._alarm_state[alarm_pv]['severity'],
                                         alarm_status)
                # If severity of current alarm is higher, make that the return
                # values of the function.
                if self._alarm_state[alarm_pv]['severity'] > \
                        displayed_alarm_severity:
                    displayed_alarm_severity = \
                        self._alarm_state[alarm_pv]['severity']
                    displayed_alarm_msg = alarm_msg
            else:
                self._alarm_state[alarm_pv]['severity'] = status.OK
                self._alarm_state[alarm_pv]['status'] = alarm_status

        return displayed_alarm_severity, displayed_alarm_msg

    @staticmethod
    def _create_alarm_message(pv_msg_txt, alarm_pv):
        return f'Alarm PV: "{alarm_pv}", ' \
               f'Message: {pv_msg_txt} '

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

    def _write_alarm_to_log(self, alarm_msg, alarm_severity, alarm_status):
        alarm_msg += f', Alarm severity = {alarm_severity}, '
        alarm_msg += f'Alarm status = {alarm_status}'
        if alarm_severity == status.ERROR:
            self.log.error(alarm_msg)
        elif alarm_severity == status.WARN:
            self.log.warning(alarm_msg)
        else:
            self.log.info(alarm_msg)

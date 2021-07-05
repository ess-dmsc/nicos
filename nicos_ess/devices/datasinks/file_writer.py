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
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************

from time import time as currenttime
from nicos.core import Param, status, Device, host, listof
from streaming_data_types import deserialise_x5f2
import json
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler


class FileWriterStatus(KafkaStatusHandler):

    def new_messages_callback(self, messages):
        key = max(messages.keys())
        if messages[key][4:8] == b"x5f2":
            result = deserialise_x5f2(messages[key])
            _status = json.loads(result.status_json)
            self._setROParam(
                'statusinterval', result.update_interval // 1000
            )
            if _status['state'] == 'idle':
                self.curstatus = status.OK, _status['state']
            else:
                self.curstatus = status.BUSY, _status['state']
            next_update = currenttime() + self.statusinterval
            if next_update > self.nextupdate:
                self._setROParam('nextupdate', next_update)


class FileWriterParameters(Device):
    parameters = {
        'brokers': Param('List of kafka hosts to be connected to',
                        type=listof(host(defaultport=9092)),
                        default=['localhost'], preinit=True, userparam=False),
        'command_topic': Param(
            'Kafka topic where status messages are written',
            type=str, settable=False, preinit=True, mandatory=True,
            userparam=False,),
        'nexus_config_path': Param('NeXus configuration file (full-path)',
                                   type=str, mandatory=True, userparam=False,),
        'job_id': Param('Writer job identification',
                        type=str, mandatory=False, userparam=False,),
    }

    def set_job_id(self, val):
        self._setROParam('job_id', val)

    def get_job_id(self):
        return self.job_id

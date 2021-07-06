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

import json
from datetime import datetime
from time import time as currenttime

from file_writer_control.JobHandler import JobHandler
from file_writer_control.WorkerCommandChannel import WorkerCommandChannel
from file_writer_control.WriteJob import WriteJob
from streaming_data_types import deserialise_x5f2

from nicos import session
from nicos.core import ADMIN, Device, Param, host, listof, requires, status

from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler
from nicos_ess.nexus.nexus_config import NexusTemplate

# TODO: sometimes the GUI says writing even when it is idle
# And NICOS itself thinks the FW is idle (via doStatus)
class FileWriterStatus(KafkaStatusHandler):
    def new_messages_callback(self, messages):
        key = max(messages.keys())
        if messages[key][4:8] == b'x5f2':
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


class FileWriterControl(Device):
    parameters = {
        'brokers': Param('List of kafka hosts to be connected',
            type=listof(host(defaultport=9092)), mandatory=True, preinit=True,
            userparam=False
        ),
        'command_topic': Param(
            'Kafka topic where status messages are written',
            type=str, settable=False, preinit=True, mandatory=True,
            userparam=False,
        ),
        'nexus_config_path': Param('NeXus configuration file (full-path)',
            type=str, mandatory=True, userparam=True, settable=True),
        'job_id': Param('Writer job identification',
            type=str, mandatory=False, userparam=False,
            internal=True
        ),
        'ack_timeout': Param('How long to wait for timeout on acknowledgement',
            type=int, default=5, unit='s', userparam=False,
            settable=False,
        ),
    }

    _command_channel = None
    _job_handler = None

    def doPreinit(self, mode):
        # TODO: Can we not just get the current job_id from FileWriterStatus
        self._set_job_id(self._cache.get(self.name, 'job_id', default=''))
        self._command_channel = \
            WorkerCommandChannel(f'{self.brokers[0]}/{self.command_topic}')
        # If there is a job_id then this means the file-writer is currently
        # writing
        self._job_handler = JobHandler(worker_finder=self._command_channel,
                                       job_id=self.job_id)

    def doStart(self):
        if self.job_id:
            session.log.warning(
                'A write job is already running. To start a new '
                'job, please stop the current one')
            return

        nexus_structure = self._read_nexus_config()

        # Initialise the write job.
        write_job = WriteJob(
            nexus_structure,
            '{0:%Y}-{0:%m}-{0:%d}_{0:%H}{0:%M}.nxs'.format(datetime.now()),
            self.brokers[0],
            datetime.now(),
        )

        start_handler = self._job_handler.start_job(write_job)
        self._set_job_id(write_job.job_id)
        timeout = int(currenttime()) + self.ack_timeout

        # TODO: this should be non-blocking?
        while not start_handler.is_done():
            if int(currenttime()) > timeout:
                session.log.error(f'Request to start writing job not '
                                  'acknowledged by filewriter')
                self._set_job_id('')
                return

        session.log.info(f'Writing job with ID {self.job_id} is starting')

    def _read_nexus_config(self):
        config = self.nexus_config_path
        nexus_template = NexusTemplate(config)
        nexus_template.load_config_file()
        nexus_template.add_proposal_information()
        return str(nexus_template)

    def doStop(self):
        if not self.job_id:
            self.log.warning(
                'Cannot stop file-writer job because the ID is unknown')
            return

        stop_handler = self._job_handler.stop_now()
        timeout = int(currenttime()) + self.ack_timeout

        # TODO: this should be non-blocking too?
        while not stop_handler.is_done() and not self._job_handler.is_done():
            if int(currenttime()) > timeout:
                session.log.error(f'Request to stop writing job not'
                                  'acknowledged by filewriter')
                return

        session.log.info(f'Writing job with ID {self.job_id} is stopping')
        self._set_job_id('')

    @requires(level=ADMIN)
    def reset_job_id(self, value=''):
        # HACK: this is a hack so that if the filewriting is started/stopped
        # outside of NICOS we can force a job_id into NICOS
        self._set_job_id(value)

    def _set_job_id(self, value):
        self._setROParam('job_id', value)

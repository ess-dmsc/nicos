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
#   Nikhil Biyani <nikhil.biyani@psi.ch>
#
# *****************************************************************************

from streaming_data_types.fbschemas.forwarder_config_update_rf5k import Protocol, \
    UpdateType
from streaming_data_types.forwarder_config_update_rf5k import StreamInfo, \
    serialise_rf5k

from nicos.core import Attach, Device, Param, oneof, status, usermethod

from nicos_ess.devices.kafka.producer import ProducesKafkaMessages
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler


class EpicsKafkaForwarderControl(ProducesKafkaMessages, Device):
    """ Configures the EPICS to Kafka forwarder

    This class is used to configure the forwarder that forwards EPICS PVs
    to Kafka topics. The commands are written on a Kafka topic provided
    in the parameters. These commands are then captured by the forwarder
    which writes all the changes to PVs on the provided Kafka topics.
    The messages are serialized by the forwarder using flatbuffers with
    schema-id provided in parameters.

    Default values for topic and schema can be set using *instpvtopic* and
    *instpvschema* parameters. These can be overridden for each device
    and also can be overridden for each PV while configuring the device.
    """

    parameters = {
        'cmdtopic': Param('Kafka topic to write configurations commands',
            type=str, settable=False, mandatory=True, userparam=False, ),
        'instpvtopic': Param(
            'Default topic for the instrument where PVs are to be forwarded',
            type=str, mandatory=True, userparam=False, ),
        'instpvschema': Param(
            'Default flatbuffers schema to be used for the instrument',
            type=oneof('f142', 'f143'), settable=False, default='f142',
            userparam=False, ),
    }

    def doPreinit(self, mode):
        ProducesKafkaMessages.doPreinit(self, mode)

    def doInit(self, mode):
        self._issued = {}
        self._notforwarding = {}

    def doStatus(self, maxage=0):
        if not self._issued:
            return status.OK, 'None issued'
        if not self._notforwarding:
            return status.OK, 'Forwarding..'
        num_not_forwarded = len(self._notforwarding)
        num_pvs = len(self._issued.keys())
        if num_not_forwarded == num_pvs:
            return status.ERROR, 'None forwarded!'
        return (status.WARN, f'Not forwarded: {num_not_forwarded}/{num_pvs}',)

    def status_update(self, message):
        """
        Updates the list of the PVs currently forwarded according to the
        `forward-epics-to-kafka` and compares the information with the PVs
        the NICOS issued.
        :param messages: a list in the form
         [ {'channel_name': pv, 'converters': [{'broker': broker, 'topic':
        topic, 'schema': schema_id}, {...} ], ...]
        :return:
        """

        def get_not_forwarding(msg, issued):
            if not msg["streams"]:
                return issued.keys()
            pvs_read = []
            not_forwarded = []
            for stream in msg["streams"]:
                pv = stream["channel_name"]
                pvs_read.append(pv)
                if pv in issued:
                    forwarding = (issued[pv][0] == stream["output_topic"] and
                        issued[pv][1] == stream["schema"])
                    if not forwarding:
                        not_forwarded.append(pv)
            not_forwarded += [pv for pv in issued if pv not in pvs_read]
            return not_forwarded

        if self._issued:
            self._notforwarding = set(get_not_forwarding(message, self._issued))

        self.doStatus()

    def add(self, pv_details):
        try:
            config_change = UpdateType.UpdateType.ADD
            streams = [StreamInfo(pv, schema or self.instpvschema,
                                      topic or self.instpvtopic,
                Protocol.Protocol.CA, ) for pv, (topic, schema) in
                pv_details.items()]
            self._issued.update(
                {pv: (topic or self.instpvtopic, schema or self.instpvschema)
                 for pv, (topic, schema) in pv_details.items()})  # update issued
        except KeyError as e:
            self.log.warning(e)
            return
        buff = serialise_rf5k(config_change, streams)
        self.send(self.cmdtopic, buff)

    def pv_forwarding_info(self, pv):
        return self._issued.get(pv, None)

    def reissue(self):
        self.add(self._issued)


class EpicsKafkaForwarder(KafkaStatusHandler):
    """ Monitor the EPICS to Kafka forwarder

    This class is used to monitor the forwarder that forwards EPICS PVs
    to Kafka topics.
    If the `EpicsKafkaForwarderControl` is attached this class can be used to
    control the forwarder as well. See documentation for
    `EpicsKafkaForwarderControl` for further information.
    """

    attached_devices = {
        'forwarder_control': Attach('Forwarder control',
                                    EpicsKafkaForwarderControl, optional=True),
    }

    def doPreinit(self, mode):
        KafkaStatusHandler.doPreinit(self, mode)

    def doInit(self, mode):
        # Dict of PVs issued and actually being forwarded
        self._forwarded = {}
        self._long_loop_delay = self.pollinterval

    @property
    def issued(self):
        """ Provides a set of PVs the NICOS issued. Returns a
        non-empty value only if the forwarder_control is present.
        """
        return (
            self._attached_forwarder_control._issued if
            self._attached_forwarder_control else None)

    @property
    def forwarded(self):
        return self._forwarded

    def _status_update_callback(self, messages):
        """
        Updates the list of the PVs currently forwarded according to the
        `forward-epics-to-kafka`. If forwarder_control is present compares
        with the PVs issued.
        :param messages: A dictionary of {timestamp, StatusMessage},
        where StatusMessage is the named tuple defined in schema x5f2
        (https://github.com/ess-dmsc/streaming-data-types)
        """

        def get_latest_message(message_list):
            gen = (msg for _, msg in sorted(message_list.items(), reverse=True)
                if 'streams' in msg)
            return next(gen, None)

        message = get_latest_message(messages)
        if not message:
            return

        self._set_next_update(message)
        self._forwarded = {stream["channel_name"] for stream in
            message["streams"]}

        if self._attached_forwarder_control:
            self._attached_forwarder_control.status_update(message)
            self._setROParam('curstatus',
                self._attached_forwarder_control.doStatus())
        else:
            self._setROParam('curstatus',
                (status.OK, 'Forwarding..' if self.forwarded else 'idle'), )

    def pv_forwarding_info(self, pv):
        """ Returns the forwarded topic and schema for the given pv.
        Returns a non-empty value only if the forwarder_control is present.
        :param pv: pv name
        :return: (kafka-topic, schema) tuple for the forwarded PV
        """
        if self._attached_forwarder_control:
            return self._attached_forwarder_control.pv_forwarding_info(pv)
        return None

    def pvs_not_forwarding(self):
        """ Provides a set of PVs currently not being forwarded. Returns a
        non-empty value only if the forwarder_control is present.
        """
        if self._attached_forwarder_control:
            return self._attached_forwarder_control._notforwarding
        return None

    def add(self, pv_details):
        """
        Sends a command to the forwarder to add the PVs described in
        `pv_details`. If the forwarder_control is not present does nothing.
        :param pv_details: dictionary with the pvs name as the keys and (
        topic, converter) as values
        """
        if self._attached_forwarder_control:
            self._attached_forwarder_control.add(pv_details)

    @usermethod
    def reissue(self):
        """Reissue all the PVs to the forwarder.
        If the forwarder_control is not present does nothing.
        """
        if self._attached_forwarder_control:
            self._attached_forwarder_control.reissue()

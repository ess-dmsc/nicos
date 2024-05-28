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
#   Nikhil Biyani <nikhil.biyani@psi.ch>
#   Michele Brambilla <michele.brambilla@psi.ch>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
import time

from streaming_data_types.fbschemas.forwarder_config_update_fc00.UpdateType import (
    UpdateType,
)
from streaming_data_types.forwarder_config_update_fc00 import (
    Protocol,
    StreamInfo,
    serialise_fc00,
)

from nicos import session
from nicos.core import (
    status,
    POLLER,
    SIMULATION,
    Param,
)
from nicos.utils import createThread
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler


class EpicsKafkaForwarder(KafkaStatusHandler):
    """Monitor the status of the EPICS to Kafka forwarder"""

    parameters = {
        "config_topic": Param(
            "Kafka topic where configuration messages are written",
            type=str,
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
    }

    _forwarded = {}
    _to_be_forwarded = {}
    _producer = None
    _stop_requested = False

    def doInit(self, mode):
        self._long_loop_delay = self.pollinterval
        self._stop_requested = False
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._producer = KafkaProducer.create(self.brokers)
            self._updater_thread = createThread(
                "forwarder_updater", self._update_forwarded_pvs
            )

    def doShutdown(self):
        KafkaStatusHandler.doShutdown(self)
        self._stop_requested = True

    @property
    def forwarded(self):
        return set(self._forwarded)

    def _get_pvs_to_forward(self):
        to_forward = {}
        for dev in session.devices.values():
            if hasattr(dev, "to_forward"):
                for pv, *settings in dev.to_forward:
                    to_forward[pv] = settings
        return to_forward

    def _generate_forwarder_config(self, pvs):
        streams = []
        for pv, (schema, topic, protocol, periodic) in pvs.items():
            protocol = (
                Protocol.Protocol.CA if protocol == "ca" else Protocol.Protocol.PVA
            )
            streams.append(StreamInfo(pv, schema, topic, protocol, periodic))
        return serialise_fc00(UpdateType.REPLACE, streams)

    def _update_forwarded_pvs(self):
        while not self._stop_requested:
            try:
                to_forward = self._get_pvs_to_forward()
                if to_forward != self._to_be_forwarded:
                    self._to_be_forwarded = to_forward
                    buffer = self._generate_forwarder_config(to_forward)
                    self._producer.produce(self.config_topic, buffer)
            except RuntimeError as err:
                self.log.error(f"could not configure forwarder, {err}")
            time.sleep(0.5)

    def _status_update_callback(self, messages):
        """
        Updates the list of the PVs currently forwarded.

        :param messages: A dictionary of {timestamp, x5f2 status messages}.
        """

        def get_latest_message(message_list):
            gen = (
                msg
                for _, msg in sorted(message_list.items(), reverse=True)
                if "streams" in msg
            )
            return next(gen, None)

        message = get_latest_message(messages)
        if not message:
            return

        self._forwarded = {stream["channel_name"] for stream in message["streams"]}

        status_msg = "Forwarding.." if self._forwarded else "idle"
        self._setROParam("curstatus", (status.OK, status_msg))

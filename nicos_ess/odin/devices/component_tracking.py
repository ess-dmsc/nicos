#  -*- coding: utf-8 -*-
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
#
#   Stefanos Athanasopoulos <stefanos.athanasopoulos@ess.eu>
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************
"""Component Tracking Device."""

from datetime import datetime

from streaming_data_types import deserialise_f144

from nicos.core import SIMULATION, Override, Param, Readable, host, listof

from nicos_ess.devices.kafka.consumer import KafkaConsumer


class ComponentTrackingDevice(Readable):
    """Device for reading the Metrology System data."""

    parameters = {
        "brokers": Param(
            "The kafka address brokers",
            type=listof(host(defaultport=9092)),
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "response_topic": Param(
            "The topic where the metrology system data appear",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "confirmed_components": Param(
            "List of confirmed components",
            type=listof(dict),
            userparam=False,
            settable=True,
            mandatory=False,
        ),
        "valid_components": Param(
            "List of valid component names",
            type=listof(str),
            userparam=False,
            settable=True,
            mandatory=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }

    _consumer = None
    _unconfirmed_components = []
    _last_confirm_timestamp = None
    _last_scan_timestamp = None

    def doPreinit(self, mode):
        if mode != SIMULATION:
            self._consumer = KafkaConsumer.create(self.brokers)
            self._consumer.subscribe(self.response_topic)
        else:
            self._consumer = None

        # Settings for thread to fetch new message
        self._stoprequest = True
        self._updater_thread = None

    def read_metrology_system_messages(self):
        messages = {}
        validity = {}

        self._consumer.set_all_to_offset(offset_from_end=1)

        msg = self._consumer.poll(1000)
        if msg is None:
            self.log.warning("No messages received from Kafka")
            return {}
        elif msg.value():
            name, values = self._process_kafka_message(msg.value())
            if not name:
                self.log.warning("Invalid message received from Kafka")
                return {}
            messages[name] = values
            if name.endswith(":valid"):
                validity[name.split(":")[0]] = values["value"] == 1

        components_data = self._extract_components(list(messages.values()))

        for component in components_data:
            if component["valid"] == 1:
                component["distance_from_sample"] = round(component["z"], 3)
            else:
                component["distance_from_sample"] = "Not detected"
        self._update_unconfirmed_components(components_data)

        return self._unconfirmed_components

    def _update_unconfirmed_components(self, new_components):
        temp = []
        for new_component in new_components:
            for component in self._unconfirmed_components:
                if component["component_name"] == new_component["component_name"]:
                    new_component["confirmed_distance_from_sample"] = component.get(
                        "confirmed_distance_from_sample"
                    )
            temp.append(new_component)
        self._unconfirmed_components = temp
        self._last_scan_timestamp = datetime.now()

    def _extract_components(self, data):
        components = {}
        for entry in data:
            component_name, component_value = entry["name"].split(":")
            current_component = components.get(component_name, {})
            current_component[component_value] = entry["value"]
            components[component_name] = current_component

        full_component_data = []
        for name, details in components.items():
            details["component_name"] = name
            full_component_data.append(details)
        return full_component_data

    def _process_kafka_message(self, msg):
        if msg[4:8] != b"f144":
            return None, None
        log_data = deserialise_f144(msg)
        source_name = log_data.source_name
        value = log_data.value
        timestamp = log_data.timestamp_unix_ns
        return source_name, {
            "name": source_name,
            "value": value,
            "timestamp": timestamp,
        }

    def confirm_components(self):
        self.valid_components = [
            value["component_name"]
            for value in self._unconfirmed_components
            if value["valid"]
        ]
        to_be_confirmed = list(self._unconfirmed_components)
        for component in to_be_confirmed:
            component["confirmed_distance_from_sample"] = component[
                "distance_from_sample"
            ]
        self._unconfirmed_components = to_be_confirmed
        self.confirmed_components = to_be_confirmed
        self._last_confirm_timestamp = datetime.now()
        return self.confirmed_components

    def get_confirmed_timestamp(self):
        return self._last_confirm_timestamp

    def get_scan_timestamp(self):
        return self._last_scan_timestamp

"""Component Tracking Device."""

from datetime import datetime, timedelta

from streaming_data_types import deserialise_f144

from nicos.core import (
    SIMULATION,
    Override,
    Param,
    Readable,
    host,
    listof,
    status,
    tupleof,
)

from nicos_ess.devices.kafka.consumer import KafkaConsumer
from nicos_ess.utilities.json_utils import generate_nxlog_json


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
        "gollum_data": Param(
            "Dictionary of Gollum data",
            type=dict,
            userparam=True,
            settable=True,
            mandatory=False,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
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
            self._consumer.subscribe([self.response_topic])
            self._setROParam("curstatus", (status.OK, ""))
        else:
            self._consumer = None

        # Settings for thread to fetch new message
        self._stoprequest = True
        self._updater_thread = None

    def read_metrology_system_messages(self):
        current_time = datetime.now()
        messages = {}
        validity = {}

        self._consumer.seek_to_end()

        while True:
            if datetime.now() > current_time + timedelta(seconds=1):
                break
            msg = self._consumer.poll()
            if msg is None:
                continue
            elif msg.value():
                name, values = self._process_kafka_message(msg.value())
                if not name:
                    continue
                messages[name] = values
                if name.endswith(":valid"):
                    validity[name.split(":")[0]] = values["value"] == 1
        if not messages:
            self._setROParam(
                "curstatus", (status.WARN, "Could not retrieve messages from Kafka.")
            )
            return {}

        self.gollum_data = messages
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
        self._setROParam("curstatus", (status.OK, ""))

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

    def _generate_json_configs_groups(self):
        groups = {}
        for source_name in self.gollum_data:
            group_name, log_name = source_name.split(":")
            if log_name == "valid":
                continue

            if group_name not in groups:
                groups[group_name] = {"nx_class": "NXcollection", "children": []}

            unit = ""
            if log_name in ("x", "y", "z"):
                unit = "mm"
            elif log_name in ("alpha", "beta", "gamma"):
                unit = "deg"

            nxlog_json = generate_nxlog_json(
                log_name, "f144", source_name, self.response_topic, unit
            )
            groups[group_name]["children"].append(nxlog_json)

        return groups

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        return self.curstatus

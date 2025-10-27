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
    POLLER,
    SIMULATION,
    Param,
    status,
)
from nicos.utils import createThread
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler
from nicos_ess.utilities.json_utils import (
    build_json,
    generate_dataset_json,
    generate_group_json,
    generate_nxlog_json,
)


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
        """
        Get the set of currently forwarded PVs.

        :return: A set of forwarded PVs.
        """
        return set(self._forwarded)

    def get_nexus_json(self):
        """
        Get the Nexus JSON configuration.

        :return: A list of JSON configurations to be treated as a "children" list.
        """
        return self._generate_json_configs()

    def get_component_nexus_json(self):
        children = build_json(
            session.devices["component_tracking"]._generate_json_configs_groups()
        )
        return generate_group_json("component_tracker", "NXcollection", children)

    def _get_forwarder_config(self, dev):
        for nexus_config_dict in dev.nexus_config:
            yield (
                nexus_config_dict.get("source_name", ""),
                nexus_config_dict.get("schema", ""),
                nexus_config_dict.get("topic", ""),
                nexus_config_dict.get("protocol", ""),
                nexus_config_dict.get("periodic", 0),
            )

    def _get_pvs_to_forward(self):
        # devices = session.devices.values()
        # for dev in devices:
        #     if hasattr(dev, "nexus_config"):
        #         print(self._get_forwarder_config(dev))

        return {
            pv: (schema, topic, protocol, periodic)
            for dev in session.devices.values()
            if hasattr(dev, "nexus_config")
            for pv, schema, topic, protocol, periodic in self._get_forwarder_config(dev)
        }

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
                # print("1", to_forward)
                if to_forward != self._to_be_forwarded:
                    # print("2", to_forward)
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

    def _get_json_config(self, dev):
        for nexus_config_dict in dev.nexus_config:
            group_name = nexus_config_dict.get("group_name", "")
            nx_class = nexus_config_dict.get("nx_class", "")
            dataset_type = nexus_config_dict.get(
                "dataset_type", "nxlog"
            )  # default nxlog to keep backwards compatibility for now
            if group_name and nx_class:
                if dataset_type == "nxlog":
                    yield self._handle_nxlog(
                        nexus_config_dict, dev, group_name, nx_class
                    )
                elif dataset_type == "static_read":
                    yield self._handle_static_read(
                        nexus_config_dict, dev, group_name, nx_class
                    )
                elif dataset_type == "static_value":
                    yield self._handle_static_value(
                        nexus_config_dict, dev, group_name, nx_class
                    )

    def _handle_nxlog(self, config, dev, group_name, nx_class):
        dev_name = dev.name
        suffix = config.get("suffix", "")
        if suffix:
            dev_name = f"{dev_name}_{suffix}"
        return (
            dev_name,
            {
                "group_name": group_name,
                "nx_class": nx_class,
                "units": config.get("units", ""),
                "pv": config.get("source_name", ""),
                "schema": config.get("schema", ""),
                "topic": config.get("topic", ""),
                "dataset_type": config.get("dataset_type", "nxlog"),
            },
        )

    def _handle_static_read(self, config, dev, group_name, nx_class):
        dev_name = dev.name
        current_value = dev.read(0)
        suffix = config.get("suffix", "")
        if suffix:
            dev_name = f"{dev_name}_{suffix}"
        return (
            dev_name,
            {
                "group_name": group_name,
                "nx_class": nx_class,
                "units": config.get("units", ""),
                "value": current_value,
                "dataset_type": config.get("dataset_type", "static_read"),
            },
        )

    def _handle_static_value(self, config, dev, group_name, nx_class):
        dev_name = dev.name
        suffix = config.get("suffix", "")
        if suffix:
            dev_name = f"{dev_name}_{suffix}"
        return (
            dev_name,
            {
                "group_name": group_name,
                "nx_class": nx_class,
                "units": config.get("units", ""),
                "value": config.get("value", ""),
                "dataset_type": config.get("dataset_type", "static_value"),
            },
        )

    def _get_configs_for_json(self):
        return {
            dev_name: config
            for dev in session.devices.values()
            if hasattr(dev, "nexus_config")
            for dev_name, config in self._get_json_config(dev)
        }

    def _generate_json_configs(self):
        dev_configs = self._get_configs_for_json()
        groups = {}

        for dev_name, config in dev_configs.items():
            group_name = config["group_name"]
            if group_name not in groups:
                groups[group_name] = {"nx_class": config["nx_class"], "children": []}

            if config["dataset_type"] == "nxlog":
                json_snippet = generate_nxlog_json(
                    dev_name,
                    config["schema"],
                    config["pv"],
                    config["topic"],
                    config["units"],
                )
            elif config["dataset_type"] in ["static_read", "static_value"]:
                json_snippet = generate_dataset_json(
                    dev_name,
                    config["value"],
                    config["units"],
                )
                print(json_snippet)
            else:
                continue

            groups[group_name]["children"].append(json_snippet)
        return build_json(groups)

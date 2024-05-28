description = "Monitors the status of the Forwarder"

devices = dict(
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors and configures the Forwarder",
        statustopic="ymir_forwarder_dynamic_status",
        config_topic="ymir_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)

description = "Monitors the status of the Forwarder"

devices = dict(
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["nido_forwarder_dynamic_status"],
        config_topic="nido_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)

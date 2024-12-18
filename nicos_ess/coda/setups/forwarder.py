description = "Monitors the status of the Forwarder"

devices = dict(
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic=["coda_forwarder_dynamic_status"],
        config_topic="coda_forwarder_dynamic_config",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)

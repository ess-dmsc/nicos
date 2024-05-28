description = "Monitors the status of the Forwarder"

devices = dict(
    KafkaForwarder=device(
        "nicos_ess.devices.forwarder.EpicsKafkaForwarder",
        description="Monitors the status of the Forwarder",
        statustopic="ymir_forwarder_status",
        brokers=configdata("config.KAFKA_BROKERS"),
    ),
)

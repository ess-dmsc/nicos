# ruff: noqa: F821
description = "Shared Kafka readback consumer"

group = "lowlevel"

devices = dict(
    KafkaReadbacks=device(
        "nicos_ess.devices.kafka.readback.KafkaReadbackConsumer",
        description="Shared Kafka consumer for readback values",
        brokers=configdata("config.KAFKA_BROKERS"),
        topics=["tn_data_general"],
        visibility=(),
    ),
)

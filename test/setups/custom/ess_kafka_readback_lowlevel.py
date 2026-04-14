# ruff: noqa: F821
description = "Shared Kafka readback consumer for smoke tests"

group = "lowlevel"

devices = dict(
    KafkaReadbacks=device(
        "nicos_ess.devices.kafka.readback.KafkaReadbackConsumer",
        description="Shared Kafka consumer for smoke tests",
        brokers=["localhost:9092"],
        topics=["topic1", "topic2", "topic3"],
        visibility=(),
    ),
)

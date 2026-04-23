# ruff: noqa: F821
description = "Shared Kafka readback router for smoke tests"

group = "lowlevel"

devices = dict(
    KafkaReadbacks=device(
        "nicos_ess.devices.kafka.readback.KafkaReadbackRouter",
        description="Routes Kafka readback updates for smoke tests",
        brokers=["localhost:9092"],
        topics=["topic1", "topic2", "topic3"],
        visibility=(),
    ),
)

# ruff: noqa: F821
description = "Shared Kafka readback router"

group = "lowlevel"

devices = dict(
    KafkaReadbacks=device(
        "nicos_ess.devices.kafka.readback.KafkaReadbackRouter",
        description="Routes Kafka readback updates to KafkaReadable devices",
        brokers=configdata("config.KAFKA_BROKERS"),
        topics=["ymir_motion"],
        visibility=(),
    ),
)

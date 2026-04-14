# ruff: noqa: F821
description = "First Kafka readback smoke test device"

includes = ["ess_kafka_readback_lowlevel"]

devices = dict(
    FirstKafkaReadable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="First Kafka readback smoke test device",
        kafka="KafkaReadbacks",
        topic="readbacks",
        source_name="src:first",
        unit="mm",
    ),
)

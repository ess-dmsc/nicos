# ruff: noqa: F821
description = "Second Kafka readback smoke test device"

includes = ["ess_kafka_readback_lowlevel"]

devices = dict(
    SecondKafkaReadable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Second Kafka readback smoke test device",
        kafka="KafkaReadbacks",
        topic="readbacks",
        source_name="src:second",
        unit="mm",
    ),
)

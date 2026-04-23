# ruff: noqa: F821
description = "First Kafka readback smoke test setup"

includes = ["ess_kafka_readback_lowlevel"]

devices = dict(
    FirstTopic1Readable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="First smoke test readback on topic1",
        kafka="KafkaReadbacks",
        topic="topic1",
        source_name="src:first:topic1",
        unit="mm",
    ),
    FirstTopic2Readable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="First smoke test readback on topic2",
        kafka="KafkaReadbacks",
        topic="topic2",
        source_name="src:first:topic2",
        unit="mm",
    ),
)

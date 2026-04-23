# ruff: noqa: F821
description = "Second Kafka readback smoke test setup"

includes = ["ess_kafka_readback_lowlevel"]

devices = dict(
    SecondTopic1Readable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Second smoke test readback on topic1",
        kafka="KafkaReadbacks",
        topic="topic1",
        source_name="src:second:topic1",
        unit="mm",
    ),
    SecondTopic3Readable=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Second smoke test readback on topic3",
        kafka="KafkaReadbacks",
        topic="topic3",
        source_name="src:second:topic3",
        unit="mm",
    ),
)

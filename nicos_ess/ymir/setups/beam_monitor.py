# ruff: noqa: F821

description = "The dream beam monitor stream"

devices = dict(
    dream_beam_monitor=device(
        "nicos_ess.devices.kafka.kafka_readable.Da00Readable",
        description="Kafka reader for beam monitor data",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic="dream_beam_monitor",
        source_name="",
    ),
)

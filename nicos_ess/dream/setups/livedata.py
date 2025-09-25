# ruff: noqa: F821
description = "Live data reduction."

KAFKA_BROKERS_YMIR = [
    "10.100.4.15:8093",
    "10.100.4.17:8093",
    "10.100.5.29:8093",
]

devices = dict(
    livedata=device(
        "nicos_ess.devices.kafka.kafka_readable.Da00Readable",
        description="The DRAM live data reduction.",
        brokers=KAFKA_BROKERS_YMIR,  # configdata("config.KAFKA_BROKERS"),
        topic=["dream_livedata_data"],
        source_name="some_source",
    ),
)

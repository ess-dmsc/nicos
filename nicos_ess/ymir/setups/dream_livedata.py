# ruff: noqa: F821
description = "Live data reduction."

devices = dict(
    dream_livedata=device(
        "nicos_ess.devices.kafka.kafka_readable.Da00Readable",
        description="The DRAM live data reduction.",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic=["dream_livedata_data"],
        source_name="some_source",
    ),
)

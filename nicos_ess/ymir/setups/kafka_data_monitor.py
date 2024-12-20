description = "A little device to read f144 data from a kafka topic"

devices = dict(
    f144_motor=device(
        "nicos_ess.devices.kafka.kafka_readable.F144Readable",
        description="Readback of a f144 motor",
        brokers=configdata("config.KAFKA_BROKERS"),
        topic=["ymir_motion"],
        source_name="YMIR-BmScn:MC-LinY-01:Mtr",
        unit="mm",
    ),
)

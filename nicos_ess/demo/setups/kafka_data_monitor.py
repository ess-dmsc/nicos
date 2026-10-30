description = "A little device to read f144 data from a kafka topic"

includes = ["kafka_readbacks"]

devices = dict(
    f144_motor=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Readback of a f144 motor",
        kafka="KafkaReadbacks",
        topic="demo_motion",
        source_name="DEMO-BmScn:MC-LinY-01:Mtr.RBV",
        unit="mm",
    ),
)

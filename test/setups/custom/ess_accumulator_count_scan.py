# Minimal accumulator setup used by command tests.

includes = ["ess_count_scan_common"]

devices = dict(
    KafkaReadbacks=device(
        "nicos_ess.devices.kafka.readback.KafkaReadbackRouter",
        description="Kafka readback router",
        brokers=["localhost:9092"],
        topics=["readbacks"],
    ),
    proton_acc=device(
        "nicos_ess.devices.kafka.readback.KafkaAccumulatorChannel",
        description="Accumulated proton charge",
        kafka="KafkaReadbacks",
        topic="readbacks",
        source_name="pulse_source",
        type="monitor",
        unit="uC",
        fmtstr="%.3f",
    ),
    detector=device(
        "nicos.devices.generic.Detector",
        description="Detector with accumulated proton charge monitor",
        timers=["timer"],
        monitors=["proton_acc"],
    ),
)

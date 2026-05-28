# ruff: noqa: F821
description = "Generic detector with proton charge monitor"

group = "optional"

includes = ["kafka_readbacks"]

TOPIC = "tn_data_general"

devices = dict(
    proton_charge=device(
        "nicos_ess.devices.kafka.readback.KafkaAccumulatorChannel",
        description="Accumulated HEBT proton charge",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="HEBT-160LWU:PBI-BCM-001:PulseChargeR",
        type="monitor",
        unit="uC",
        fmtstr="%.3f",
    ),
    detector=device(
        "nicos.devices.generic.Detector",
        description="Generic detector with proton charge monitor",
        monitors=["proton_charge"],
    ),
)

startupcode = """
SetDetectors(detector)
"""

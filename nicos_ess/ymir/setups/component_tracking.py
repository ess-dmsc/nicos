# ruff: noqa: F821
description = "ODIN Component Tracking System"

group = "optional"

devices = dict(
    component_tracking=device(
        "nicos_ess.odin.devices.component_tracking.ComponentTrackingDevice",
        description="The component tracking system of ODIN",
        brokers=configdata("config.KAFKA_BROKERS"),
        response_topic="ymir_metrology",
    ),
)

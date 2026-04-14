# ruff: noqa: F821
description = "Accelerator and moderator information read back from Kafka"

group = "optional"

includes = ["kafka_readbacks"]

TOPIC = "tn_data_general"

devices = dict(
    a2t_pulse_charge=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Accelerator to target pulse charge",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="A2T-130LWU:PBI-BCM-001:PulseChargeR",
        unit="uC",
    ),
    a2t_flat_top_current=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Accelerator to target flat top current",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="A2T-130LWU:PBI-BCM-001:FlatTopCurrentR",
        unit="uA",
    ),
    a2t_pulse_width=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Accelerator to target pulse width",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="A2T-130LWU:PBI-BCM-001:PulseWidthR",
        unit="us",
    ),
    hebt_pulse_charge=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="HEBT pulse charge",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="HEBT-160LWU:PBI-BCM-001:PulseChargeR",
        unit="uC",
    ),
    cms_active_state=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="CMS active state machine status",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:SC-FSM-007x:STS_Active",
        unit="",
    ),
    upper_moderator_1_temperature=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Upper moderator 1 temperature",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:Cryo-TT-82025:MeasValue",
        unit="K",
    ),
    upper_moderator_2_temperature=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Upper moderator 2 temperature",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:Cryo-TT-82027:MeasValue",
        unit="K",
    ),
    lower_moderator_1_temperature=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Lower moderator 1 temperature",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:Cryo-TT-82029:MeasValue",
        unit="K",
    ),
    lower_moderator_2_temperature=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="Lower moderator 2 temperature",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:Cryo-TT-82031:MeasValue",
        unit="K",
    ),
    cms_common_pid_temperature=device(
        "nicos_ess.devices.kafka.readback.KafkaReadable",
        description="CMS common PID temperature",
        kafka="KafkaReadbacks",
        topic=TOPIC,
        source_name="CrS-CMS:Cryo-TT-82033:MeasValue",
        unit="K",
    ),
)

# ruff: noqa: F821
description = "The area detector for YMIR"

devices = dict(
    orca_kafka_plugin=device(
        "nicos_ess.devices.epics.area_detector.ADKafkaPlugin",
        description="The configuration of the Kafka plugin for the Orca camera.",
        kafkapv="YMIR-Det1:Kfk1:",
        brokerpv="KafkaBrokerAddress_RBV",
        topicpv="KafkaTopic_RBV",
        sourcepv="SourceName_RBV",
        visibility=(),
    ),
    orca_camera=device(
        "nicos_ess.devices.epics.area_detector.AreaDetector",
        description="The light tomography Orca camera.",
        pv_root="YMIR-Det1:cam1:",
        ad_kafka_plugin="orca_kafka_plugin",
        image_topic="ymir_camera",
        unit="images",
        brokers=configdata("config.KAFKA_BROKERS"),
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    orca_image_type=device(
        "nicos_ess.devices.epics.area_detector.ImageType",
        description="Image type for the tomography setup.",
    ),
    area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["orca_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(area_detector_collector)
"""

# ruff: noqa: F821
description = "The area detector for YMIR"

devices = dict(
    orca_camera=device(
        "nicos_ess.devices.epics.area_detector.AreaDetector",
        description="The light tomography Orca camera.",
        pv_root="YMIR-Det1:cam1:",
        image_pv="YMIR-Det1:image1:ArrayData",
        ad_kafka_plugin="orca_kafka_plugin",
        topicpv="YMIR-Det1:Kfk1:KafkaTopic_RBV",
        sourcepv="YMIR-Det1:Kfk1:SourceName_RBV",
        unit="images",
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

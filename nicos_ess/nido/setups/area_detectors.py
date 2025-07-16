description = "The area detector for NIDO"

camera_system_pv_root = "Orca:"
camera_device_pv_root = ""
camera_ndplugin_pv_root = "image1:"
camera_kafkaplugin_pv_root = "Kfk1:"
water_cooler_pv_root = ""

devices = dict(
    orca_camera=device(
        "nicos_ess.devices.epics.area_detector.OrcaFlash4",
        description="The light tomography Orca camera.",
        pv_root=f"{camera_system_pv_root}{camera_device_pv_root}",
        image_pv=f"{camera_system_pv_root}{camera_ndplugin_pv_root}ArrayData",
        ad_kafka_plugin="orca_kafka_plugin",
        topicpv=f"{camera_system_pv_root}{camera_kafkaplugin_pv_root}KafkaTopic_RBV",
        sourcepv=f"{camera_system_pv_root}{camera_kafkaplugin_pv_root}SourceName_RBV",
        unit="images",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        watercooler_mode="watercooler_mode",
        watercooler_temperature="watercooler_temperature",
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

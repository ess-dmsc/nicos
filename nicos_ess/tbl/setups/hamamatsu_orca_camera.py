# ruff: noqa: F821

description = "TBL Hamamatsu Orca camera"

camera_system_pv_root = "TBL-DtCMOS:"
camera_device_pv_root = "NDet-OrcF43:"
camera_ndplugin_pv_root = "image1:"
camera_kafkaplugin_pv_root = "Kfk1:"
water_cooler_pv_root = "TBL-DtCMOS:NDet-FTCtrl-001:"

devices = dict(
    watercooler_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The water cooler mode.",
        readpv=f"{water_cooler_pv_root}Mode-R",
        writepv=f"{water_cooler_pv_root}Mode-S",
        visibility=(),
    ),
    watercooler_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The water cooler temperature.",
        readpv=f"{water_cooler_pv_root}Temperature-R",
        writepv=f"{water_cooler_pv_root}TemperatureSP0-S",
        targetpv=f"{water_cooler_pv_root}TemperatureSP0-R",
        visibility=(),
    ),
    orca_sharpness=device(
        "nicos_ess.devices.virtual.area_detector.SharpnessChannel",
        description="Sharpness post processing channel for the area detector.",
    ),
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
    orca_chip_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="CMOS chip temperature",
        readpv=f"{camera_system_pv_root}{camera_device_pv_root}Temperature-R",
    ),
    orca_image_type=device(
        "nicos_ess.devices.epics.area_detector.ImageType",
        description="Image type for the tomography setup.",
    ),
    orca_area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["orca_camera"],
        others=["orca_sharpness"],
        postprocess=[("orca_sharpness", "orca_camera")],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

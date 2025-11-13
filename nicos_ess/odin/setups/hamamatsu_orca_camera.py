# ruff: noqa: F821

description = "ODIN Hamamatsu Orca camera"

camera_system_pv_root = "ODIN-DtCMOS:"
camera_device_pv_root = "NDet-OrcF43:"
camera_ndplugin_pv_root = "image1:"
camera_kafkaplugin_pv_root = "Kfk1:"
camera_schemasplugin_pv_root = "Schema:"
water_cooler_pv_root = "ODIN-DtCMOS:NDet-FTCtrl-001:"

devices = dict(
    # watercooler_mode=device(
    #     "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
    #     description="The water cooler mode.",
    #     readpv=f"{water_cooler_pv_root}Mode-R",
    #     writepv=f"{water_cooler_pv_root}Mode-S",
    #     visibility=(),
    # ),
    # watercooler_temperature=device(
    #     "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
    #     description="The water cooler temperature.",
    #     readpv=f"{water_cooler_pv_root}Temperature-R",
    #     writepv=f"{water_cooler_pv_root}TemperatureSP0-S",
    #     targetpv=f"{water_cooler_pv_root}TemperatureSP0-R",
    #     visibility=(),
    # ),
    orca_camera=device(
        "nicos_ess.devices.epics.area_detector.OrcaFlash4",
        description="The light tomography Orca camera.",
        pv_root=f"{camera_system_pv_root}{camera_device_pv_root}",
        image_pv=f"{camera_system_pv_root}{camera_ndplugin_pv_root}ArrayData",
        ad_kafka_plugin="orca_kafka_plugin",
        topicpv=f"{camera_system_pv_root}{camera_kafkaplugin_pv_root}KafkaTopic_RBV",
        sourcepv=f"{camera_system_pv_root}{camera_schemasplugin_pv_root}SourceName_RBV",
        unit="images",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        # watercooler_mode="watercooler_mode", # wait for the julabo
        # watercooler_temperature="watercooler_temperature", # wait for the julabo
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
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

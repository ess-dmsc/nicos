# ruff: noqa: F821

description = "TBL Hamamatsu Orca camera"

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
    orca_camera=device(
        "nicos_ess.devices.epics.area_detector.OrcaFlash4",
        description="The light tomography Orca camera.",
        pv_root="TBL-DtCMOS:NDet-OrcF43:",
        image_pv="TBL-DtCMOS:image1:ArrayData",
        ad_kafka_plugin="orca_kafka_plugin",
        topicpv="TBL-DtCMOS:Kfk1:KafkaTopic_RBV",
        sourcepv="TBL-DtCMOS:Kfk1:SourceName_RBV",
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
    orca_area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["orca_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

description = "The area detector for NIDO"

camera_system_pv_root = "Orca:"
camera_device_pv_root = ""
camera_ndplugin_pv_root = "image1:"
water_cooler_pv_root = ""

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
        "nicos_ess.devices.epics.adcore.OrcaFlash4",
        description="The light tomography Orca camera.",
        pv_root=f"{camera_system_pv_root}{camera_device_pv_root}",
        image_pv_root=f"{camera_system_pv_root}{camera_ndplugin_pv_root}",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        watercooler="watercooler_mode",
    ),
    orca_image_type=device(
        "nicos_ess.devices.image_type.ImageType",
        description="Image type for the tomography setup.",
    ),
    orca_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer of the camera collector, for counts with a time preset",
        fmtstr="%.2f",
        unit="s",
        visibility=(),
    ),
    area_detector_collector=device(
        "nicos.devices.generic.Detector",
        description="Area detector collector",
        images=["orca_camera"],
        timers=["orca_timer"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(area_detector_collector)
"""

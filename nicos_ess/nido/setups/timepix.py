description = "The timepix in NIDO"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorBase",
        description="TimePix3 detector.",
        pv_root="Tpx3:cam1:",
        image_pv="Tpx3:image1:ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["timepix"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(area_detector_collector)
"""

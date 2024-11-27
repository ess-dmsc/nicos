description = "The NGEM detector"

devices = dict(
    ngem=device(
        "nicos_ess.devices.epics.area_detector.NGemDetector",
        description="The ngem.",
        pv_root="TBL-Det1:cam1:",
        image_pv="TBL-Det1:image1:ArrayData",
        counter_pv="TBL-Det1:cam1:ArrayCounter",
        unit="images",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["ngem"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(area_detector_collector)
"""

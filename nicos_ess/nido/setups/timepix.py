description = "The timepix in NIDO"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.area_detector.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="Tpx3:cam1:",
        image_pv="Tpx3:image1:ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="Tpx3:cam1:PelEvtRate_RBV",
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

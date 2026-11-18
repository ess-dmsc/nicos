description = "The timepix in NIDO"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.adcore.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="LabS-ECDC:NDet-TPX3-001:cam1:",
        image_pv_root="LabS-ECDC:NDet-TPX3-001:image1:",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="LabS-ECDC:NDet-TPX3-001:cam1:PelEvtRate_RBV",
    ),
    timepix_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer of the camera collector, for counts with a time preset",
        fmtstr="%.2f",
        unit="s",
        visibility=(),
    ),
    timepix_area_detector_collector=device(
        "nicos.devices.generic.Detector",
        description="Area detector collector",
        images=["timepix"],
        timers=["timepix_timer"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(timepix_area_detector_collector)
"""

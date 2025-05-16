description = "The timepix in NIDO"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.area_detector.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="TBL-DtTPX:NDet-TPX3-001:cam1:",
        image_pv="TBL-DtTPX:NDet-TPX3-001:image1:ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="TBL-DtTPX:NDet-TPX3-001:cam1:PelEvtRate_RBV",
    ),
    timepix_area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["timepix"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
    photonis_intensifier_gain=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Photonis intensifier gain",
        readpv="TBL-DtTPX:NDet-ImgInt-001:AO0",
        writepv="TBL-DtTPX:NDet-ImgInt-001:AO0Set",
        abslimits=(0, 10),
    ),
)

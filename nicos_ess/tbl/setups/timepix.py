description = "The timepix in TBL"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.area_detector.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="TBL-DtTPX:NDet-TPX3-001:Cam1_",
        image_pv="TBL-DtTPX:NDet-TPX3-001:Img1_ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="TBL-DtTPX:NDet-TPX3-001:Cam1_PelEvtRate_RBV",
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
    photonis_intensifier_bias=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Photonis intensifier bias voltage",
        readpv="TBL-DtTPX:NDet-ImgInt-001:AO1",
        writepv="TBL-DtTPX:NDet-ImgInt-001:AO1Set",
        abslimits=(0, 10),
    ),
)

description = "The timepix in ODIN"

devices = dict(
    timepix=device(
        "nicos_ess.devices.epics.area_detector.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="ODIN-DtTPX:NDet-TPX3-001:cam1:",
        image_pv="ODIN-DtTPX:NDet-TPX3-001:image1:ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="ODIN-DtTPX:NDet-TPX3-001:cam1:PelEvtRate_RBV",
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
        readpv="ODIN-DtTPX:NDet-ImgInt-001:AO0",
        writepv="ODIN-DtTPX:NDet-ImgInt-001:AO0Set",
        abslimits=(0, 10),
    ),
    photonis_intensifier_bias=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Photonis intensifier bias voltage",
        readpv="ODIN-DtTPX:NDet-ImgInt-001:AO1",
        writepv="ODIN-DtTPX:NDet-ImgInt-001:AO1Set",
        abslimits=(0, 10),
    ),
    temp_led_on_dly=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Timepix LED on delay",
        readpv="ODIN-DtCmn:Ctrl-EVR-001:DlyGen3Delay-SP",
        writepv="ODIN-DtCmn:Ctrl-EVR-001:DlyGen3Delay-SP",
        abslimits=(0, 70000),
    ),
    temp_led_off_dly=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Timepix LED off delay",
        readpv="ODIN-DtCmn:Ctrl-EVR-001:DlyGen4Delay-SP",
        writepv="ODIN-DtCmn:Ctrl-EVR-001:DlyGen4Delay-SP",
        abslimits=(0, 70000),
    ),
)

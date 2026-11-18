description = "The timepix in TBL"

devices = dict(
    timepix3_camera=device(
        "nicos_ess.devices.epics.adcore.TimepixDetector",
        description="TimePix3 detector.",
        pv_root="TBL-DtTPX:NDet-TPX3-001:cam1:",
        image_pv_root="TBL-DtTPX:NDet-TPX3-001:image1:",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    timepix_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="TimePix3 photon event counter",
        readpv="TBL-DtTPX:NDet-TPX3-001:cam1:PelEvtRate_RBV",
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
        description="Timepix area detector collector",
        images=["timepix3_camera"],
        timers=["timepix_timer"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
    photonis_intensifier_gain=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Photonis intensifier gain",
        readpv="TBL-DtTPX:NDet-ImgInt-001:AO0",
        writepv="TBL-DtTPX:NDet-ImgInt-001:AO0Set",
        userlimits=(0, 10),
        precision=0.01,  # DAC readback: 4.9996 for 5.0
    ),
    photonis_intensifier_bias=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Photonis intensifier bias voltage",
        readpv="TBL-DtTPX:NDet-ImgInt-001:AO1",
        writepv="TBL-DtTPX:NDet-ImgInt-001:AO1Set",
        userlimits=(0, 10),
        precision=0.01,  # DAC readback: 4.9996 for 5.0
    ),
)

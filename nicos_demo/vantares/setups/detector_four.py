description = "ZWO camera emulation (4 cams)"
group = "lowlevel"

sysconfig = dict(
    datasinks=["ImageSaver1", "ImageSaver2", "ImageSaver3", "ImageSaver4"],
)

devices = dict(
    timer_zwo=device(
        "nicos.devices.generic.VirtualTimer",
        description="The camera's internal timer",
        visibility=(),
    ),
    zwo1=device(
        "nicos.devices.generic.VirtualImage",
        description="Camera 1",
        fmtstr="%d",
        size=(1024, 1024),
        visibility=(),
    ),
    zwo2=device(
        "nicos.devices.generic.VirtualImage",
        description="Camera 1",
        fmtstr="%d",
        size=(1024, 1024),
        visibility=(),
    ),
    zwo3=device(
        "nicos.devices.generic.VirtualImage",
        description="Camera 1",
        fmtstr="%d",
        size=(1024, 1024),
        visibility=(),
    ),
    zwo4=device(
        "nicos.devices.generic.VirtualImage",
        description="Camera 1",
        fmtstr="%d",
        size=(1024, 1024),
        visibility=(),
    ),
    temp_zwo1=device(
        "nicos.devices.generic.VirtualTemperature",
        description="The CMOS chip temperature camera 1",
        abslimits=(-100, 0),
        warnlimits=(None, 0),
        speed=6,
        unit="degC",
        maxage=5,
        fmtstr="%.0f",
    ),
    temp_zwo2=device(
        "nicos.devices.generic.VirtualTemperature",
        description="The CMOS chip temperature camera 2",
        abslimits=(-100, 0),
        warnlimits=(None, 0),
        speed=6,
        unit="degC",
        maxage=5,
        fmtstr="%.0f",
    ),
    temp_zwo3=device(
        "nicos.devices.generic.VirtualTemperature",
        description="The CMOS chip temperature camera 3",
        abslimits=(-100, 0),
        warnlimits=(None, 0),
        speed=6,
        unit="degC",
        maxage=5,
        fmtstr="%.0f",
    ),
    temp_zwo4=device(
        "nicos.devices.generic.VirtualTemperature",
        description="The CMOS chip temperature camera 4",
        abslimits=(-100, 0),
        warnlimits=(None, 0),
        speed=6,
        unit="degC",
        maxage=5,
        fmtstr="%.0f",
    ),
    det_zwo1=device(
        "nicos.devices.generic.Detector",
        description="The ZWO camera 1 detector",
        images=["zwo1"],
        timers=["timer_zwo"],
    ),
    det_zwo2=device(
        "nicos.devices.generic.Detector",
        description="The ZWO camera 1 detector",
        images=["zwo2"],
        timers=["timer_zwo"],
    ),
    det_zwo3=device(
        "nicos.devices.generic.Detector",
        description="The ZWO camera 1 detector",
        images=["zwo3"],
        timers=["timer_zwo"],
    ),
    det_zwo4=device(
        "nicos.devices.generic.Detector",
        description="The ZWO camera 1 detector",
        images=["zwo4"],
        timers=["timer_zwo"],
    ),
    ImageSaver1=device(
        "nicos.devices.datasinks.FITSImageSink",
        description="Saves image data in FITS format",
        filenametemplate=["1_%(pointcounter)08d.fits"],
        subdir="cam1",
        detectors=["det_zwo1"],
    ),
    ImageSaver2=device(
        "nicos.devices.datasinks.FITSImageSink",
        description="Saves image data in FITS format",
        filenametemplate=["2_%(pointcounter)08d.fits"],
        subdir="cam2",
        detectors=["det_zwo2"],
    ),
    ImageSaver3=device(
        "nicos.devices.datasinks.FITSImageSink",
        description="Saves image data in FITS format",
        filenametemplate=["3_%(pointcounter)08d.fits"],
        subdir="cam3",
        detectors=["det_zwo3"],
    ),
    ImageSaver4=device(
        "nicos.devices.datasinks.FITSImageSink",
        description="Saves image data in FITS format",
        filenametemplate=["4_%(pointcounter)08d.fits"],
        subdir="cam4",
        detectors=["det_zwo4"],
    ),
)

startupcode = """
SetDetectors(det_zwo1, det_zwo2, det_zwo3, det_zwo4)
"""

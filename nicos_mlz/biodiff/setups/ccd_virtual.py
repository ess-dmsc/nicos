description = "Andor DV936 CCD camera setup"
group = "basic"

sysconfig = dict(
    datasinks=["FITSFileSaver", "LiveViewSink"],
)

includes = ["shutter", "microstep", "reactor", "nl1", "guidehall", "astrium"]

devices = dict(
    LiveViewSink=device(
        "nicos.devices.datasinks.LiveViewSink",
        description="Sends image data to LiveViewWidget",
    ),
    FITSFileSaver=device(
        "nicos.devices.datasinks.FITSImageSink",
        description="Saves image data in FITS format",
        filenametemplate=["%(proposal)s_%(pointcounter)08d.fits"],
        subdir=".",
    ),
    ccdtime=device(
        "nicos.devices.generic.VirtualTimer",
        description="Internal LimaCDDTimer",
    ),
    ccd=device(
        "nicos.devices.generic.VirtualImage",
        description="Andor DV936 CCD camera",
        size=(1024, 1024),
    ),
    roi1=device(
        "nicos.devices.generic.RectROIChannel",
        description="ROI 1",
        roi=(480, 200, 64, 624),
    ),
    roi2=device(
        "nicos.devices.generic.RectROIChannel",
        description="ROI 2",
        roi=(500, 350, 24, 344),
    ),
    ccddet=device(
        "nicos_mlz.biodiff.devices.detector.BiodiffDetector",
        description="Andor DV936 CCD detector",
        timers=["ccdtime"],
        images=["ccd"],
        counters=["roi1", "roi2"],
        maxage=10,
        gammashutter="gammashutter",
        photoshutter="photoshutter",
        postprocess=[
            ("roi1", "ccd"),
            ("roi2", "ccd"),
        ],
    ),
)

startupcode = """
SetDetectors(ccddet)
"""

# This setup has the simulated camera on a stock NICOS Detector and the live
# view sink. Command tests use it to check what reaches clients through the
# count loop.
includes = ["ess_count_scan_common"]

sysconfig = dict(datasinks=["liveview"])

devices = dict(
    liveview=device("nicos_ess.devices.datasinks.live_view.ReducedLiveViewSink"),
    cam=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetector",
        pollinterval=None,
    ),
    det=device(
        "nicos.devices.generic.Detector",
        images=["cam"],
        timers=["timer"],
        liveinterval=0.05,
    ),
)

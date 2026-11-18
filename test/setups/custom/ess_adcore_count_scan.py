# This setup has one adcore image channel on a stock NICOS Detector and the
# live view sink. Command tests use it to check what reaches clients through
# the count loop.
includes = ["ess_count_scan_common"]

sysconfig = dict(datasinks=["liveview"])

devices = dict(
    liveview=device("nicos_ess.devices.datasinks.live_view.ReducedLiveViewSink"),
    cam=device(
        "nicos_ess.devices.epics.adcore.AreaDetector",
        pv_root="SIM:AD:cam1:",
        image_pv_root="SIM:AD:image1:",
        pva=True,
    ),
    det=device(
        "nicos.devices.generic.Detector",
        images=["cam"],
        timers=["timer"],
        liveinterval=0.05,
    ),
)

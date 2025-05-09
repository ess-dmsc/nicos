description = "The monitor detector."

devices = dict(
    timer_1=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
    mfh_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="TEST:DEVICE:",
        readpv="TEST:DEVICE:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
    monitor_det=device(
        "nicos.devices.generic.detector.Detector",
        description="The monitor histogrammer",
        unit="",
        images=["mfh_1"],
        timers=["timer_1"],
        hist_schema="hs01",
    ),
)

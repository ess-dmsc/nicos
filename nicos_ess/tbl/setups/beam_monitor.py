description = "The monitor detector."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="TBL:MFHist:",
        readpv="TBL:MFHist:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
)

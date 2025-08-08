description = "The monitor detector."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.epics.multiframe_histogrammer.MultiFrameHistogrammer",
        description="Multi-frame histogrammer",
        pv_root="BIFR:MFHist:",
        readpv="BIFR:MFHist:signal",
        pva=True,
        monitor=True,
        pollinterval=None,
    ),
)

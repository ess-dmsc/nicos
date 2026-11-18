description = "TBL Bee Beans NGEM"

devices = dict(
    ngem_area_detector=device(
        "nicos_ess.devices.epics.adcore.AreaDetector",
        description="nGEM detector.",
        pv_root="TBL-DtGEM:NDet-nGem-001:",
        image_pv_root="TBL-DtGEM:image1:",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    ngem_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM event counter",
        readpv="TBL-DtGEM:NDet-nGem-001:CEvents-R",
    ),
    ngem_unidentified_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM unidentified event counter",
        readpv="TBL-DtGEM:NDet-nGem-001:BadEventIDs-R",
        visibility=(),
    ),
    ngem_failed_transfers=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM failed transfer counter",
        readpv="TBL-DtGEM:NDet-nGem-001:FailedTransfers-R",
        visibility=(),
    ),
    ngem_failed_pushes=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM failed push counter",
        readpv="TBL-DtGEM:NDet-nGem-001:FailedPushes-R",
        visibility=(),
    ),
    ngem_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer of the camera collector, for counts with a time preset",
        fmtstr="%.2f",
        unit="s",
        visibility=(),
    ),
    ngem_area_detector_collector=device(
        "nicos.devices.generic.Detector",
        description="nGEM area detector collector",
        images=["ngem_area_detector"],
        timers=["ngem_timer"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

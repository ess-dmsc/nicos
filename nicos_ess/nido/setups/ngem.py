description = "The nGEM in NIDO"

devices = dict(
    ngem=device(
        "nicos_ess.devices.epics.area_detector.AreaDetector",
        description="nGEM detector.",
        pv_root="TBL-Det1:cam1:",
        image_pv="TBL-Det1:image1:ArrayData",
        unit="images",
        pollinterval=None,
        pva=True,
        monitor=True,
    ),
    ngem_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM event counter",
        readpv="TBL-Det1:cam1:CEvents-R",
    ),
    ngem_unidentified_event_counter=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM unidentified event counter",
        readpv="TBL-Det1:cam1:BadEventIDs-R",
        visiblitity=(),
    ),
    ngem_failed_transfers=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM failed transfer counter",
        readpv="TBL-Det1:cam1:FailedTransfers-R",
        visiblitity=(),
    ),
    ngem_failed_pushes=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="nGEM failed push counter",
        readpv="TBL-Det1:cam1:FailedPushes-R",
        visiblitity=(),
    ),
    area_detector_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["ngem"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

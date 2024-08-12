# ruff: noqa: F821
description = "The area detector for NIDO"

devices = dict(
    tpx_camera=device(
        "nicos_ess.devices.epics.timepix.AreaDetector",
        description="The light tomography Hama camera.",
        pv_root="Tpx3:cam1:",
        image_pv="Tpx3:image1:ArrayData",
        unit="images",
        pollinterval=0.5,
        pva=True,
        monitor=True,
    ),
    area_detector_collector_tpx=device(
        "nicos_ess.devices.epics.timepix.AreaDetectorCollector",
        description="Area detector collector",
        images=["tpx_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
    hit_rate=device(
        "nicos.devices.epics.pva.EpicsReadable",
        description="Timepix hit rate",
        readpv="Tpx3:cam1:PelEvtRate_RBV",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)

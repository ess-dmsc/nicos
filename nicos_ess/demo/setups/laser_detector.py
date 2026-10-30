description = "The laser detector in the DEMO cave"

devices = dict(
    laser_pv=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The laser PV",
        readpv="DEMO-SETS:SE-BADC-001:SLOWDATA",
        visibility=(),
    ),
    laser_timing_status=device(
        "nicos_ess.demo.devices.laser_detector.TimingStatusDevice",
        description="The lasers timestamps synchronisation status",
        readpv="DEMO-SETS:SE-BPTP-001:PTP_STATUS",
        visibility=(),
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    laser=device(
        "nicos_ess.demo.devices.laser_detector.LaserDetector",
        description="Laser detector in DEMO cave",
        laser="laser_pv",
        timingstatus="laser_timing_status",
    ),
)

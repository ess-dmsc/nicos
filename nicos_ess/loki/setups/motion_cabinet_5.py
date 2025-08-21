description = "Motion Cabinet 5"

devices = dict(
    cabinet_5_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 5 status",
        pv_root="LOKI-MCS5:MC-MCU-05:Cabinet",
        number_of_bits=24,
    ),
)

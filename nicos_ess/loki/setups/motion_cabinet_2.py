description = "Motion Cabinet 2"

devices = dict(
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="LOKI-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
)

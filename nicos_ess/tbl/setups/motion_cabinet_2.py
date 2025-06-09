description = "Motion cabinet 2"

devices = dict(
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="TBL-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
)

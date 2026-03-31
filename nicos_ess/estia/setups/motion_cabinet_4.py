description = "Motion Cabinet 4"

devices = dict(
    cabinet_4_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 4 Status",
        pv_root="ESTIA-MCS4:MC-MCU-04:Cabinet",
        number_of_bits=24,
    ),
)

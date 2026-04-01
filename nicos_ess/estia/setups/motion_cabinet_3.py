description = "Motion Cabinet 3"

devices = dict(
    cabinet_3_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 3 Status",
        pv_root="ESTIA-MCS3:MC-MCU-03:Cabinet",
        number_of_bits=24,
    ),
)

description = "Motion Cabinet 1"

devices = dict(
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 Status",
        pv_root="ESTIA-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
)

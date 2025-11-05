description = "Motion Cabinet 2"

root = "ESTIA-MCS2:MC-MCU-02:"

devices = dict(
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 Status",
        pv_root=f"{root}Cabinet",
        number_of_bits=24,
    ),
)

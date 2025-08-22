description = "Motion Cabinet 3"

devices = dict(
    cabinet_3_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 3 status",
        pv_root="LOKI-MCS3:MC-MCU-03:Cabinet",
        number_of_bits=24,
    ),
    cabinet_3_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 1",
        readpv="LOKI-MCS3:MC-MCU-03:Pressure1",
    ),
    cabinet_3_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 2",
        readpv="LOKI-MCS3:MC-MCU-03:Pressure2",
    ),
)

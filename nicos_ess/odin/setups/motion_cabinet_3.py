# ODIN — Motion cabinet 3

description = "Motion cabinet 3"

# No motion/pneumatic axes assigned to cabinet 3 in the provided list.
# Keep cabinet health readbacks for completeness.

devices = dict(
    cabinet_3_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 3 status",
        pv_root="ODIN-MCS3:MC-MCU-03:Cabinet",
        number_of_bits=24,
    ),
    cabinet_3_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 1",
        readpv="ODIN-MCS3:MC-MCU-03:Pressure1",
    ),
    cabinet_3_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 3 pressure 2",
        readpv="ODIN-MCS3:MC-MCU-03:Pressure2",
    ),
)

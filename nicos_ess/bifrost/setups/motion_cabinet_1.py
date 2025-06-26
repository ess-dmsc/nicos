description = "Motion Cabinet 1"


devices = dict(
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root="BIFRO-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
    thermal_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Thermal Shutter",
        readpv="BIFRO-ThSht:MC-Pne-01:ShtAuxBits07",
    ),
    thermal_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the thermal shutter",
        readpv="BIFRO-ThSht:MC-Pne-01:ShtMsgTxt",
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv="BIFRO-MCS1:MC-MCU-01:Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv="BIFRO-MCS1:MC-MCU-01:Pressure2",
    ),
)

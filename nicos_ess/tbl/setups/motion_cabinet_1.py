description = "Motion cabinet 1"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Heavy Shutter",
        readpv="TBL-HvSht:MC-Pne-01:ShtAuxBits07",
    ),
    heavy_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the heavy shutter",
        readpv="TBL-HvSht:MC-Pne-01:ShtMsgTxt",
    ),
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root="TBL-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv="TBL-MCS1:MC-MCU-01:Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv="TBL-MCS1:MC-MCU-01:Pressure2",
    ),
)

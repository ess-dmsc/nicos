description = "Pneumatic devices in the YMIR motion cabinet 1"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Heaby Shutter",
        readpv="YMIR-HvSht:MC-Pne-01:ShtAuxBits07",
        writepv="YMIR-HvSht:MC-Pne-01:ShtOpen",
        statuspv="YMIR-HvSht:MC-Pne-01:ShtStatusCode",
        msgtxt="YMIR-HvSht:MC-Pne-01:ShtMsgTxt",
        pva=True,
        monitor=True,
    ),
    filter_1=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 1",
        readpv="YMIR-Fil:MC-Pne-01:ShtAuxBits07",
        writepv="YMIR-Fil:MC-Pne-01:ShtOpen",
        statuspv="YMIR-Fil:MC-Pne-01:ShtStatusCode",
        resetpv="YMIR-Fil:MC-Pne-01:ShtErrRst",
        msgtxt="YMIR-Fil:MC-Pne-01:ShtMsgTxt",
        monitor=True,
        pva=True,
    ),
    filter_2=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 2",
        readpv="YMIR-Fil:MC-Pne-02:ShtAuxBits07",
        writepv="YMIR-Fil:MC-Pne-02:ShtOpen",
        statuspv="YMIR-Fil:MC-Pne-02:ShtStatusCode",
        resetpv="YMIR-Fil:MC-Pne-02:ShtErrRst",
        msgtxt="YMIR-Fil:MC-Pne-02:ShtMsgTxt",
        monitor=True,
        pva=True,
    ),
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root="YMIR-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv="YMIR-MCS1:MC-MCU-01:Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv="YMIR-MCS1:MC-MCU-01:Pressure2",
    ),
)

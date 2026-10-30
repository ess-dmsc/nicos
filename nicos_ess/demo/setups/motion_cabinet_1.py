description = "Pneumatic devices in the DEMO motion cabinet 1"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Heaby Shutter",
        readpv="DEMO-HvSht:MC-Pne-01:ShtAuxBits07",
        writepv="DEMO-HvSht:MC-Pne-01:ShtOpen",
        statuspv="DEMO-HvSht:MC-Pne-01:ShtStatusCode",
        msgtxt="DEMO-HvSht:MC-Pne-01:ShtMsgTxt",
        pva=True,
        monitor=True,
    ),
    filter_1=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 1",
        readpv="DEMO-Fil:MC-Pne-01:ShtAuxBits07",
        writepv="DEMO-Fil:MC-Pne-01:ShtOpen",
        statuspv="DEMO-Fil:MC-Pne-01:ShtStatusCode",
        resetpv="DEMO-Fil:MC-Pne-01:ShtErrRst",
        msgtxt="DEMO-Fil:MC-Pne-01:ShtMsgTxt",
        monitor=True,
        pva=True,
    ),
    filter_2=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 2",
        readpv="DEMO-Fil:MC-Pne-02:ShtAuxBits07",
        writepv="DEMO-Fil:MC-Pne-02:ShtOpen",
        statuspv="DEMO-Fil:MC-Pne-02:ShtStatusCode",
        resetpv="DEMO-Fil:MC-Pne-02:ShtErrRst",
        msgtxt="DEMO-Fil:MC-Pne-02:ShtMsgTxt",
        monitor=True,
        pva=True,
    ),
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root="DEMO-MCS1:MC-MCU-01:Cabinet",
        number_of_bits=24,
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv="DEMO-MCS1:MC-MCU-01:Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv="DEMO-MCS1:MC-MCU-01:Pressure2",
    ),
)

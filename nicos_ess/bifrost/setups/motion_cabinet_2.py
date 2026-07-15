description = "Motion cabinet 2"


devices = dict(
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="BIFRO-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
    attenuator_1=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Attenuator Changer 1",
        readpv="BIFRO-AttChg:MC-Pne-01:ShtAuxBits07",
        writepv="BIFRO-AttChg:MC-Pne-01:ShtOpen",
        statuspv="BIFRO-AttChg:MC-Pne-01:ShtStatusCode",
        msgtxt="BIFRO-AttChg:MC-Pne-01:ShtMsgTxt",
        pva=True,
        monitor=True,
    ),
    attenuator_2=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Attenuator Changer 2",
        readpv="BIFRO-AttChg:MC-Pne-02:ShtAuxBits07",
        writepv="BIFRO-AttChg:MC-Pne-02:ShtOpen",
        statuspv="BIFRO-AttChg:MC-Pne-02:ShtStatusCode",
        msgtxt="BIFRO-AttChg:MC-Pne-02:ShtMsgTxt",
        pva=True,
        monitor=True,
    ),
    attenuator_3=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Attenuator Changer 3",
        readpv="BIFRO-AttChg:MC-Pne-03:ShtAuxBits07",
        writepv="BIFRO-AttChg:MC-Pne-03:ShtOpen",
        statuspv="BIFRO-AttChg:MC-Pne-03:ShtStatusCode",
        msgtxt="BIFRO-AttChg:MC-Pne-03:ShtMsgTxt",
        pva=True,
        monitor=True,
    ),
    cabinet_2_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 1",
        readpv="BIFRO-MCS2:MC-MCU-02:Pressure1",
    ),
    cabinet_2_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 2",
        readpv="BIFRO-MCS2:MC-MCU-02:Pressure2",
    ),
)

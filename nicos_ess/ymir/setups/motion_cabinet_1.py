description = "Pneumatic devices in the YMIR motion cabinet 1"

devices = dict(
    heavy_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Heaby Shutter",
        readpv="YMIR-HvSht:MC-Pne-01:ShtAuxBits07",
        writepv="YMIR-HvSht:MC-Pne-01:ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    heavy_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the heavy shutter",
        readpv="YMIR-HvSht:MC-Pne-01:ShtMsgTxt",
    ),
    filter_1=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 1",
        readpv="YMIR-Fil:MC-Pne-01:ShtAuxBits07",
        writepv="YMIR-Fil:MC-Pne-01:ShtOpen",
    ),
    filter_1_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the filter 1",
        readpv="YMIR-Fil:MC-Pne-01:ShtMsgTxt",
    ),
    filter_2=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Filter 2",
        readpv="YMIR-Fil:MC-Pne-02:ShtAuxBits07",
        writepv="YMIR-Fil:MC-Pne-02:ShtOpen",
    ),
    filter_2_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the filter 2",
        readpv="YMIR-Fil:MC-Pne-02:ShtMsgTxt",
    ),
)

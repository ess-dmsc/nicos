description = 'Pneumatic devices in the YMIR motion cabinet 1'

devices = dict(
    heavy_shutter=device(
        'nicos_ess.devices.epics.pva.shutter.EpicsShutter',
        description="Heaby Shutter",
        readpv='YMIR-HvSht:MC-Pne-01:ShtAuxBits07',
        writepv='YMIR-HvSht:MC-Pne-01:ShtOpen',
        pva=True,
        pollinterval=None,
        monitor=True,
    ),
    heavy_shutter_status=device(
        'nicos.devices.epics.pva.EpicsStringReadable',
        description='Status of the heavy shutter',
        readpv='YMIR-HvSht:MC-Pne-01:ShtMsgTxt',
        pva=True,
        pollinterval=None,
        monitor=True
    ),
    filter_1=device(
        'nicos_ess.devices.epics.pva.shutter.EpicsShutter',
        description="Filter 1",
        readpv='YMIR-Fil:MC-Pne-01:ShtAuxBits07',
        writepv='YMIR-Fil:MC-Pne-01:ShtOpen',
        pva=True,
        pollinterval=None,
        monitor=True,
    ),
    filter_1_status=device(
        'nicos.devices.epics.pva.EpicsStringReadable',
        description='Status of the filter 1',
        readpv='YMIR-Fil:MC-Pne-01:ShtMsgTxt',
        pva=True,
        pollinterval=None,
        monitor=True
    ),
    filter_2=device(
        'nicos_ess.devices.epics.pva.shutter.EpicsShutter',
        description="Filter 2",
        readpv='YMIR-Fil:MC-Pne-02:ShtAuxBits07',
        writepv='YMIR-Fil:MC-Pne-02:ShtOpen',
        pva=True,
        pollinterval=None,
        monitor=True,
    ),
    filter_2_status=device(
        'nicos.devices.epics.pva.EpicsStringReadable',
        description='Status of the filter 2',
        readpv='YMIR-Fil:MC-Pne-02:ShtMsgTxt',
        pva=True,
        pollinterval=None,
        monitor=True
    ),
)
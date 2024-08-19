description = "Prototype interferometer measurement"

etalon_prefix = "ESTIA-Sel1:Mech-GU-001"

group = "lowlevel"

devices = dict(
    # pilot_laser=device(
    #     'nicos_ess.estia.devices.multiline.PilotLaser',
    #     description='Pilot laser',
    #     pvprefix=etalon_prefix,
    #     readpv=f'{etalon_prefix}:LaserReady-R',
    #     switchstates={
    #         'enable': 1,
    #         'disable': 0
    #     },
    #     switchpvs={
    #         'read': f'{etalon_prefix}:RedPilotLaser-S',
    #         'write': f'{etalon_prefix}:RedPilotLaser-S'
    #     },
    #     visibility=(),
    # ),
    # env_humidity=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Environmental humidity',
    #     readpv=f'{etalon_prefix}:EnvDataHum-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # env_pressure=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Environmental pressure',
    #     readpv=f'{etalon_prefix}:EnvDataPress-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # env_temperature=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Environmental temperature',
    #     readpv=f'{etalon_prefix}:EnvDataTemp-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # temp_1=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='First temperature sensor',
    #     readpv=f'{etalon_prefix}:TempSensorS2-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # temp_2=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Second temperature sensor',
    #     readpv=f'{etalon_prefix}:TempSensorS2-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # temp_3=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Third temperature sensor',
    #     readpv=f'{etalon_prefix}:TempSensorS3-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    # temp_4=device(
    #     'nicos.devices.epics.pva.EpicsReadable',
    #     description='Fourth emperature sensor',
    #     readpv=f'{etalon_prefix}:TempSensorS4-R',
    #     visibility=(),
    #     pollinterval=None,
    #     monitor=True,
    #     pva=True,
    # ),
    multiline=device(
        "nicos_ess.estia.devices.multiline.MultilineController",
        description="Multiline interferometer controller",
        pvprefix=etalon_prefix,
        readpv=f"{etalon_prefix}:MeasState-R",
        epicstimeout=30.0,
        # pilot_laser='pilot_laser',
        # temperature='env_temperature',
        # pressure='env_pressure',
        # humidity='env_humidity'
    ),
)

channels = [17, 18, 19, 20, 21, 22, 23, 24, 27, 28]

for ch in channels:
    devices[f"ch{ch:02}"] = device(
        "nicos_ess.estia.devices.multiline.MultilineChannel",
        description=f"Value of channel {ch}",
        channel=ch,
        controller="multiline",
        unit="mm",
    )

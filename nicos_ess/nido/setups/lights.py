description = 'MOXA box controlled lights'

pv_root = 'SE-NURF:SE-E1241-001:'

devices = dict(
    ch_0=device(
        'nicos_ess.devices.epics.manual_switch.ManualSwitch',
        description='Large box shutter',
        readpv='{}AO0'.format(pv_root),
        writepv='{}AO0Set'.format(pv_root),
        pollinterval=0.5,
        monitor=True,
        pva=True,
        states=['Close','Open'],
        mapping={'Close':0,'Open':5}
        #abslimits=(0,5),
        #userlimits=(0,5),
    ),
    ch_3=device(
        'nicos.devices.epics.pva.EpicsAnalogMoveable',
        description='Small LED',
        readpv='{}AO3'.format(pv_root),
        writepv='{}AO3Set'.format(pv_root),
        pollinterval=0.5,
        monitor=True,
        pva=True,
        abslimits=(0,5),
        userlimits=(0,5),
    )
)



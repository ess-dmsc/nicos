description = 'Some kind of SKF chopper'

pv_root = 'LabS-Embla:Chop-Drv-0601:'

devices = dict(
    skf_drive_temp=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Drive temperature',
        readpv='{}DrvTmp_Stat'.format(pv_root),
    ),
    skf_motor_temp=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Motor temperature',
        readpv='{}MtrTmp_Stat'.format(pv_root),
    ),
    skf_pos_v13=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Position',
        readpv='{}PosV13_Stat'.format(pv_root),
    ),
    skf_pos_v24=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Position',
        readpv='{}PosV24_Stat'.format(pv_root),
    ),
    skf_pos_w13=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Position',
        readpv='{}PosW13_Stat'.format(pv_root),
    ),
    skf_pos_w24=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Position',
        readpv='{}PosW24_Stat'.format(pv_root),
    ),
    skf_pos_Z12=device('nicos_ess.devices.epics.pva.EpicsReadable',
        description='Position',
        readpv='{}PosZ12_Stat'.format(pv_root),
    ),
    skf_status=device(
        'nicos.devices.epics.EpicsStringReadable',
        description='The chopper status.',
        readpv='{}Chop_Stat'.format(pv_root),
    ),
    skf_control=device(
        'nicos_ess.devices.epics.extensions.EpicsMappedMoveable',
        description='Used to start and stop the chopper.',
        readpv='{}Cmd'.format(pv_root),
        writepv='{}Cmd'.format(pv_root),
        requires={'level': 'user'},
        mapping={'Clear chopper': 8,
                 'Start chopper': 6,
                 'Async start': 5,
                 'Stop chopper': 3,
                 'Reset chopper': 1,
        },
    ),
    skf_speed=device(
        'nicos_ess.devices.epics.pva.EpicsAnalogMoveable',
        description='The current speed.',
        requires={'level': 'user'},
        readpv='{}Spd_Stat'.format(pv_root),
        writepv='{}Spd_SP'.format(pv_root),
        abslimits=(0.0, 77),
    ),

)

description = 'The mini-chopper for YMIR'

pv_root = 'Utg-Ymir:Chop-Drv-0101:'

devices = dict(
    mini_chopper_status=device(
        'nicos.devices.epics.EpicsStringReadable',
        description='The chopper status.',
        readpv='{}Chop_Stat'.format(pv_root),
        lowlevel=True,
    ),
    mini_chopper_control=device(
        'nicos_ess.devices.epics.extensions.EpicsMappedMoveable',
        description='Used to start and stop the chopper.',
        readpv='{}Cmd'.format(pv_root),
        writepv='{}Cmd'.format(pv_root),
        requires={'level': 'admin'},
        lowlevel=True,
        mapping={'start': 6,
                 'stop': 3,
                 'reset': 1,
        },
    ),
    mini_chopper_speed=device(
        'nicos_ess.devices.epics.pva.EpicsAnalogMoveable',
        description='The current speed.',
        readpv='{}Spd_Stat'.format(pv_root),
        writepv='{}Spd_SP'.format(pv_root),
        abslimits=(0.0, 14),
        lowlevel=True,
    ),
    mini_chopper_delay=device(
        'nicos_ess.devices.epics.pva.EpicsAnalogMoveable',
        description='The current delay.',
        readpv='{}Chopper-Delay-SP'.format(pv_root),
        writepv='{}Chopper-Delay-SP'.format(pv_root),
        abslimits=(0.0, 71428571.0),
        lowlevel=True,
    ),
    mini_chopper=device(
        'nicos_ess.devices.epics.mini_chopper.EssChopper',
        description='The mini-chopper',
        speed='mini_chopper_speed',
        phase='mini_chopper_delay',
        state='mini_chopper_status',
        command='mini_chopper_control',
    ),
)

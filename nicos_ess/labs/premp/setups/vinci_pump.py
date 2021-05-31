description = 'Vinci pump'

pv_root = 'utg-vincipump-001:Dr1:'

devices = dict(
    vinci_volume=device(
        'nicos_ess.devices.epics.pva.EpicsReadable',
        description='The volume',
        readpv='{}Volume'.format(pv_root),
    ),
    vinci_flow=device(
        'nicos_ess.devices.epics.pva.EpicsReadable',
        description='The flow',
        readpv='{}Flow'.format(pv_root),
    ),
    vinci_pressure=device(
        'nicos_ess.devices.epics.pva.EpicsAnalogMoveable',
        description='The pressure',
        readpv='{}Pressure'.format(pv_root),
        writepv='{}PM_Press_SP'.format(pv_root)
    ),
)

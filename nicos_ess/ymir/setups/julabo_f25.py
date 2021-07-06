description = 'Julabo F25 for the Huginn-sans.'

pv_root = 'SES-HGNSANS-01:WTctrl-JUL25HL-001:'

devices = dict(
    T_julabo=device(
        'nicos.devices.epics.EpicsAnalogMoveable',
        description='The temperature',
        readpv='SIMPLE:VALUE1'.format(pv_root),
        writepv='SIMPLE:VALUE1'.format(pv_root),
        targetpv='SIMPLE:VALUE1'.format(pv_root),
        epicstimeout=3.0,
        abslimits=(0,100),
    ),
    julabo_status=device(
        'nicos_ess.devices.epics.pva.EpicsMappedMoveable',
        description='The status',
        readpv='SIMPLE:MBBI'.format(pv_root),
        writepv='SIMPLE:MBBI'.format(pv_root),
        # mapping={'ZERO': 0, 'ONE': 1},
        ignore_stop=True,
    ),
    T_julabo_external=device(
        'nicos.devices.epics.EpicsReadable',
        description='The external sensor temperature',
        readpv='{}EXTT'.format(pv_root),
        lowlevel=True,
        epicstimeout=3.0,
    ),
    julabo_external_enabled=device(
        'nicos.devices.epics.EpicsStringReadable',
        description='Whether the external sensor is enabled',
        readpv='{}EXTSENS'.format(pv_root),
        lowlevel=True,
        epicstimeout=3.0,
    ),
    julabo_internal_P=device(
        'nicos.devices.epics.EpicsAnalogMoveable',
        description='The internal P value',
        readpv='{}INTP'.format(pv_root),
        writepv='{}INTP:SP'.format(pv_root),
        lowlevel=True,
        epicstimeout=3.0,
    ),
    julabo_internal_I=device(
        'nicos.devices.epics.EpicsAnalogMoveable',
        description='The internal I value',
        readpv='{}INTI'.format(pv_root),
        writepv='{}INTI:SP'.format(pv_root),
        lowlevel=True,
        epicstimeout=3.0,
    ),
    julabo_internal_D=device(
        'nicos.devices.epics.EpicsAnalogMoveable',
        description='The internal D value',
        readpv='{}INTD'.format(pv_root),
        writepv='{}INTD:SP'.format(pv_root),
        lowlevel=True,
        epicstimeout=3.0,
    ),
)

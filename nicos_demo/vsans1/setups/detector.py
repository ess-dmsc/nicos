description = 'detector related devices including beamstop'

group = 'lowlevel'

BS1_X_OFS = -475.055

devices = dict(
    det1_t_ist = device('nicos.devices.generic.VirtualTimer',
        description = 'measured time of detector 1',
        fmtstr = '%.0f',
        lowlevel = True,
        maxage = 120,
        pollinterval = 15,
    ),
    det1_hv_interlock = device('nicos.devices.generic.ManualSwitch',
        description = 'interlock for detector 1 high voltage',
        lowlevel = True,
        states = (0, 1),
    ),
    det1_hv_discharge_mode = device('nicos.devices.generic.ManualSwitch',
        description = 'set discharge mode of detector 1',
        lowlevel = True,
        states = (0, 1),
    ),
    det1_hv_discharge = device('nicos.devices.generic.ManualSwitch',
        description = 'enable and disable discharge of detector 1',
        lowlevel = True,
        states = (0, 1),
    ),
    det1_hv_supply = device('nicos.devices.generic.VirtualMotor',
        description = 'high voltage power supply of detector 1',
        abslimits = (0.0, 1501.0),
        maxage = 120,
        pollinterval = 15,
        fmtstr = '%d',
        unit = 'V',
    ),
    det1_hv_ax = device('nicos_mlz.sans1.devices.hv.Sans1HV',
        description = 'high voltage of detector 1',
        unit = 'V',
        fmtstr = '%d',
        supply = 'det1_hv_supply',
        discharger = 'det1_hv_discharge',
        interlock = 'det1_hv_interlock',
        maxage = 120,
        pollinterval = 15,
        lowlevel = True,
    ),
    det1_hv_offtime = device('nicos_mlz.sans1.devices.hv.Sans1HVOffDuration',
        description = 'Duration below operating voltage',
        hv_supply = 'det1_hv_ax',
        maxage = 120,
        pollinterval = 15,
    ),
    det1_hv = device('nicos_mlz.sans1.devices.hv.VoltageSwitcher',
        description = 'high voltage of detector 1 switcher',
        moveable = 'det1_hv_ax',
        mapping = {'ON': (1500, 1),
                   'LOW': (1, 69),
                   'OFF': (0, 1)},
        precision = 1,
        unit = '',
        fallback = 'unknown',
    ),
    hv_current = device('nicos.devices.generic.ReadonlyParamDevice',
        description = 'high voltage current of detector 1',
        device = 'det1_hv_supply',
        parameter = 'curvalue',  # 'current',
        maxage = 120,
        pollinterval = 15,
        lowlevel = True,
    ),
    det1_x = device('nicos.devices.generic.Axis',
        description = 'detector 1 x axis',
        fmtstr = '%.0f',
        maxage = 120,
        pollinterval = 5,
        requires = dict(level = 'admin'),
        precision = 0.3,
        motor = 'det1_xmot',
        obs = [],
    ),
    det1_xmot = device('nicos.devices.generic.VirtualMotor',
        description = 'detector 1 x motor',
        fmtstr = '%.1f',
        abslimits = (4, 570),
        curvalue = 4,
        lowlevel = True,
        unit = 'mm',
    ),
    det1_z = device('nicos.devices.generic.LockedDevice',
        description =
        'detector 1 z position interlocked with high voltage supply',
        device = 'det1_z_ax',
        lock = 'det1_hv',
        unlockvalue = 'LOW',
        fmtstr = '%.0f',
        maxage = 120,
        pollinterval = 15,
    ),
    det1_z_ax = device('nicos.devices.generic.Axis',
        description = 'detector 1 z axis',
        fmtstr = '%.0f',
        maxage = 120,
        pollinterval = 5,
        lowlevel = True,
        precision = 1.0,
        dragerror = 150.0,
        motor = 'det1_zmot',
        obs = [],
    ),
    det1_zmot = device('nicos.devices.generic.VirtualMotor',
        description = 'detector 1 z motor',
        fmtstr = '%.1f',
        abslimits = (1100, 20000),
        userlimits = (1111, 20000),
        curvalue = 1111,
        lowlevel = True,
        unit = 'mm',
    ),
    det1_omg = device('nicos.devices.generic.Axis',
        description = 'detector 1 omega axis',
        fmtstr = '%.0f',
        maxage = 120,
        pollinterval = 5,
        requires = dict(level = 'admin'),
        precision = 0.2,
        motor = 'det1_omegamot',
    ),
    det1_omegamot = device('nicos.devices.generic.VirtualMotor',
        description = 'detector 1 omega motor',
        fmtstr = '%.1f',
        abslimits = (-0.2, 21),
        lowlevel = True,
        unit = 'deg',
    ),
    bs1_xmot = device('nicos.devices.generic.VirtualMotor',
        description = 'beamstop 1 x motor',
        fmtstr = '%.2f',
        abslimits = (480, 868),
        curvalue = 823.055,  # 'none' position
        lowlevel = True,
        unit = 'mm',
    ),
    bs1_xenc = device('nicos.devices.generic.VirtualCoder',
        fmtstr = '%.2f',
        lowlevel = True,
        motor = 'bs1_xmot',
    ),
    bs1_ymot = device('nicos.devices.generic.VirtualMotor',
        description = 'beamstop 1 y motor',
        fmtstr = '%.1f',
        abslimits = (-100, 590),
        curvalue = 100, 
        lowlevel = True,
        unit = 'mm',
    ),
    bs1_yenc = device('nicos.devices.generic.VirtualCoder',
        fmtstr = '%.2f',
        lowlevel = True,
        motor = 'bs1_ymot',
    ),
    bs1_xax = device('nicos_mlz.sans1.devices.beamstop.BeamStopAxis',
        description = 'beamstop 1 x axis',
        motor = 'bs1_xmot',
        coder = 'bs1_xenc',
        precision = 0.1,
        fmtstr = '%.2f',
        lowlevel = True,
    ),
    bs1_yax = device('nicos_mlz.sans1.devices.beamstop.BeamStopAxis',
        description = 'beamstop 1 y axis',
        motor = 'bs1_ymot',
        coder = 'bs1_yenc',
        precision = 0.1,
        fmtstr = '%.2f',
        lowlevel = True
    ),
    bs1 = device('nicos_mlz.sans1.devices.beamstop.BeamStop',
        description = 'selects the shape of the beamstop',
        xaxis = 'bs1_xax',
        yaxis = 'bs1_yax',
        ypassage = -99, # encoder value! # XXX!
        unit = 'mm',
        shape = 'none',
        slots = { # in encoder values !
            '100x100' : 125.2 - BS1_X_OFS,
            'd35'     : 197.0 - BS1_X_OFS,
            '70x70'   : 253.4 - BS1_X_OFS,
            '55x55'   : 317.4 - BS1_X_OFS,
            'none'    : 348.0 - BS1_X_OFS,  # no shapeholder!
            '85x85'   : 390.4 - BS1_X_OFS,
        },
        # limits for free-move area (in encoder values!)
        xlimits = (480, 868), # XXX!
        ylimits = (100, 590), # XXX!
        # requires = dict(level='admin'),
    ),
    bs1_shape = device('nicos.devices.generic.ParamDevice',
        description = 'selected beam shape',
        device = 'bs1',
        parameter = 'shape',
        copy_status = True,
        requires = {'level': 'admin'},
    ),
)
description = 'The Anton-Paar MCR702e Rheometer'

pv_root = 'TEST:RHEO:'

devices = dict(
    viscocity=device(
        'nicos.devices.epics.pva.EpicsReadable',
        description='The calculated viscosity.',
        readpv='{}Viscosity-RB'.format(pv_root),
        monitor=True,
        pva=True,
        pollinterval=None,
    ),
    tot_modulus=device(
        'nicos.devices.epics.pva.EpicsReadable',
        description='The calculated tot modulus.',
        readpv='{}TotModulus-RB'.format(pv_root),
        monitor=True,
        pva=True,
        pollinterval=None,
    ),
    meas_number=device(
        'nicos.devices.epics.pva.EpicsReadable',
        description='The measurement number, restarts at 1 for each new measurement interval.',
        readpv='{}MeasNumb-R'.format(pv_root),
        monitor=True,
        pva=True,
        pollinterval=None,
    ),
    meas_interval=device(
        'nicos.devices.epics.pva.EpicsReadable',
        description='The interval number.',
        readpv='{}MeasInterval-R'.format(pv_root),
        monitor=True,
        pva=True,
        pollinterval=None,
    ),
    rheo_control=device(
        'nicos_ess.devices.epics.ap_rheometer.RheometerControl',
        description='The controller for the rheometer.',
        pv_root=pv_root,
        pva=True,
    ),
)

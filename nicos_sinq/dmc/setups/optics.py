description = 'Sample devices in the SINQ DMC.'

pvprefix = 'SQ:DMC:mcu4:'

devices = dict(
    taz=device('nicos_ess.devices.epics.motor.EpicsMotor',
               description='Optics Z motor',
               motorpv=f'{pvprefix}TAZ',
               errormsgpv=f'{pvprefix}TAZ-MsgTxt',
               ),
)
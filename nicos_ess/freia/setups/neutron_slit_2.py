description = "2-blade Neutron Slit 2"
prefix = "FREIA-ColSl2:MC-"

devices = dict(
    blade_r=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Right blade",
        motorpv=f"{prefix}SlYm-01:Mtr",
        visibility=(),
    ),
    blade_l=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Left blade",
        motorpv=f"{prefix}SlYp-01:Mtr",
        visibility=(),
    ),
    neutron_slit_2=device(
        "nicos.devices.generic.slit.HorizontalGap",
        description="Main Slit Controller",
        opmode="2blades_opposite",
        left="blade_l",
        right="blade_r",
    ),
)

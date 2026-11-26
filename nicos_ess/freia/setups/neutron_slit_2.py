description = "2-blade Neutron Slit 2"
prefix = "FREIA-ColSl2:MC-"

devices = dict(
    ns2_blade_b=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Right blade",
        motorpv=f"{prefix}SlZm-01:Mtr",
        visibility=(),
    ),
    ns2_blade_t=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Left blade",
        motorpv=f"{prefix}SlZp-01:Mtr",
        visibility=(),
    ),
    neutron_slit_2=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit Controller",
        opmode="2blades_opposite",
        bottom="ns2_blade_b",
        top="ns2_blade_t",
    ),
)

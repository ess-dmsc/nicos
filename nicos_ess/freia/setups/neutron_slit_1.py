description = "4-blade Neutron Slit 1"
prefix = "FREIA-ColSl1:MC-"

devices = dict(
    ns1_blade_r=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Right blade",
        motorpv=f"{prefix}SlYm-01:Mtr",
        visibility=(),
    ),
    ns1_blade_l=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Left blade",
        motorpv=f"{prefix}SlYp-01:Mtr",
        visibility=(),
    ),
    ns1_blade_t=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Top blade",
        motorpv=f"{prefix}SlZp-01:Mtr",
        visibility=(),
    ),
    ns1_blade_b=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Bottom blade",
        motorpv=f"{prefix}SlZm-01:Mtr",
        visibility=(),
    ),
    neutron_slit_1=device(
        "nicos.devices.generic.slit.Slit",
        description="Main Slit Controller",
        opmode="4blades_opposite",
        left="ns1_blade_l",
        right="ns1_blade_r",
        top="ns1_blade_t",
        bottom="ns1_blade_b",
    ),
)

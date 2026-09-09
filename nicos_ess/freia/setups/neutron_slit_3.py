description = "4-blade Neutron Slit 3"
prefix = "FREIA-ColSl3:MC-"

devices = dict(
    ns3_blade_r=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Right blade",
        motorpv=f"{prefix}SlYm-01:Mtr",
        visibility=(),
    ),
    ns3_blade_l=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Left blade",
        motorpv=f"{prefix}SlYp-01:Mtr",
        visibility=(),
    ),
    ns3_blade_t=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Top blade",
        motorpv=f"{prefix}SlZp-01:Mtr",
        visibility=(),
    ),
    ns3_blade_b=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Bottom blade",
        motorpv=f"{prefix}SlZm-01:Mtr",
        visibility=(),
    ),
    neutron_slit_3=device(
        "nicos.devices.generic.slit.Slit",
        description="Main Slit Controller",
        opmode="4blades_opposite",
        left="ns3_blade_l",
        right="ns3_blade_r",
        top="ns3_blade_t",
        bottom="ns3_blade_b",
    ),
)

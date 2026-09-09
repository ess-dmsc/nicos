description = "3-set Piezo Slits 1"
prefix = "FREIA-PzSl1:MC-"

devices = dict(
    # Piezo Slit 1
    ps1_z1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-1 top blade",
        motorpv=f"{prefix}SlZp-01:Mtr",
        visibility=(),
    ),
    ps1_z2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-1 bottom blade",
        motorpv=f"{prefix}SlZm-01:Mtr",
        visibility=(),
    ),
    piezo_set_1_1=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 1-1 Controller",
        opmode="2blades_opposite",
        top="ps1_z1",
        bottom="ps1_z2",
    ),
    # Piezo Slit 2
    ps1_z3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-2 top blade",
        motorpv=f"{prefix}SlZp-02:Mtr",
        visibility=(),
    ),
    ps1_z4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-2 bottom blade",
        motorpv=f"{prefix}SlZm-02:Mtr",
        visibility=(),
    ),
    piezo_set_1_2=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 1-2 Controller",
        opmode="2blades_opposite",
        top="ps1_z3",
        bottom="ps1_z4",
    ),
    # Piezo Slit 3
    ps1_z5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-3 top blade",
        motorpv=f"{prefix}SlZp-03:Mtr",
        visibility=(),
    ),
    ps1_z6=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 1-3 bottom blade",
        motorpv=f"{prefix}SlZm-03:Mtr",
        visibility=(),
    ),
    piezo_set_1_3=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 1-3 Controller",
        opmode="2blades_opposite",
        top="ps1_z5",
        bottom="ps1_6",
    ),
)

description = "3-set Piezo Slits 2"
prefix = "FREIA-PzSl2:MC-"

devices = dict(
    # Piezo Slit 1
    ps2_z1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-1 top blade",
        motorpv=f"{prefix}SlZp-01:Mtr",
        visibility=(),
    ),
    ps2_z2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-1 bottom blade",
        motorpv=f"{prefix}SlZm-01:Mtr",
        visibility=(),
    ),
    piezo_set_2_1=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 2-1 Controller",
        opmode="2blades_opposite",
        top="ps2_z1",
        bottom="ps2_z2",
    ),
    # Piezo Slit 2
    ps2_z3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-2 top blade",
        motorpv=f"{prefix}SlZp-02:Mtr",
        visibility=(),
    ),
    ps2_z4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-2 bottom blade",
        motorpv=f"{prefix}SlZm-02:Mtr",
        visibility=(),
    ),
    piezo_set_1_2=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 2-2 Controller",
        opmode="2blades_opposite",
        top="ps2_z3",
        bottom="ps2_z4",
    ),
    # Piezo Slit 3
    ps2_z5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-3 top blade",
        motorpv=f"{prefix}SlZp-03:Mtr",
        visibility=(),
    ),
    ps2_z6=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit set 2-3 bottom blade",
        motorpv=f"{prefix}SlZm-03:Mtr",
        visibility=(),
    ),
    piezo_set_1_3=device(
        "nicos.devices.generic.slit.VerticalGap",
        description="Main Slit 2-3 Controller",
        opmode="2blades_opposite",
        top="ps2_z5",
        bottom="ps2_6",
    ),
)

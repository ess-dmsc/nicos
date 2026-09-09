description = "Ancillary axis for the Sample Area"
prefix = "FREIA-AncSt:MC-Lin-"

devices = dict(
    an_axis_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 1 Motor",
        motorpv=f"{prefix}01:Mtr",
    ),
    an_axis_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 2 Motor",
        motorpv=f"{prefix}02:Mtr",
    ),
    an_axis_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 3 Motor",
        motorpv=f"{prefix}03:Mtr",
    ),
    an_axis_4=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 4 Motor",
        motorpv=f"{prefix}04:Mtr",
    ),
    an_axis_5=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 5 Motor",
        motorpv=f"{prefix}05:Mtr",
    ),
    an_axis_6=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 6 Motor",
        motorpv=f"{prefix}06:Mtr",
    ),
)

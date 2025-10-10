description = "Test motor"

includes = ["stdsystem"]

devices = dict(
    motor_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Single axis positioner",
        motorpv="SIM:M1",
        has_powerauto=False,
        has_errormsg=False,
        has_errorbit=False,
        has_reseterror=False,
    ),
)

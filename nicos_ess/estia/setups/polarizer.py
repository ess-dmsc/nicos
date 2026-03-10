description = "Polarizer"

devices = dict(
    polarizer_lin_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer in-beam changer",
        motorpv="ESTIA-PolChg:MC-LinY01:Mtr",
    ),
    angular_adjustment=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer angular adjustment",
        motorpv="ESTIA-PolChg:MC-RotZ01:Mtr",
    ),
)

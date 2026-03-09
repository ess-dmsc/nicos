description = "Polarizer"

devices = dict(
    in_beam_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer in-beam changer",
        pv_root="ESTIA-PolChg:MC-LinY01:Mtr",
    ),
    angular_adjustment=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer angular adjustment",
        pv_root="ESTIA-PolChg:MC-RotZ01:Mtr",
    ),
)

description = "Solid Liquid Sample Changer Horizontal Stage"


devices = dict(
    sample_changer_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="SLSC Horizontal Motion",
        motorpv="ESTIA-SpSt:MC-LinY-01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
)

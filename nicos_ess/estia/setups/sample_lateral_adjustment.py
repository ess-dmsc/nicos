description = "Sample Lateral Adjustment and Sample Table Pneumatic Coupling"


devices = dict(
    sample_changer_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Y Motion",
        motorpv="ESTIA-SpLin:MC-LinY-01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
)

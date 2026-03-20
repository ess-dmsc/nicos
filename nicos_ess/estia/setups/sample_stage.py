description = "Sample stage system made up of Newport Hexapod and Goinometer Sample Rotation Stage"


devices = dict(
    sample_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Stage Rotation Base",
        motorpv="ESTIA-SpRot:MC-RotZ01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    # TODO: Add hexapod here when available
)

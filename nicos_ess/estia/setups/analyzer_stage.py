description = "Analyzer stage motions"


devices = dict(
    analyzer_lift=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="analyzer vertical motion",
        motorpv="ESTIA-AnLft:MC-LinZ01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
    ),
    analyzer_angular_adjustment_motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="analyzer angular adjustment motor",
        motorpv="ESTIA-AnRot:MC-RotY01:Mtr",
        has_powerauto=False,
        fmtstr="%.2f",
        visibility=(),
    ),
    analyzer_angular_adjustment=device(
        "nicos_ess.estia.devices.transformed_analyzer_stage.MmToDegrees",
        description="analyzer angular adjustment",
        motor="analyzer_angular_adjustment_motor",
    ),
)

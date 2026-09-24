description = "Detector Positioning Motors"

devices = dict(
    detector_lift=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector z-axis linear motion",
        motorpv="FREIA-DtLft:MC-LinZ-01:Mtr",
    ),
    detector_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector y-axis roational",
        motorpv="FREIA-DtRot:MC-RotY-02:Mtr",
    ),
    detector_beam_trans=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Detector x-axis linear motion",
        motorpv="FREIA-DtLin:MC-LinX-03:Mtr",
    ),
)

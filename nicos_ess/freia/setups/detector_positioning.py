description = "Detector Positioning Motors"

devices = dict(
    detector_lift=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 1 Motor",
        motorpv="FREIA-DtLft:MC-LinZ-01:Mtr",
    ),
    detector_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 2 Motor",
        motorpv="FREIA-DtRot:MC-RotY-02:Mtr",
    ),
    detector_beam_trans=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Axis 3 Motor",
        motorpv="FREIA-DtLin:MC-LinX-03:Mtr",
    ),
)

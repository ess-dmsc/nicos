description = "collimation changers"

pv_root = "FREIA-ColCh1:MC-LinY-"

devices = dict(
    collimation_changer_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation changer 1",
        motorpv=f"{pv_root}01:Mtr",
    ),
    collimation_changer_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation changer 2",
        motorpv=f"{pv_root}02:Mtr",
    ),
    collimation_changer_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation changer 3",
        motorpv=f"{pv_root}03:Mtr",
    ),
)

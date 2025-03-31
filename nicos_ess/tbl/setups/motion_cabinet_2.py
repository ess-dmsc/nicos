description = "Motion cabinet 2"

devices = dict(
    attenuator_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Attenuator changer",
        motorpv="TBL-AttChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimator_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLin:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimator_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLif:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole changer",
        motorpv="TBL-PinChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 1",
        motorpv="TBL-FilChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 2",
        motorpv="TBL-FilChg:MC-LinY-02:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 3",
        motorpv="TBL-FilChg:MC-LinY-03:Mtr",
        monitor_deadband=0.01,
    )
)
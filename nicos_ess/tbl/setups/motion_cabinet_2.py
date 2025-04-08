description = "Motion cabinet 2"

devices = dict(
    attenuator_changer_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Attenuator changer",
        motorpv="TBL-AttChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    attenuator_changer_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="attenuator_changer_axis",
        mapping={"attenuator_1": 0, "attenuator_2": 0, "attenuator_3": 20},
    ),
    collimator_horizontal_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLin:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimator_vertical_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLif:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_changer_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole changer",
        motorpv="TBL-PinChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    pinhole_changer_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="pinhole_changer_axis",
        mapping={"pinhole_1": 0, "pinhole_2": 0, "pinhole_3": 20},
    ),
    filter_changer_axis_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 1",
        motorpv="TBL-FilChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_controller_1=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="filter_changer_axis_1",
        mapping={"filter_1": 0, "filter_2": 0, "filter_3": 20},
    ),
    filter_changer_axis_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 2",
        motorpv="TBL-FilChg:MC-LinY-02:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_controller_2=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="filter_changer_axis_2",
        mapping={"filter_1": 0, "filter_2": 0, "filter_3": 20},
    ),
    filter_changer_axis_3=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 3",
        motorpv="TBL-FilChg:MC-LinY-03:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_controller_3=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="filter_changer_axis_3",
        mapping={"filter_1": 0, "filter_2": 0, "filter_3": 20},
    )
)
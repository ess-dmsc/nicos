description = "Filter station axes, motor temperatures and mapped positions"

devices = dict(
    bank_1_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter bank 1 axis",
        motorpv="TBL-FilChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    bank_1_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter bank 1 motor temperature",
        readpv="TBL-FilChg:MC-LinY-01:Mtr-Temp",
    ),
    config_bank_1=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Filter bank 1 discrete postions",
        controlled_device="bank_1_axis",
        mapping={
            "Blank": 1,
            "Bi: ⌀40 x 50 mm": 56.66,
            "Cd: ⌀40 x 50 mm": 131.66,
            "Sapphire: ⌀40 x 50 mm": 206.66,
        },
    ),
    bank_2_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter bank 2",
        motorpv="TBL-FilChg:MC-LinY-02:Mtr",
        monitor_deadband=0.01,
    ),
    bank_2_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter bank 2 motor temperature",
        readpv="TBL-FilChg:MC-LinY-02:Mtr-Temp",
    ),
    config_bank_2=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Filter bank 2 discrete postions",
        controlled_device="bank_2_axis",
        mapping={
            "Blank": 1,
            "Bi: ⌀50 x 25 mm": 58.91,
            "Be: ⌀50 x 40 mm": 133.91,
            "Si: ⌀40 x 50 mm": 208.91,
        },
    ),
    bank_3_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter bank 3",
        motorpv="TBL-FilChg:MC-LinY-03:Mtr",
        monitor_deadband=0.01,
    ),
    bank_3_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter bank 3 motor temperature",
        readpv="TBL-FilChg:MC-LinY-03:Mtr-Temp",
    ),
    config_bank_3=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Filter bank 3 discrete postions",
        controlled_device="bank_3_axis",
        mapping={
            "Blank": 1,
            "Bi: ⌀50 x 60 mm": 57.07,
            "Beam Monitor": 221.07,
        },
    ),
)

description = "Motion cabinet 2"

devices = dict(
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="TBL-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
    filter_changer_axis_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Filter changer 1",
        motorpv="TBL-FilChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    filter_changer_axis_1_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter changer 1 temperature",
        readpv="TBL-FilChg:MC-LinY-01:Mtr-Temp",
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
    filter_changer_axis_2_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter changer 2 temperature",
        readpv="TBL-FilChg:MC-LinY-02:Mtr-Temp",
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
    filter_changer_axis_3_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Filter changer 3 temperature",
        readpv="TBL-FilChg:MC-LinY-03:Mtr-Temp",
    ),
    filter_changer_controller_3=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="filter_changer_axis_3",
        mapping={"filter_1": 0, "filter_2": 0, "filter_3": 20},
    ),
)

description = "Collimation system for LoKI"

pv_root = "LOKI"
selector_1_pv_root = f"{pv_root}-ColCh1:"
selector_2_pv_root = f"{pv_root}-ColCh2:"
slit_set_1_pv_root = f"{pv_root}-ColSl1:"
slit_set_2_pv_root = f"{pv_root}-ColSl2:"
slit_set_3_pv_root = f"{pv_root}-ColSl3:"

devices = dict(
    collimator_selector_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear collimation guide 1 - electrical axis 3 in motion cabinet 3",
        motorpv=f"{selector_1_pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimator_selector_1_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="collimator_selector_1",
        mapping={"collimation_position": -9.23, "guide_position": 251.92},
    ),
    collimator_selector_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear collimation guide 2 - electrical axis 4 in motion cabinet 3",
        motorpv=f"{selector_2_pv_root}MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    collimator_selector_2_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="collimator_selector_2",
        mapping={"collimation_position": 310.96, "guide_position": -49.84},
    ),
    slit_set_1_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 left blade - electrical axis 1 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 right blade - electrical axis 2 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 upper blade - electrical axis 3 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 lower blade - electrical axis 4 in motion cabinet 2",
        motorpv=f"{slit_set_1_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # slit_set_1_horizontal_center=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 1 horizontal center",
    #     motorpv=f"{slit_set_1_pv_root}MC-Yc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_1_horizontal_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 1 horizontal gap",
    #     motorpv=f"{slit_set_1_pv_root}MC-Yg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_1_vertical_center=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 1 vertical center",
    #     motorpv=f"{slit_set_1_pv_root}MC-Zc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_1_vertical_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 1 vertical gap",
    #     motorpv=f"{slit_set_1_pv_root}MC-Zg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    slit_set_2_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade - electrical axis 5 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade - electrical axis 6 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade - electrical axis 7 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade - electrical axis 8 in motion cabinet 2",
        motorpv=f"{slit_set_2_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # slit_set_2_horizontal_center=device(
    #     # readable?
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 2 horizontal center",
    #     motorpv=f"{slit_set_2_pv_root}MC-Yc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_2_horizontal_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 2 horizontal gap",
    #     motorpv=f"{slit_set_2_pv_root}MC-Yg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_2_vertical_center=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 2 vertical center",
    #     motorpv=f"{slit_set_2_pv_root}MC-Zc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_2_vertical_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 2 vertical gap",
    #     motorpv=f"{slit_set_2_pv_root}MC-Zg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    slit_set_3_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 3 left blade - electrical axis 9 in motion cabinet 2",
        motorpv=f"{slit_set_3_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_3_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 3 right blade - electrical axis 10 in motion cabinet 2",
        motorpv=f"{slit_set_3_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_3_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 3 upper blade - electrical axis 11 in motion cabinet 2",
        motorpv=f"{slit_set_3_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_3_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 3 lower blade - electrical axis 12 in motion cabinet 2",
        motorpv=f"{slit_set_3_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # slit_set_3_horizontal_center=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 3 horizontal center",
    #     motorpv=f"{slit_set_3_pv_root}MC-Yc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_3_horizontal_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 3 horizontal gap",
    #     motorpv=f"{slit_set_3_pv_root}MC-Yg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_3_vertical_center=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 3 vertical center",
    #     motorpv=f"{slit_set_3_pv_root}MC-Zc-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
    # slit_set_3_vertical_gap=device(
    #     "nicos_ess.devices.epics.pva.motor.EpicsMotor",
    #     description="Collimation slit set 3 vertical gap",
    #     motorpv=f"{slit_set_3_pv_root}MC-Zg-01:Mtr",
    #     monitor_deadband=0.01,
    # ),
)

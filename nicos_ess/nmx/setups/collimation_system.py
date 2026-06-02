description = "NMX Collimation System"

pv_root = "NMX"
slit_set_1_pv_root = f"{pv_root}-ColSl1:"
slit_set_2_pv_root = f"{pv_root}-ColSl2:"
pinhole_exchanger_pv_root= f"{pv_root}-PinChg:"

# TODO: Check descriptions (axis and cabinet numbers)!

devices = dict(
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
)

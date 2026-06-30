description = "NMX Slits (Collimation System)"

pv_root = "NMX"
slit_set_1_pv_root = f"{pv_root}-ColSl1:"
slit_set_2_pv_root = f"{pv_root}-ColSl2:"

devices = dict(
    # Slit 1 blades
    slit_set_1_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 left blade",
        motorpv=f"{slit_set_1_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 right blade",
        motorpv=f"{slit_set_1_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 upper blade",
        motorpv=f"{slit_set_1_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_1_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 lower blade",
        motorpv=f"{slit_set_1_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    # Slit 1 center and gap
    slit_set_1_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal center",
        motorpv=f"{slit_set_1_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal gap",
        motorpv=f"{slit_set_1_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical center",
        motorpv=f"{slit_set_1_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_1_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical gap",
        motorpv=f"{slit_set_1_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Slit 2 blades
    slit_set_2_left_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade",
        motorpv=f"{slit_set_2_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_right_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade",
        motorpv=f"{slit_set_2_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_upper_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade",
        motorpv=f"{slit_set_2_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    slit_set_2_lower_blade=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade",
        motorpv=f"{slit_set_2_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility={},
    ),
    # Slit 2 center and gap
    slit_set_2_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal center",
        motorpv=f"{slit_set_2_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal gap",
        motorpv=f"{slit_set_2_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical center",
        motorpv=f"{slit_set_2_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_set_2_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical gap",
        motorpv=f"{slit_set_2_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
)

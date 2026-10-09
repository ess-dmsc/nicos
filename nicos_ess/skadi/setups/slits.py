description = "SKADI Collimation slits (Collimation System)"

pv_root = "SKADI"
col_slit_set_1_pv_root = f"{pv_root}-ColSl1:"
col_slit_set_2_pv_root = f"{pv_root}-ColSl2:"
col_slit_set_3_pv_root = f"{pv_root}-ColSl3:"
col_slit_set_4_pv_root = f"{pv_root}-ColSl4:"
sample_slit_set_4_pv_root = f"{pv_root}-SpSl1:"

devices = dict(
    # Collimation slit 1 blades
    col_slit_set_1_blade_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 left blade",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_blade_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 right blade",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_blade_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 upper blade",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_blade_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 lower blade",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 1 center and gap
    col_slit_set_1_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal center",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 horizontal gap",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical center",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_1_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 1 vertical gap",
        motorpv=f"{col_slit_set_1_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 2 blades
    col_slit_set_2_blade_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_blade_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_blade_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_blade_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 2 center and gap
    col_slit_set_2_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal center",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal gap",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical center",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_2_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical gap",
        motorpv=f"{col_slit_set_2_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 3 blades
    col_slit_set_3_blade_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_blade_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_blade_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_blade_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 3 center and gap
    col_slit_set_3_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal center",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal gap",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical center",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_3_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical gap",
        motorpv=f"{col_slit_set_3_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 4 blades
    col_slit_set_4_blade_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 left blade",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_blade_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 right blade",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_blade_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 upper blade",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_blade_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 lower blade",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Collimation slit 4 center and gap
    col_slit_set_4_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal center",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 horizontal gap",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical center",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_set_4_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation slit set 2 vertical gap",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Sample slit blades
    sample_slit_set_4_blade_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 left blade",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_blade_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 right blade",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_blade_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 upper blade",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_blade_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 lower blade",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    # Slit 4 center and gap
    sample_slit_set_4_horizontal_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 horizontal center",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_horizontal_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 horizontal gap",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_vertical_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 vertical center",
        motorpv=f"{sample_slit_set_4_pv_root}MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_slit_set_4_vertical_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample slit set 2 vertical gap",
        motorpv=f"{col_slit_set_4_pv_root}MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
)

# ODIN — Motion cabinet 4

description = "Motion cabinet 4"

devices = dict(
    # --- Motors: Beam limiter slit set 1 (blades + centre & gap) ---
    col_slit_1_yp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 (Y+)",
        motorpv="ODIN-ColSl1:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_1_ym=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 (Y-)",
        motorpv="ODIN-ColSl1:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_1_zp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 (Z+)",
        motorpv="ODIN-ColSl1:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_1_zm=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 (Z-)",
        motorpv="ODIN-ColSl1:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_1_hori_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 horizontal centre (Yc)",
        motorpv="ODIN-ColSl1:MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_hori_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 horizontal gap (Yg)",
        motorpv="ODIN-ColSl1:MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_vert_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 vertical centre (Zc)",
        motorpv="ODIN-ColSl1:MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_vert_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 vertical gap (Zg)",
        motorpv="ODIN-ColSl1:MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Motors: Beam limiter slit set 2 (blades + centre & gap) ---
    col_slit_2_yp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 (Y+)",
        motorpv="ODIN-ColSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_2_ym=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 (Y-)",
        motorpv="ODIN-ColSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_2_zp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 (Z+)",
        motorpv="ODIN-ColSl2:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_2_zm=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 (Z-)",
        motorpv="ODIN-ColSl2:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_2_hori_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 horizontal centre (Yc)",
        motorpv="ODIN-ColSl2:MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_hori_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 horizontal gap (Yg)",
        motorpv="ODIN-ColSl2:MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_vert_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 vertical centre (Zc)",
        motorpv="ODIN-ColSl2:MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_vert_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 vertical gap (Zg)",
        motorpv="ODIN-ColSl2:MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Motors: Beam limiter slit set 3 (blades + centre & gap) ---
    col_slit_3_yp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 (Y+)",
        motorpv="ODIN-ColSl3:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_3_ym=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 (Y-)",
        motorpv="ODIN-ColSl3:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_3_zp=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 (Z+)",
        motorpv="ODIN-ColSl3:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_3_zm=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 (Z-)",
        motorpv="ODIN-ColSl3:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        visibility=(),
    ),
    col_slit_3_hori_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 horizontal centre (Yc)",
        motorpv="ODIN-ColSl3:MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_hori_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 horizontal gap (Yg)",
        motorpv="ODIN-ColSl3:MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_vert_centre=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 vertical centre (Zc)",
        motorpv="ODIN-ColSl3:MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_vert_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 vertical gap (Zg)",
        motorpv="ODIN-ColSl3:MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Motors: Cameras ---
    camera1_distance=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Camera: Distance (Z)",
        motorpv="ODIN-CmDis1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    camera1_focus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Camera: Focus (Rz)",
        motorpv="ODIN-CmFoc1:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    camera2_distance=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Camera: Distance (Z)",
        motorpv="ODIN-CmDis2:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    camera2_focus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Camera: Focus (Rz)",
        motorpv="ODIN-CmFoc2:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Cabinet health ---
    cabinet_4_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 4 status",
        pv_root="ODIN-MCS4:MC-MCU-04:Cabinet",
        number_of_bits=24,
    ),
)

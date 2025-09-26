# ODIN — Motion cabinet 4

description = "Motion cabinet 4"

devices = dict(
    # --- Motors: Beam limiter slit sets 1–3 ---
    col_slit_1_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 left (Y+)",
        motorpv="ODIN-ColSl1:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 right (Y-)",
        motorpv="ODIN-ColSl1:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 upper (Z+)",
        motorpv="ODIN-ColSl1:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_1_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 1 lower (Z-)",
        motorpv="ODIN-ColSl1:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 left (Y+)",
        motorpv="ODIN-ColSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 right (Y-)",
        motorpv="ODIN-ColSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 upper (Z+)",
        motorpv="ODIN-ColSl2:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_2_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 2 lower (Z-)",
        motorpv="ODIN-ColSl2:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_left=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 left (Y+)",
        motorpv="ODIN-ColSl3:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_right=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 right (Y-)",
        motorpv="ODIN-ColSl3:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_upper=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 upper (Z+)",
        motorpv="ODIN-ColSl3:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    col_slit_3_lower=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimation Slit 3 lower (Z-)",
        motorpv="ODIN-ColSl3:MC-SlZm-01:Mtr",
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
    cabinet_4_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 4 pressure 1",
        readpv="ODIN-MCS4:MC-MCU-04:Pressure1",
    ),
    cabinet_4_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 4 pressure 2",
        readpv="ODIN-MCS4:MC-MCU-04:Pressure2",
    ),
)

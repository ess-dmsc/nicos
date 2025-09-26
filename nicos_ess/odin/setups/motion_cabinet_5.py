# ODIN — Motion cabinet 5

description = "Motion cabinet 5"

devices = dict(
    # --- Motors: Large sample stage (SpSt1) ---
    spst1_lin_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Linear Z",
        motorpv="ODIN-SpSt1:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst1_lin_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Linear X",
        motorpv="ODIN-SpSt1:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst1_lin_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Linear Y",
        motorpv="ODIN-SpSt1:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst1_rot_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Goniometer Rx",
        motorpv="ODIN-SpSt1:MC-RotX-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst1_rot_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Goniometer Ry",
        motorpv="ODIN-SpSt1:MC-RotY-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst1_rot_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Large Sample Stage: Rotary Rz",
        motorpv="ODIN-SpSt1:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Motors: Small sample stage (SpSt2) ---
    spst2_lin_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Linear Z",
        motorpv="ODIN-SpSt2:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst2_lin_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Linear X",
        motorpv="ODIN-SpSt2:MC-LinX-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst2_lin_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Linear Y",
        motorpv="ODIN-SpSt2:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst2_rot_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Goniometer Rx",
        motorpv="ODIN-SpSt2:MC-RotX-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst2_rot_y=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Goniometer Ry",
        motorpv="ODIN-SpSt2:MC-RotY-01:Mtr",
        monitor_deadband=0.01,
    ),
    spst2_rot_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Small Sample Stage: Rotary Rz",
        motorpv="ODIN-SpSt2:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Motors: Ancillary stages ---
    anc_linear_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ancillary Stage: Linear 1",
        motorpv="ODIN-AncSt1:MC-Lin-01:Mtr",
        monitor_deadband=0.01,
    ),
    anc_linear_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ancillary Stage: Linear 2",
        motorpv="ODIN-AncSt2:MC-Lin-01:Mtr",
        monitor_deadband=0.01,
    ),
    anc_goniometer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ancillary Stage: Goniometer",
        motorpv="ODIN-AncGon:MC-Rot-01:Mtr",
        monitor_deadband=0.01,
    ),
    anc_rotary=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Ancillary Stage: Rotary",
        motorpv="ODIN-AncRot:MC-Rot-01:Mtr",
        monitor_deadband=0.01,
    ),
    # --- Cabinet health ---
    cabinet_5_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 5 status",
        pv_root="ODIN-MCS5:MC-MCU-05:Cabinet",
        number_of_bits=24,
    ),
)

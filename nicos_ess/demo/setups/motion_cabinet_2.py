# ruff: noqa: F821
description = "The motors for alignment in the DEMO cave"


# slit motors
# DEMO-DivSl2:MC-SlYp-01:Mtr
# DEMO-DivSl2:MC-SlYm-01:Mtr
# DEMO-DivSl2:MC-SlZp-01:Mtr
# DEMO-DivSl2:MC-SlZm-01:Mtr

# slit virtual motors
# DEMO-DivSl2:MC-SlYc-01:Mtr
# DEMO-DivSl2:MC-SlYg-01:Mtr
# DEMO-DivSl2:MC-SlZc-01:Mtr
# DEMO-DivSl2:MC-SlZg-01:Mtr

# linear stage
# DEMO-BmScn:MC-LinY-01:Mtr

# rotation stage
# DEMO-SpRot:MC-RotZ-01:Mtr

# sample changer
# DEMO-SpChg:MC-LinY-01:Mtr


devices = dict(
    linear_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear stage",
        motorpv="DEMO-BmScn:MC-LinY-01:Mtr",
        nexus_config=[
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "mm",
                "suffix": "readback",
                "source_name": "DEMO-BmScn:MC-LinY-01:Mtr.RBV",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "mm",
                "suffix": "setpoint",
                "source_name": "DEMO-BmScn:MC-LinY-01:Mtr.VAL",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "m/s",
                "suffix": "speed",
                "source_name": "DEMO-BmScn:MC-LinY-01:Mtr.VELO",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
        ],
        monitor_deadband=0.01,
    ),
    rotation_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotation stage",
        motorpv="DEMO-SpRot:MC-RotZ-01:Mtr",
        nexus_config=[
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "deg",
                "suffix": "readback",
                "source_name": "DEMO-SpRot:MC-RotZ-01:Mtr.RBV",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "deg",
                "suffix": "setpoint",
                "source_name": "DEMO-SpRot:MC-RotZ-01:Mtr.VAL",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "deg/s",
                "suffix": "speed",
                "source_name": "DEMO-SpRot:MC-RotZ-01:Mtr.VELO",
                "schema": "f144",
                "topic": "DEMO_motion",
                "protocol": "pva",
                "periodic": 1,
                "dataset_type": "nx_log",
            },
        ],
        monitor_deadband=0.01,
    ),
    sample_changer_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample changer",
        motorpv="DEMO-SpChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    sample_changer_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="sample_changer_axis",
        description="No description available.",
        mapping={"sample_1": 0, "sample_2": 10, "sample_3": 20},
    ),
    slit_y_plus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y+",
        motorpv="DEMO-DivSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_y_minus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y-",
        motorpv="DEMO-DivSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_z_plus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z+",
        motorpv="DEMO-DivSl2:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_z_minus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z-",
        motorpv="DEMO-DivSl2:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_y_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y center",
        motorpv="DEMO-DivSl2:MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_y_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y gap",
        motorpv="DEMO-DivSl2:MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_z_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z center",
        motorpv="DEMO-DivSl2:MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
    ),
    slit_z_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z gap",
        motorpv="DEMO-DivSl2:MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
    ),
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root="DEMO-MCS2:MC-MCU-02:Cabinet",
        number_of_bits=24,
    ),
    cabinet_2_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 1",
        readpv="DEMO-MCS2:MC-MCU-02:Pressure1",
    ),
    cabinet_2_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 2",
        readpv="DEMO-MCS2:MC-MCU-02:Pressure2",
    ),
)

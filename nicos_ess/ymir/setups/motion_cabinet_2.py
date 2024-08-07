# ruff: noqa: F821
description = "The motors for alignment in the YMIR cave"


# slit motors
# YMIR-DivSl2:MC-SlYp-01:Mtr
# YMIR-DivSl2:MC-SlYm-01:Mtr
# YMIR-DivSl2:MC-SlZp-01:Mtr
# YMIR-DivSl2:MC-SlZm-01:Mtr

# slit virtual motors
# YMIR-DivSl2:MC-SlYc-01:Mtr
# YMIR-DivSl2:MC-SlYg-01:Mtr
# YMIR-DivSl2:MC-SlZc-01:Mtr
# YMIR-DivSl2:MC-SlZg-01:Mtr

# linear stage
# YMIR-BmScn:MC-LinY-01:Mtr

# rotation stage
# YMIR-SpRot:MC-RotZ-01:Mtr

# sample changer
# YMIR-SpChg:MC-LinY-01:Mtr


devices = dict(
    linear_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Linear stage",
        motorpv="YMIR-BmScn:MC-LinY-01:Mtr",
        nexus_config=[
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "mm",
                "suffix": "readback",
                "source_name": "YMIR-BmScn:MC-LinY-01:Mtr.RBV",
                "schema": "f144",
                "topic": "ymir_motion",
                "protocol": "pva",
                "periodic": 1,
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "mm",
                "suffix": "setpoint",
                "source_name": "YMIR-BmScn:MC-LinY-01:Mtr.VAL",
                "schema": "f144",
                "topic": "ymir_motion",
                "protocol": "pva",
                "periodic": 1,
            },
            {
                "group_name": "motion_cabinet_2",
                "nx_class": "NXpositioner",
                "units": "m/s",
                "suffix": "speed",
                "source_name": "YMIR-BmScn:MC-LinY-01:Mtr.VELO",
                "schema": "f144",
                "topic": "ymir_motion",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    rotation_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Rotation stage",
        motorpv="YMIR-SpRot:MC-RotZ-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    sample_changer_axis=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample changer",
        motorpv="YMIR-SpChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    sample_changer_controller=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        controlled_device="sample_changer_axis",
        mapping={"sample_1": 0, "sample_2": 10, "sample_3": 20},
    ),
    slit_y_plus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y+",
        motorpv="YMIR-DivSl2:MC-SlYp-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_y_minus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y-",
        motorpv="YMIR-DivSl2:MC-SlYm-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_z_plus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z+",
        motorpv="YMIR-DivSl2:MC-SlZp-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_z_minus=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z-",
        motorpv="YMIR-DivSl2:MC-SlZm-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_y_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y center",
        motorpv="YMIR-DivSl2:MC-SlYc-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_y_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Y gap",
        motorpv="YMIR-DivSl2:MC-SlYg-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_z_center=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z center",
        motorpv="YMIR-DivSl2:MC-SlZc-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
    slit_z_gap=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Z gap",
        motorpv="YMIR-DivSl2:MC-SlZg-01:Mtr",
        monitor_deadband=0.01,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
)

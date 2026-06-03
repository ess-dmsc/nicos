description = "The middle focus mask changer"
prefix = "ESTIA-Chg:MC-"

devices = dict(
    horizontal_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Horizontal adjustment of the mask changer",
        motorpv=f"{prefix}LinY01:Mtr",
        visibility=(),
    ),
    vertical_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Vertical adjustment of the mask changer",
        motorpv=f"{prefix}LinZ01:Mtr",
        visibility=(),
    ),
    mask_changer_rot=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="In-Beam changer",
        motorpv=f"{prefix}RotX01:Mtr",
        visibility=(),
    ),
    laser=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="device to turn on and off the VS laser",
        readpv="ESTIA-SES:Ctrl-IM-100:LaserEnable",
        writepv="ESTIA-SES:Ctrl-IM-100:LaserEnable",
    ),
    laser_readback=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="readback value of the VS laser",
        readpv="ESTIA-SES:Ctrl-IM-100:LaserEnabled",
    ),
    mask_changer_macro=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Preset mappings for the mask changer",
        controlled_device="mask_changer_rot",
        mapping={"Middle": 176.5},
    ),
    # Temperature Readouts
    mask_changer_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Mask Changer Rotation Temp",
        readpv=f"{prefix}RotX01:Mtr-Temp",
        visibility=(),
    ),
)

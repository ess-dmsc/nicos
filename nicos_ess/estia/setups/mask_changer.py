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
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        description="Preset mappings for the mask changer"
        "\ndevice order: horizontal, vertical, rotation",
        controlled_devices=[
            "horizontal_adjust",
            "vertical_adjust",
            "mask_changer_rot",
        ],
        mapping={
            "Scintillator (Mask 1)": (-0.1335, 12.3329, 138.1799),
            "Pinhole (Mask 2)": (-0.1335, 12.3329, 183.1903),
            "Horizontal Slit (Mask 3)": (-0.1335, 12.3329, 228.1803),
            "Vertical Slit (Mask 4)": (-0.1335, 12.3329, 273.1803),
            "Empty (Mask 5)": (-0.1335, 12.3329, 318.1803),
            "Crosshair (Mask 6)": (-0.1335, 12.3729, 3.1799),
            "Mirror (Mask 7)": (-0.1335, 12.3729, 48.1799),
            "Empty (Mask 8)": (-0.1335, 12.3329, 93.1799),
        },
    ),
    # Temperature Readouts
    mask_changer_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Mask Changer Rotation Temp",
        readpv=f"{prefix}RotX01:Mtr-Temp",
        visibility=(),
    ),
)

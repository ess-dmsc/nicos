description = "The middle focus polarizer"
pv_root = "ESTIA-PolChg:MC-"

devices = dict(
    polarizer_lin_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer in-beam changer",
        motorpv=f"{pv_root}LinY01:Mtr",
        visibility=(),
    ),
    polarizer_angular_adjustment=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer angular adjustment",
        motorpv=f"{pv_root}RotZ01:Mtr",
        visibility=(),
    ),
    polarizer_macro=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        description="Preset mappings for the mask changer"
        "\ndevice order: linear, angular",
        controlled_devices=[
            "polarizer_lin_stage",
            "polarizer_angular_adjustment",
        ],
        mapping={"Position 0": (0, 0)},
    ),
    # Temperature Readouts
    polarizer_lin_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Polarizer LinY Temp",
        readpv=f"{pv_root}LinY01:Mtr-Temp",
        visibility=(),
    ),
    polarizer_rot_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Polarizer RotZ Temp",
        readpv=f"{pv_root}RotZ01:Mtr-Temp",
        visibility=(),
    ),
)

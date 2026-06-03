description = "Polarizer"
pv_root = "ESTIA-PolChg:MC-"

devices = dict(
    polarizer_lin_stage=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer in-beam changer",
        motorpv=f"{pv_root}LinY01:Mtr",
    ),
    angular_adjustment=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Polarizer angular adjustment",
        motorpv=f"{pv_root}RotZ01:Mtr",
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

description = "The Virtual Source Slit Set"

pv_root_1 = "ESTIA-VSSlP:MC-"
pv_root_2 = "ESTIA-VSSlN:MC-"

devices = dict(
    right_top_blade_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 1 (right-top) / Horizontal",
        motorpv=f"{pv_root_1}LinX-01:Mtr",
    ),
    right_top_blade_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 1 (right-top) / Vertical",
        motorpv=f"{pv_root_1}LinZ-01:Mtr",
    ),
    left_bottom_blade_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 2 (lef-bottom)/ Horizontal",
        motorpv=f"{pv_root_2}LinX-01:Mtr",
    ),
    left_bottom_blade_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 2 (left-bottom) / Vertical",
        motorpv=f"{pv_root_2}LinZ-01:Mtr",
    ),
    vs_slit_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Rotation around z axis",
        motorpv="ESTIA-VSRot:MC-RotZ-01:Mtr",
    ),
    vs_controller=device(
        "nicos.devices.generic.slit.Slit",
        opmode="centered",
        description="Virtual Source Slit Controller",
        left="left_bottom_blade_horizontal",
        right="right_top_blade_horizontal",
        top="right_top_blade_vertical",
        bottom="left_bottom_blade_vertical",
    ),
)

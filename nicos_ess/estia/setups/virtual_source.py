description = "The Virtual Source Slit Set"

pv_root_1 = "ESTIA-VSSlP:MC-"
pv_root_2 = "ESTIA-VSSlN:MC-"

devices = dict(
    right_top_blade_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 1 (right-top) / Horizontal",
        motorpv=f"{pv_root_1}LinX-01:Mtr",
        visibility=(),
    ),
    right_top_blade_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 1 (right-top) / Vertical",
        motorpv=f"{pv_root_1}LinZ-01:Mtr",
        visibility=(),
    ),
    left_bottom_blade_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 2 (lef-bottom)/ Horizontal",
        motorpv=f"{pv_root_2}LinX-01:Mtr",
        visibility=(),
    ),
    left_bottom_blade_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Blade 2 (left-bottom) / Vertical",
        motorpv=f"{pv_root_2}LinZ-01:Mtr",
        visibility=(),
    ),
    vs_slit_rotation=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="VS - Rotation around z axis",
        motorpv="ESTIA-VSRot:MC-RotZ-01:Mtr",
    ),
    slit=device(
        "nicos.devices.generic.slit.Slit",
        opmode="offcentered",
        description="Slit device to control the vs slit pair",
        left="left_bottom_blade_horizontal",
        right="right_top_blade_horizontal",
        bottom="right_top_blade_vertical",
        top="left_bottom_blade_vertical",
    ),
    virtual_source=device(
        "nicos_ess.estia.devices.virtual_source.VSCalculator",
        description="Reads the virtual source slit's width and height",
        slit="slit",
        rot="vs_slit_rotation",
    ),
)

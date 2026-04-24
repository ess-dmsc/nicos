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
        visibility=(),
    ),
    slit=device(
        "nicos.devices.generic.slit.Slit",
        opmode="4blades",
        description="Slit device to control the VS slit pair",
        left="left_bottom_blade_horizontal",
        right="right_top_blade_horizontal",
        bottom="right_top_blade_vertical",
        top="left_bottom_blade_vertical",
        visibility=(),
    ),
    virtual_source=device(
        "nicos_ess.estia.devices.virtual_source.VirtualSource",
        description="Reads the virtual source slit gaps and current angle",
        slit="slit",
        rot="vs_slit_rotation",
        opmode="centered",
    ),
    # Temperature Readouts
    right_horizontal_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Right Top Horizontal Motor Temp",
        readpv=f"{pv_root_1}LinX-01:Mtr-Temp",
        visibility=(),
    ),
    right_vertical_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Right Top Vertical Motor Temp",
        readpv=f"{pv_root_1}LinZ-01:Mtr-Temp",
        visibility=(),
    ),
    left_horizontal_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Left Bottom Horizontal Motor Temp",
        readpv=f"{pv_root_2}LinX-01:Mtr-Temp",
        visibility=(),
    ),
    left_vertical_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Left Bottom Vertical Motor Temp",
        readpv=f"{pv_root_2}LinZ-01:Mtr-Temp",
        visibility=(),
    ),
    vs_rotation_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Virtual Source Rotation Motor Temp",
        readpv="ESTIA-VSRot:MC-RotZ-01:Mtr-Temp",
        visibility=(),
    ),
)

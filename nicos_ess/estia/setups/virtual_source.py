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
        description="Slit device to control the vs slit pair",
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
)

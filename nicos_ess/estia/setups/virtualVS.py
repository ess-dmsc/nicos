description = "The Virtual Source Slit Set"

pv_root_1 = "IOC:"


devices = dict(
    right_top_blade_horizontal=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 1 (right-top) / Horizontal",
        # motorpv=f"{pv_root_1}m1",
        abslimits=(-25, 0.0),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    right_top_blade_vertical=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 1 (right-top) / Vertical",
        # motorpv=f"{pv_root_1}m2",
        abslimits=(-8.5, 8.5),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    left_bottom_blade_horizontal=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 2 (lef-bottom)/ Horizontal",
        # motorpv=f"{pv_root_1}m3",
        abslimits=(0, 25),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    left_bottom_blade_vertical=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 2 (left-bottom) / Vertical",
        # motorpv=f"{pv_root_1}m4",
        abslimits=(-8.5, 8.5),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    slit_rotation=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Rotation around z axis",
        # motorpv=f"{pv_root_1}m5",
        abslimits=(-2, 15),
        speed=1,
        unit="deg",
    ),
    ####Controller Device 4-blade Slit
    four_blade_slit=device(
        "nicos.devices.generic.slit.Slit",
        opmode="centered",
        description="4-blade slit controller",
        top="right_top_blade_vertical",
        bottom="left_bottom_blade_vertical",
        right="left_bottom_blade_horizontal",
        left="right_top_blade_horizontal",
    ),
    ####Readout Devices
    vs_readout=device(
        "nicos_ess.estia.devices.v_source.VSCalculator",
        description="readout for the slit dimensions using 4 blade slit controls",
        slit="four_blade_slit",
        rot="slit_rotation",
        unit="mm",
        fmtstr="[%.3f x %.3f]",
    ),
    vs_controller=device(
        "nicos_ess.estia.devices.v_source.VirtualSlit",
        description="readout for the slit dimensions using 4 blade slit controls",
        slit="four_blade_slit",
        rot="slit_rotation",
    ),
)

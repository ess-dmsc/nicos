description = "The Virtual Source Slit Set"

pv_root_1 = "IOC:"


devices = dict(
    right_blade_horizontal_v=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 1 (right-top) / Horizontal",
        # motorpv=f"{pv_root_1}m1",
        abslimits=(0, 25),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    right_blade_vertical_v=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 1 (right-top) / Vertical",
        # motorpv=f"{pv_root_1}m2",
        abslimits=(-8.5, 8.5),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    left_blade_horizontal_v=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 2 (lef-bottom)/ Horizontal",
        # motorpv=f"{pv_root_1}m3",
        abslimits=(-25, 0.0),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    left_blade_vertical_v=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Blade 2 (left-bottom) / Vertical",
        # motorpv=f"{pv_root_1}m4",
        abslimits=(-8.5, 8.5),
        speed=1,
        unit="mm",
        visibility=(),
    ),
    slit_rotation_v=device(
        # "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        "nicos.devices.generic.virtual.VirtualMotor",
        description="VS - Rotation around z axis",
        # motorpv=f"{pv_root_1}m5",
        abslimits=(-2, 15),
        speed=1,
        unit="deg",
    ),
    ####Controller Device 4-blade Slit
    four_blade_slit_v=device(
        "nicos.devices.generic.slit.Slit",
        description="4-blade slit controller",
        top="right_blade_vertical_v",
        bottom="left_blade_vertical_v",
        left="left_blade_horizontal_v",
        right="right_blade_horizontal_v",
    ),
    ####Readout Devices
    vs_controller_v=device(
        "nicos_ess.estia.devices.virtual_source.VirtualSource",
        description="controller for the slit dimensions using 4 blade slit controls",
        slit="four_blade_slit_v",
        rot="slit_rotation_v",
    ),
)

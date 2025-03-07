description = "IPC slit after mono2 shielding"
group = "lowlevel"

tango_base = "tango://miractrl.mira.frm2.tum.de:10000/mira/"

devices = dict(
    ms2bus=device(
        "nicos.devices.vendor.ipc.IPCModBusTango",
        tangodevice=tango_base + "ms2/bio",
        visibility=(),
    ),
    # NOTE: this slit is mounted upside-down -- therefore the
    # left/right/top/bottom axis sides are switched
    ms2_l_mot=device(
        "nicos.devices.vendor.ipc.SlitMotor",
        visibility=(),
        bus="ms2bus",
        addr=0x88,
        side=3,
        slope=-80.0,
        zerosteps=1150,
        resetpos=-20,
        abslimits=(-32, 13),
    ),
    ms2_r_mot=device(
        "nicos.devices.vendor.ipc.SlitMotor",
        visibility=(),
        bus="ms2bus",
        addr=0x88,
        side=2,
        slope=80.0,
        zerosteps=1170,
        resetpos=20,
        abslimits=(-13, 32),
    ),
    ms2_b_mot=device(
        "nicos.devices.vendor.ipc.SlitMotor",
        visibility=(),
        bus="ms2bus",
        addr=0x88,
        side=1,
        slope=-40.0,
        zerosteps=780,
        resetpos=-45,
        abslimits=(-70, 19),
    ),
    ms2_t_mot=device(
        "nicos.devices.vendor.ipc.SlitMotor",
        visibility=(),
        bus="ms2bus",
        addr=0x88,
        side=0,
        slope=40.0,
        zerosteps=770,
        resetpos=45,
        abslimits=(-17, 70),
    ),
    ms2_l=device(
        "nicos.devices.generic.Axis",
        visibility=(),
        precision=0.1,
        backlash=-2.0,
        motor="ms2_l_mot",
    ),
    ms2_r=device(
        "nicos.devices.generic.Axis",
        visibility=(),
        precision=0.1,
        backlash=2.0,
        motor="ms2_r_mot",
    ),
    ms2_b=device(
        "nicos.devices.generic.Axis",
        visibility=(),
        precision=0.1,
        backlash=-2.0,
        motor="ms2_b_mot",
    ),
    ms2_t=device(
        "nicos.devices.generic.Axis",
        visibility=(),
        precision=0.1,
        backlash=2.0,
        motor="ms2_t_mot",
    ),
    ms2=device(
        "nicos.devices.generic.Slit",
        description="slit after monochromator Mira2 in shielding table",
        left="ms2_l",
        right="ms2_r",
        bottom="ms2_b",
        top="ms2_t",
        opmode="offcentered",
        pollinterval=5,
        maxage=10,
    ),
)

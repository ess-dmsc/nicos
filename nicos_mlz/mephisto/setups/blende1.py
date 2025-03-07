description = "sample slit devices"

includes = ["system"]

tango_base = "tango://mephistosrv.mephisto.frm2.tum.de:10000/mephisto/aperture1/"

devices = dict(
    edge1=device(
        "nicos.devices.entangle.Motor",
        description="top edge",
        tangodevice=tango_base + "motor1",
        fmtstr="%7.3f",
        abslimits=(-100, 100),
        visibility=(),
    ),
    edge2=device(
        "nicos.devices.entangle.Motor",
        description="bottom edge",
        tangodevice=tango_base + "motor2",
        fmtstr="%7.3f",
        abslimits=(-100, 100),
        visibility=(),
    ),
    edge3=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "motor3",
        fmtstr="%7.3f",
        abslimits=(-100, 100),
        visibility=(),
    ),
    edge4=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "motor4",
        fmtstr="%7.3f",
        abslimits=(-100, 100),
        visibility=(),
    ),
    e1=device(
        "nicos.devices.generic.Axis",
        motor="edge1",
        precision=0.1,
        visibility=(),
    ),
    e2=device(
        "nicos.devices.generic.Axis",
        motor="edge2",
        precision=0.1,
        visibility=(),
    ),
    e3=device(
        "nicos.devices.generic.Axis",
        motor="edge3",
        precision=0.1,
        visibility=(),
    ),
    e4=device(
        "nicos.devices.generic.Axis",
        motor="edge4",
        precision=0.1,
        visibility=(),
    ),
    b1=device(
        "nicos.devices.generic.Slit",
        description="first slit",
        top="e1",
        bottom="e2",
        right="e3",
        left="e4",
    ),
)

description = "Huber sample slits"
group = "lowlevel"

tango_base = "tango://miractrl.mira.frm2.tum.de:10000/mira/"

devices = dict(
    ss1r=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/left1",
        abslimits=(-35, 65),
        precision=0.1,
    ),
    ss1l=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/right1",
        abslimits=(-65, 35),
        precision=0.1,
    ),
    ss1b=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/bottom1",
        abslimits=(-65, 35),
        precision=0.1,
    ),
    ss1t=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/top1",
        abslimits=(-35, 65),
        precision=0.1,
    ),
    ss1=device(
        "nicos.devices.generic.Slit",
        description="First sample slit",
        left="ss1l",
        right="ss1r",
        bottom="ss1b",
        top="ss1t",
        opmode="offcentered",
        pollinterval=5,
        maxage=10,
    ),
    ss2r=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/left2",
        abslimits=(-35, 65),
        precision=0.1,
    ),
    ss2l=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/right2",
        abslimits=(-65, 35),
        precision=0.1,
    ),
    ss2b=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/bottom2",
        abslimits=(-65, 35),
        precision=0.1,
    ),
    ss2t=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "slit/top2",
        abslimits=(-35, 65),
        precision=0.1,
    ),
    ss2=device(
        "nicos.devices.generic.Slit",
        description="Second sample slit",
        left="ss2l",
        right="ss2r",
        bottom="ss2b",
        top="ss2t",
        opmode="offcentered",
        pollinterval=5,
        maxage=10,
    ),
)

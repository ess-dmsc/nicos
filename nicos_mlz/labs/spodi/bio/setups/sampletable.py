description = "Sample table devices"

setup = "lowlevel"

tango_base = "tango://motorbox10.spodi.frm2.tum.de:10000/box/"

devices = dict(
    omgs_motor=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "omgs/motor",
        visibility=(),
    ),
    omgs_coder=device(
        "nicos.devices.entangle.Sensor",
        tangodevice=tango_base + "omgs/encoder",
        visibility=(),
    ),
    omgs=device(
        "nicos.devices.generic.Axis",
        description="Omega sample rotation",
        motor="omgs_motor",
        coder="omgs_coder",
        precision=0.01,
    ),
    rx_motor=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "rx/motor",
        visibility=(),
    ),
    rx=device(
        "nicos.devices.generic.Axis",
        description="RX goniometer tilt",
        motor="rx_motor",
        precision=0.01,
    ),
    ry_motor=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "ry/motor",
        visibility=(),
    ),
    ry=device(
        "nicos.devices.generic.Axis",
        description="RY goniometer tilt",
        motor="ry_motor",
        precision=0.01,
    ),
    x_motor=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "x/motor",
        visibility=(),
    ),
    x=device(
        "nicos.devices.generic.Axis",
        description="X sample translation",
        motor="x_motor",
        precision=0.01,
    ),
    y_motor=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "y/motor",
        visibility=(),
    ),
    y=device(
        "nicos.devices.generic.Axis",
        description="Y sample translation",
        motor="y_motor",
        precision=0.01,
    ),
)

description = "HUBER Sample Table Experimental Chamber 1"

group = "lowlevel"

devices = dict(
    stx_huber=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Translation X",
        precision=0.01,
        abslimits=(0, 400),
        pollinterval=5,
        maxage=12,
        unit="mm",
        speed=10,
    ),
    sty_huber=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Translation Y",
        precision=0.01,
        abslimits=(0, 400),
        pollinterval=5,
        maxage=12,
        unit="mm",
        speed=10,
    ),
    sgx_huber=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Rotation around X",
        precision=0.01,
        abslimits=(-10, 10),
        pollinterval=5,
        maxage=12,
        unit="deg",
        speed=0.5,
    ),
    sgz_huber=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Rotation around Z",
        precision=0.01,
        abslimits=(-10, 10),
        pollinterval=5,
        maxage=12,
        unit="deg",
        speed=0.5,
    ),
    sry_huber=device(
        "nicos.devices.generic.VirtualMotor",
        description="Sample Rotation around Y",
        precision=0.01,
        abslimits=(-999999, 999999),
        pollinterval=5,
        maxage=12,
        unit="deg",
        speed=10,
    ),
)

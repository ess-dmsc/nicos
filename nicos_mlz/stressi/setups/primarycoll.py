description = "Primary radial collimator"

group = "optional"

excludes = ["primaryslit_huber", "primaryslit_manual"]

tango_base = "tango://motorbox05.stressi.frm2.tum.de:10000/box/"

devices = dict(
    coll_vert_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel5/motor",
        speed=0.5,
        fmtstr="%.2f",
        visibility=(),
    ),
    coll_vert=device(
        "nicos.devices.generic.Axis",
        description="Primary radial collimator vertical tilt",
        motor="coll_vert_m",
        fmtstr="%.2f",
        precision=0.01,
    ),
    coll_hor_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel6/motor",
        speed=0.5,
        fmtstr="%.2f",
        visibility=(),
    ),
    coll_hor=device(
        "nicos.devices.generic.Axis",
        description="Primary radial collimator horizontal tilt",
        motor="coll_hor_m",
        fmtstr="%.2f",
        precision=0.01,
    ),
    coll_rot_m=device(
        "nicos.devices.entangle.Motor",
        tangodevice=tango_base + "channel7/motor",
        speed=0.015,
        fmtstr="%.2f",
        visibility=(),
    ),
    coll_rot=device(
        "nicos.devices.generic.Axis",
        description="Primary radial collimator rotation",
        motor="coll_rot_m",
        fmtstr="%.2f",
        precision=0.01,
    ),
    gv_coll=device(
        "nicos.devices.generic.TwoAxisSlit",
        description="Gauge volume primary collimator",
        fmtstr="%.2f x %.2f",
        horizontal=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                fmtstr="%.1f",
                curvalue=1,
                unit="mm",
                abslimits=(0, 20),
                speed=0.0,
                requires={"level": "admin"},
            ),
            precision=0.1,
        ),
        vertical=device(
            "nicos.devices.generic.Axis",
            motor=device(
                "nicos.devices.generic.VirtualMotor",
                fmtstr="%.1f",
                curvalue=3,
                unit="mm",
                abslimits=(0, 20),
                speed=0.0,
                requires={"level": "admin"},
            ),
            precision=0.1,
        ),
    ),
)

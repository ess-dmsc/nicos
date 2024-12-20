description = "Selector Tower Movement"

group = "lowlevel"

devices = dict(
    selector_ng_ax=device(
        "nicos.devices.generic.Axis",
        description="selector neutron guide axis",
        motor="selector_ng_mot",
        precision=0.1,
        fmtstr="%.2f",
        maxage=120,
        pollinterval=15,
        visibility=(),
        requires=dict(level="admin"),
    ),
    selector_ng_mot=device(
        "nicos.devices.generic.VirtualMotor",
        description="selector neutron guide motor",
        fmtstr="%.2f",
        abslimits=(-140, 142.5),
        visibility=(),
        requires=dict(level="admin"),
        curvalue=2.4,
        unit="mm",
    ),
    selector_ng=device(
        "nicos.devices.generic.Switcher",
        description="selector neutron guide switcher",
        moveable="selector_ng_ax",
        mapping={"SEL1 NVS042": -137.6, "NG": 2.4, "SEL2 NVS020": 142.4},
        precision=0.01,
        requires=dict(level="admin"),
    ),
    selector_tilt=device(
        "nicos.devices.generic.Axis",
        description="selector tilt axis",
        motor="selector_tilt_mot",
        precision=0.05,
        fmtstr="%.2f",
        abslimits=(-7.5 + 2.27, 7.5 + 2.27),
        maxage=120,
        pollinterval=15,
        requires=dict(level="admin"),
    ),
    selector_tilt_mot=device(
        "nicos.devices.generic.VirtualMotor",
        description="selector tilt motor",
        fmtstr="%.2f",
        abslimits=(-10, 10),
        visibility=(),
        requires=dict(level="admin"),
        unit="deg",
    ),
)

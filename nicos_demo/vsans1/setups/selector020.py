description = "setup for the 6% velocity selector"

group = "optional"

includes = ["resolution", "alias_lambda"]

excludes = ["selector042"]

devices = dict(
    selector_rpm=device(
        "nicos.devices.generic.VirtualMotor",
        description="Selector speed control",
        abslimits=(3100, 28300),
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(3099, 28310),
        curvalue=4000,
        precision=10,
        jitter=10,
        maxage=35,
    ),
    selector_lambda=device(
        "nicos.devices.vendor.astrium.SelectorLambda",
        description="Selector center wavelength control",
        seldev="selector_rpm",
        unit="A",
        fmtstr="%.2f",
        twistangle=48.3,
        length=0.25,
        beamcenter=0.123,
        maxspeed=28300,
        precision=0.01,
        maxage=35,
    ),
    selector_vacuum=device(
        "nicos.devices.generic.ManualMove",
        description="Vacuum in the selector",
        unit="x1e-3 mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.008),
        abslimits=(0, 1000),
        default=1.23e-5,
        maxage=35,
    ),
    selector_rtemp=device(
        "nicos.devices.generic.ManualMove",
        description="Temperature of the selector",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(10, 45),
        abslimits=(0, 100),
        default=35,
        maxage=35,
    ),
    selector_wflow=device(
        "nicos.devices.generic.ManualMove",
        description="Cooling water flow rate through selector",
        unit="l/min",
        fmtstr="%.1f",
        warnlimits=(1.5, 10),
        abslimits=(0, 100),
        default=10.1,
        maxage=35,
    ),
    selector_winlt=device(
        "nicos.devices.generic.ManualMove",
        description="Cooling water temperature at inlet",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(15, 28),
        abslimits=(0, 100),
        default=15.1,
        maxage=35,
    ),
    selector_woutt=device(
        "nicos.devices.generic.ManualMove",
        description="Cooling water temperature at outlet",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(15, 28),
        abslimits=(0, 100),
        default=27.8,
        maxage=35,
    ),
    selector_vibrt=device(
        "nicos.devices.generic.ManualMove",
        description="Selector vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 1),
        abslimits=(0, 5),
        default=0.1,
        maxage=35,
    ),
)

alias_config = {"wl": {"selector_lambda": 100}}

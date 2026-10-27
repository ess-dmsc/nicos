description = "Virtual motor for testing (no EPICS)."

devices = dict(
    virtual_motor=device(
        "nicos.devices.generic.virtual.VirtualMotor",
        description="Simulated motor axis",
        abslimits=(-100, 100),
        userlimits=(-100, 100),
        unit="mm",
        speed=5,
        precision=0.01,
        fmtstr="%.3f",
    ),
)

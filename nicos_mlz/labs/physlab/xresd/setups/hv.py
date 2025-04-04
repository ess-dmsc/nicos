description = "hv generator"
group = "optional"
display_order = 70

tango_base = configdata("instrument.values")["tango_base"] + "box/bruker/"

devices = dict(
    gen_voltage=device(
        "nicos.devices.entangle.PowerSupply",
        description="Voltage generator",
        tangodevice=tango_base + "gen_voltage",
        fmtstr="%.0f",
        requires={"level": "guest"},
        visibility={
            "metadata",
        },
    ),
    gen_current=device(
        "nicos.devices.entangle.PowerSupply",
        description="Current generator",
        tangodevice=tango_base + "gen_current",
        fmtstr="%.0f",
        ramp=10,
        requires={"level": "guest"},
        visibility={
            "metadata",
        },
    ),
    hv=device(
        "nicos_mlz.labs.physlab.devices.hv_generator.HighVoltagePowerSupply",
        description="High voltage device",
        tangodevice=tango_base + "generator",
        fmtstr="(%.0f, %.0f)",
        unit="kV, mA",
        voltage="gen_voltage",
        current="gen_current",
        requires={"level": "guest"},
    ),
    generator=device(
        "nicos.devices.generic.Switcher",
        description="HV setting device",
        moveable="hv",
        precision=0,
        mapping={
            "Off": (0, 0),
            "Standby": (20, 5),
            "On": (35, 40),
        },
        blockingmove=False,
    ),
    gen_ramp=device(
        "nicos.devices.generic.Switcher",
        description="Ramp selection",
        moveable="gen_ramp_dev",
        precision=0,
        blockingmove=False,
        mapping={
            "new tube": 5 / 15.0,
            "slow": 5 / 10.0,
            "normal": 5 / 5.0,
            "quick": 5 / 2.0,
            "fast": 5 / 1.0,
            "high": 5 / 0.5,
            "immediate": 60.0,
        },
    ),
    gen_ramp_dev=device(
        "nicos.devices.generic.ParamDevice",
        device="hv",
        parameter="ramp",
        fmtstr="%.2f",
        visibility=(),
    ),
)

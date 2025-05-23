description = "3He/4He dilution unit from FRM II Sample environment group"

group = "plugplay"

includes = ["alias_T"]

tango_base = f"tango://{setupname}:10000/box/"

devices = {
    f"T_{setupname}_mc": device(
        "nicos.devices.entangle.TemperatureController",
        description="The control device of the mixing chamber",
        tangodevice=tango_base + "lakeshore/control",
        unit="K",
        fmtstr="%.3f",
        pollinterval=5,
        maxage=6,
    ),
    f"T_{setupname}_mc_heaterrange": device(
        "nicos.devices.generic.Switcher",
        description="Heater range for mixing chamber heater",
        moveable=device(
            "nicos.devices.entangle.AnalogOutput",
            tangodevice=tango_base + "lakeshore/heaterrange_a",
            description="",
            visibility=(),
            unit="",
        ),
        precision=0.5,
        mapping={
            "off": 0,
            "10 nW": 1,
            "100 nW": 2,
            "1 uW": 3,
            "10 uW": 4,
            "100 uW": 5,
            "1 mW": 6,
            "10 mW": 7,
            "100 mW": 8,
        },
    ),
    f"T_{setupname}_still": device(
        "nicos.devices.entangle.Sensor",
        description="The still temperature)",
        tangodevice=tango_base + "lakeshore/sensorb",
        unit="K",
        fmtstr="%.3f",
        pollinterval=5,
        maxage=6,
    ),
    f"T_{setupname}_sample": device(
        "nicos.devices.entangle.Sensor",
        description="The sample temperature (if installed)",
        tangodevice=tango_base + "lakeshore/sensor5",
        unit="K",
        fmtstr="%.3f",
        pollinterval=5,
        maxage=6,
    ),
    f"T_{setupname}_sensor6": device(
        "nicos.devices.entangle.Sensor",
        description="The temperature of sensor 6 (if installed)",
        tangodevice=tango_base + "lakeshore/sensor6",
        unit="K",
        fmtstr="%.3f",
        pollinterval=5,
        maxage=6,
        visibility=(),
    ),
    f"T_{setupname}_still_heater": device(
        "nicos.devices.entangle.AnalogOutput",
        description="Still heater",
        tangodevice=tango_base + "lakeshore/still",
        fmtstr="%.1f",
        unit="%",
    ),
    f"{setupname}_p_still": device(
        "nicos.devices.entangle.AnalogInput",
        description="Pressure at still, also at turbo pump inlet",
        tangodevice=tango_base + "i7000/p_still",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="mbar",
    ),
    f"{setupname}_p_inlet": device(
        "nicos.devices.entangle.AnalogInput",
        description="Pressure forepump inlet, also at turbo pump outlet",
        tangodevice=tango_base + "i7000/p_inlet",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="bar",
    ),
    f"{setupname}_p_outlet": device(
        "nicos.devices.entangle.AnalogInput",
        description="Pressure forepump outlet, also at compressor inlet",
        tangodevice=tango_base + "i7000/p_outlet",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="bar",
    ),
    f"{setupname}_p_cond": device(
        "nicos.devices.entangle.AnalogInput",
        description="Condensing pressure, also at compressor outlet",
        tangodevice=tango_base + "i7000/p_cond",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="bar",
    ),
    f"{setupname}_p_tank": device(
        "nicos.devices.entangle.AnalogInput",
        description="Pressure in 3He/4He-gas reservoir",
        tangodevice=tango_base + "i7000/p_dump",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="bar",
    ),
    f"{setupname}_p_vac": device(
        "nicos.devices.entangle.AnalogInput",
        description="Pressure inside vacuum dewar",
        tangodevice=tango_base + "i7000/p_vac",
        fmtstr="%.4g",
        pollinterval=15,
        maxage=20,
        unit="mbar",
    ),
    f"{setupname}_flow": device(
        "nicos.devices.entangle.AnalogInput",
        description="Gas flow",
        tangodevice=tango_base + "i7000/flow",
        fmtstr="%.4g",
        unit="ml/min",
        pollinterval=15,
        maxage=20,
    ),
}

alias_config = {
    "T": {f"T_{setupname}_mc": 300},
    "Ts": {
        f"T_{setupname}_mc": 290,
        f"T_{setupname}_still": 250,
        f"T_{setupname}_sample": 300,
    },
}

extended = dict(
    representative=f"T_{setupname}_mc",
)

monitor_blocks = dict(
    default=Block(
        "Dilution insert " + setupname,
        [
            BlockRow(
                Field(
                    name="Setpoint", key=f"t_{setupname}_mc/setpoint", unitkey="t/unit"
                ),
                Field(name="Target", key=f"t_{setupname}_mc/target", unitkey="t/unit"),
            ),
            BlockRow(
                Field(
                    name="Manual Heater Power",
                    key=f"t_{setupname}_mc/heaterpower",
                    unitkey="t/unit",
                ),
            ),
            BlockRow(
                Field(name="MC", dev=f"T_{setupname}_mc"),
                Field(name="Sample", dev=f"T_{setupname}_sample"),
            ),
            BlockRow(
                Field(name="Still", dev=f"T_{setupname}_still"),
                Field(name="Sensor6", dev=f"T_{setupname}_sensor6"),
            ),
        ],
        setups=setupname,
    ),
    pressures=Block(
        "Pressures " + setupname,
        [
            BlockRow(
                Field(dev=f"{setupname}_p_still", name="Still", width=10),
                Field(dev=f"{setupname}_p_inlet", name="Inlet", width=10),
            ),
            BlockRow(
                Field(dev=f"{setupname}_p_cond", name="Cond", width=10),
                Field(dev=f"{setupname}_p_tank", name="Tank", width=10),
            ),
            BlockRow(
                Field(dev=f"{setupname}_p_outlet", name="Outlet", width=10),
                Field(dev=f"{setupname}_p_vac", name="Vacuum", width=10),
            ),
            BlockRow(
                Field(dev=f"{setupname}_flow", name="Flow", width=10),
            ),
        ],
        setups=setupname,
    ),
    plots=Block(
        setupname,
        [
            BlockRow(
                Field(
                    widget="nicos.guisupport.plots.TrendPlot",
                    plotwindow=300,
                    width=25,
                    height=25,
                    devices=[f"t_{setupname}_mc/setpoint", f"t_{setupname}_mc"],
                    names=["Setpoint", "Regulation"],
                ),
            ),
        ],
        setups=setupname,
    ),
)

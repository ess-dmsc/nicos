description = "setup for the velocity selector"
group = "lowlevel"
display_order = 15

excludes = ["virtual_selector"]

presets = configdata("config_selector.SELECTOR_PRESETS")

tango_base = "tango://phys.kws2.frm2:10000/kws2/"

devices = dict(
    selector=device(
        "nicos_mlz.kws2.devices.selector.SelectorSwitcher",
        description="select selector presets",
        blockingmove=False,
        moveables=["selector_speed", "selector_tilted"],
        det_pos="detector",
        presets=presets,
        mapping={k: [v["speed"], v["tilted"]] for (k, v) in presets.items()},
        fallback="unknown",
        precision=[10.0, None],
    ),
    selector_speed=device(
        "nicos_mlz.kws1.devices.selector.SelectorSpeed",
        description="Selector speed control",
        tangodevice=tango_base + "selector/speed",
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(6500, 28200),
        abslimits=(0, 28200),
        precision=50,
        window=30,
        timeout=300.0,
    ),
    selector_speed_countercard=device(
        "nicos.devices.entangle.Sensor",
        description="Selector frequency according to counter card",
        tangodevice=tango_base + "count/sel_freq",
        unit="rpm",
        fmtstr="%.0f",
        visibility=(),
    ),
    selector_tilted=device(
        "nicos.devices.generic.ManualSwitch",
        description="Whether the selector is tilted",
        states=[False, True],
        visibility=(),
    ),
    selector_lambda=device(
        "nicos_mlz.kws2.devices.selector.SelectorLambda",
        description="Selector wavelength control",
        seldev="selector_speed",
        tiltdev="selector_tilted",
        unit="A",
        fmtstr="%.2f",
        # values are for [not tilted, tilted]
        constants=[2094.3286, 1027.5895],
        offsets=[0.05828, 0.579],
    ),
    selector_rtemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="Temperature of the selector rotor",
        tangodevice=tango_base + "selector/rotortemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(10, 40),
        visibility=(),
    ),
    selector_winlt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at inlet",
        tangodevice=tango_base + "selector/waterintemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 22),
        visibility=(),
    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=tango_base + "selector/waterouttemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(14, 26),
        visibility=(),
    ),
    selector_wflow=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water flow rate through selector",
        tangodevice=tango_base + "selector/flowrate",
        unit="l/min",
        fmtstr="%.1f",
        warnlimits=(1.0, 10),
        visibility=(),
    ),
    selector_vacuum=device(
        "nicos.devices.entangle.AnalogInput",
        description="Vacuum in the selector",
        tangodevice=tango_base + "selector/vacuum",
        unit="mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.02),
        visibility=(),
    ),
    selector_vibrt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Selector vibration",
        tangodevice=tango_base + "selector/vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 0.6),
        visibility=(),
    ),
)

extended = dict(
    poller_cache_reader=["detector"],
    representative="selector",
)

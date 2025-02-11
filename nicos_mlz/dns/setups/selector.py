description = "setup for the velocity selector"
group = "lowlevel"

tango_base = "tango://phys.dns.frm2:10000/dns/"

SELECTOR_POSITIONS = {
    "in": -139.0,
    "out": 139,
}


devices = dict(
    selector_inbeam=device(
        "nicos.devices.generic.Switcher",
        description="Automatic in/out switch for the selector",
        mapping=SELECTOR_POSITIONS,
        fallback="unknown",
        moveable="selector_lift",
        precision=0.1,
    ),
    selector_speed=device(
        "nicos.devices.entangle.AnalogOutput",
        description="Selector speed control",
        tangodevice=tango_base + "selector/speed",
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(0, 3600),
    ),
    selector_rtemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="Temperature of the selector rotor",
        tangodevice=tango_base + "selector/rotortemp",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(10, 45),
    ),
    selector_winlt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at inlet",
        tangodevice=tango_base + "selector/waterintemp",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(15, 20),
    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=tango_base + "selector/waterouttemp",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(15, 20),
    ),
    selector_wflow=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water flow rate through selector",
        tangodevice=tango_base + "selector/flowrate",
        unit="l/min",
        fmtstr="%.1f",
        warnlimits=(1.5, 10),
    ),
    selector_vacuum=device(
        "nicos.devices.entangle.AnalogInput",
        description="Vacuum in the selector",
        tangodevice=tango_base + "selector/vacuum",
        unit="x1e-3 mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.005),
    ),
    selector_vibrt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Selector vibration",
        tangodevice=tango_base + "selector/vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 1),
    ),
    selector_lift=device(
        "nicos.devices.entangle.Motor",
        description="Selector lift",
        tangodevice=tango_base + "s7_motor/sel_lift",
    ),
)

extended = dict(
    representative="selector_speed",
)

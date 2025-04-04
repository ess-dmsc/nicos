description = "setup for the velocity selector"

group = "optional"

tango_base = "tango://phys.maria.frm2:10000/maria/"

devices = dict(
    selector_speed=device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Selector speed control",
        tangodevice=tango_base + "selector/speed",
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(3100, 28300),
        precision=10,
        timeout=300,
        window=10,
    ),
    selector_lambda=device(
        "nicos_mlz.maria.devices.selector.SelectorLambda",
        description="Selector wavelength control",
        seldev="selector_speed",
        unit="A",
        fmtstr="%.2f",
        twistangle=48.30,
        length=0.25,
        beamcenter=0.115,
        maxspeed=28300,
    ),
    selector_rtemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="Temperature of the selector rotor",
        tangodevice=tango_base + "selector/rotortemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(10, 45),
    ),
    selector_winlt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at inlet",
        tangodevice=tango_base + "selector/waterintemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 22),
    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=tango_base + "selector/waterouttemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 24),
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
        unit="mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.001),
    ),
    selector_vibrt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Selector vibration",
        tangodevice=tango_base + "selector/vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 1),
    ),
    wavelength=device(
        "nicos.devices.generic.DeviceAlias",
        alias="selector_lambda",
    ),
)

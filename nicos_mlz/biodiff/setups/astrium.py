description = "setup for the velocity selector"

group = "optional"

tango_base = "tango://phys.biodiff.frm2:10000/biodiff/"

devices = dict(
    selector_speed=device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Selector speed control",
        tangodevice=tango_base + "selector/speed",
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(9000, 22000),
        abslimits=(9000, 22000),
        precision=10,
        timeout=180,
    ),
    selector_lambda=device(
        "nicos.devices.vendor.astrium.SelectorLambda",
        description="Selector wavelength control",
        seldev="selector_speed",
        unit="A",
        fmtstr="%.2f",
        twistangle=19.724,
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
        warnlimits=(15, 20),
    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=tango_base + "selector/waterouttemp",
        unit="degC",
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
        unit="mbar",
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
)

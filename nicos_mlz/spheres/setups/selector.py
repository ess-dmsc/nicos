description = "setup for the velocity selector"

group = "lowlevel"

tangohost = "phys.spheres.frm2"
selector = "tango://%s:10000/spheres/selector" % tangohost

devices = dict(
    selector_speed=device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Selector speed control",
        tangodevice=selector + "/speed",
        unit="rpm",
        fmtstr="%.0f",
        warnlimits=(11000, 22000),
        abslimits=(0, 26000),
        precision=10,
        visibility=(),
        requires={"level": "admin"},
    ),
    selector_lambda=device(
        "nicos.devices.vendor.astrium.SelectorLambda",
        description="Selector wavelength control",
        seldev="selector_speed",
        unit="A",
        fmtstr="%.2f",
        twistangle=48.30,
        length=0.25,
        beamcenter=0.115,
        maxspeed=28300,
        requires={"level": "admin"},
    ),
    selector_rtemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="Temperature of the selector rotor",
        tangodevice=selector + "/rotortemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(10, 45),
        visibility=(),
    ),
    selector_winlt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at inlet",
        tangodevice=selector + "/waterintemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 20),
        visibility=(),
    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=selector + "/waterouttemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 20),
        visibility=(),
    ),
    selector_wflow=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water flow rate through selector",
        tangodevice=selector + "/flowrate",
        unit="l/min",
        fmtstr="%.1f",
        warnlimits=(1.5, 10),
        visibility=(),
    ),
    selector_vacuum=device(
        "nicos.devices.entangle.AnalogInput",
        description="Vacuum in the selector",
        tangodevice=selector + "/vacuum",
        unit="mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.005),
        visibility=(),
    ),
    selector_vibrt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Selector vibration",
        tangodevice=selector + "/vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 1),
        visibility=(),
    ),
)

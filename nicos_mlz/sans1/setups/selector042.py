description = "setup for the 10% velocity selector"

group = "optional"

excludes = ["selector020"]

tango_base = "tango://hw.sans1.frm2.tum.de:10000/sans1/selector/"

devices = dict(
    selector_rpm=device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Selector speed control",
        tangodevice=tango_base + "speed",
        abslimits=(3100, 28300),
        unit="rpm",
        fmtstr="%.0f",
        timeout=600,
        warnlimits=(3099, 28300),
        precision=10,
        comdelay=30,
        maxage=35,
    ),
    selector_lambda=device(
        "nicos.devices.vendor.astrium.SelectorLambda",
        description="Selector center wavelength control",
        seldev="selector_rpm",
        unit="A",
        fmtstr="%.3f",
        twistangle=48.3,
        length=0.25,
        beamcenter=0.123,
        maxspeed=28300,
        maxage=35,
    ),
    selector_vacuum=device(
        "nicos.devices.entangle.AnalogInput",
        description="Vacuum in the selector",
        tangodevice=tango_base + "vacuum",
        unit="x1e-3 mbar",
        fmtstr="%.5f",
        warnlimits=(0, 0.008),  # selector shuts down above 0.005
        maxage=35,
    ),
    selector_rtemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="Temperature of the selector",
        tangodevice=tango_base + "rotortemp",
        unit="C",
        fmtstr="%.1f",
        warnlimits=(10, 45),
        maxage=35,
    ),
    selector_wflow=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water flow rate through selector",
        tangodevice=tango_base + "flowrate",
        unit="l/min",
        fmtstr="%.2f",
        warnlimits=(1.5, 10),  # without rot temp sensor; old value (2.5, 10)
        maxage=35,
    ),
    #    selector_winlt = device('nicos.devices.entangle.AnalogInput',
    #        description = 'Cooling water temperature at inlet',
    #        tangodevice= tango_base + 'waterintemp',
    #        unit = 'C',
    #        fmtstr = '%.1f',
    #        warnlimits = (15, 28),
    #        maxage = 35,
    #    ),
    selector_woutt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Cooling water temperature at outlet",
        tangodevice=tango_base + "waterouttemp",
        unit="degC",
        fmtstr="%.1f",
        warnlimits=(15, 28),
        maxage=35,
    ),
    selector_vibrt=device(
        "nicos.devices.entangle.AnalogInput",
        description="Selector vibration",
        tangodevice=tango_base + "vibration",
        unit="mm/s",
        fmtstr="%.2f",
        warnlimits=(0, 1),
        maxage=35,
    ),
)

description = "Variox1 orange type cryostat with VTI"

group = "plugplay"

includes = ["alias_T"]

tango_base = f"tango://{setupname}:10000/box/"

devices = {
    f"T_{setupname}": device(
        "nicos.devices.entangle.TemperatureController",
        description="The control temperature",
        tangodevice=tango_base + "itc/control",
        unit="K",
        fmtstr="%.3f",
        pollinterval=1,
        maxage=2,
    ),
    f"{setupname}_heater": device(
        "nicos.devices.entangle.AnalogOutput",
        description="The manual heater output",
        tangodevice=tango_base + "itc/manualheater",
        unit="%",
        fmtstr="%.1f",
    ),
    f"{setupname}_control": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Selects which temperature to control",
        tangodevice=tango_base + "itc/controlchannel",
        mapping={"VTI": 1, "Sample": 2},
    ),
    f"T_{setupname}_vti": device(
        "nicos.devices.entangle.Sensor",
        description="The VTI temperature",
        tangodevice=tango_base + "itc/sensor1",
        unit="K",
        fmtstr="%.3f",
        pollinterval=1.5,
        maxage=2.5,
    ),
    f"T_{setupname}_sample": device(
        "nicos.devices.entangle.Sensor",
        description="The sample temperature",
        tangodevice=tango_base + "itc/sensor2",
        unit="K",
        fmtstr="%.3f",
        pollinterval=1.5,
        maxage=2.5,
    ),
    f"{setupname}_p": device(
        "nicos.devices.entangle.TemperatureController",
        description="Needle valve pressure regulation",
        tangodevice=tango_base + "lambda/reg",
        unit="mbar",
        fmtstr="%.1f",
        precision=0.5,
        pollinterval=5,
        maxage=6,
    ),
    f"{setupname}_nv": device(
        "nicos.devices.entangle.AnalogOutput",
        description="Needle valve setting",
        tangodevice=tango_base + "lambda/nv",
        unit="%",
        fmtstr="%.1f",
        pollinterval=1,
        maxage=2,
    ),
    f"{setupname}_lhe_fill": device(
        "nicos.devices.entangle.Sensor",
        description="Liquid Helium level",
        tangodevice=tango_base + "ilm/lhe",
        unit="%",
        fmtstr="%.1f",
        pollinterval=5,
        maxage=6,
    ),
    f"{setupname}_ln2_fill": device(
        "nicos.devices.entangle.Sensor",
        description="Liquid Nitrogen level",
        tangodevice=tango_base + "ilm/ln2",
        unit="%",
        fmtstr="%.1f",
        pollinterval=5,
        maxage=6,
    ),
    f"{setupname}_piso": device(
        "nicos.devices.entangle.Sensor",
        description="Isolation vacuum pressure",
        tangodevice=tango_base + "gauge/iso",
        unit="mbar",
        fmtstr="%.2g",
    ),
    f"{setupname}_psample": device(
        "nicos.devices.entangle.Sensor",
        description="Sample tube pressure",
        tangodevice=tango_base + "gauge/sample",
        unit="mbar",
        fmtstr="%.1f",
    ),
    f"{setupname}_ppump": device(
        "nicos.devices.entangle.Sensor",
        description="Pressure at He pump",
        tangodevice=tango_base + "gauge/pump",
        unit="mbar",
        fmtstr="%.1f",
    ),
}

alias_config = {
    "T": {f"T_{setupname}": 100},
    "Ts": {f"T_{setupname}_sample": 100, f"T_{setupname}_vti": 90},
}

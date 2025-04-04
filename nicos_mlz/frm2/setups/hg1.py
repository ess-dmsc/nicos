description = "Humidity generator for SANS humidity cell"

group = "plugplay"

tango_base = f"tango://{setupname}:10000/box/"

devices = {
    f"T_{setupname}_heater": device(
        "nicos.devices.entangle.TemperatureController",
        description="Temperature of heater",
        tangodevice=tango_base + "heater/control",
        fmtstr="%.1f",
        unit="degC",
        timeout=600.0,
        precision=0.2,
    ),
    f"T_{setupname}_julabo": device(
        "nicos.devices.entangle.TemperatureController",
        description="Temperature of Julabo",
        tangodevice=tango_base + "julabo/control",
        fmtstr="%.1f",
        unit="degC",
        timeout=600.0,
        precision=0.2,
    ),
    f"{setupname}_flowrate": device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Flow rate through humidity cell",
        tangodevice=tango_base + "mhg/flowrate",
        fmtstr="%.1f",
        unit="ml",
        timeout=600.0,
        precision=0.2,
    ),
    f"{setupname}_humidity": device(
        "nicos.devices.entangle.WindowTimeoutAO",
        description="Humidity in humidity cell",
        tangodevice=tango_base + "mhg/humidity",
        fmtstr="%.1f",
        unit="%",
        timeout=600.0,
        precision=1,
    ),
    f"T_{setupname}_cell": device(
        "nicos.devices.entangle.Sensor",
        description="Temperature in humidity cell",
        tangodevice=tango_base + "mhg/temperature",
        fmtstr="%.1f",
        unit="degC",
    ),
}

description = "Wet vertical 5T magnet"

group = "plugplay"
includes = ["alias_T"]

tango_base = f"tango://{setupname}:10000/box/"

devices = {
    f"{setupname}_piso": device(
        "nicos.devices.entangle.Sensor",
        description="Isolation vacuum pressure",
        tangodevice=tango_base + "pressure/ch1",
        fmtstr="%.3e",
    ),
    f"{setupname}_pvti": device(
        "nicos.devices.entangle.Sensor",
        description="VTI pressure",
        tangodevice=tango_base + "pressure/ch2",
        fmtstr="%.3g",
    ),
    f"{setupname}_psample": device(
        "nicos.devices.entangle.Sensor",
        description="Sample space pressure",
        tangodevice=tango_base + "pressure/ch3",
        fmtstr="%.3g",
    ),
    f"{setupname}_lhe": device(
        "nicos.devices.entangle.Sensor",
        description="Liquid helium level",
        tangodevice=tango_base + "levelmeter/level",
        fmtstr="%.0f",
        warnlimits=(120, 700),
        unit="mm",
    ),
    f"{setupname}_lhe_mode": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Readout mode of the levelmeter",
        tangodevice=tango_base + "levelmeter/mode",
        mapping={"standby": 0, "slow": 1, "fast": 2, "continuous": 3},
        warnlimits=("slow", "slow"),
    ),
    f"T_{setupname}_magnet": device(
        "nicos.devices.entangle.Sensor",
        description="Coil temperature",
        tangodevice=tango_base + "ls336/sensora",
        unit="K",
    ),
    f"T_{setupname}_vti": device(
        "nicos.devices.entangle.TemperatureController",
        description="VTI temperature",
        tangodevice=tango_base + "ls336/control2",
        unit="K",
    ),
    f"T_{setupname}_sample": device(
        "nicos.devices.entangle.TemperatureController",
        description="Sample thermometer temperature",
        tangodevice=tango_base + "ls336/control1",
        unit="K",
    ),
    f"{setupname}_vti_heater": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Heater range for VTI",
        tangodevice=tango_base + "ls336/range2",
        warnlimits=("high", "medium"),
        mapping={"off": 0, "low": 1, "medium": 2, "high": 3},
        unit="",
    ),
    f"{setupname}_sample_heater": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Heater range for sample temperature",
        tangodevice=tango_base + "ls336/range1",
        warnlimits=("high", "medium"),
        mapping={"off": 0, "low": 1, "medium": 2, "high": 3},
        unit="",
    ),
    f"{setupname}_nv_reg": device(
        "nicos.devices.entangle.TemperatureController",
        description="Needle valve regulation setpoint",
        tangodevice=tango_base + "nv/regulation",
        unit="mbar",
    ),
    f"{setupname}_nv_manual": device(
        "nicos.devices.entangle.AnalogOutput",
        description="Needle valve opening",
        tangodevice=tango_base + "ls336/control3mout",
    ),
    f"I_{setupname}": device(
        "nicos.devices.entangle.RampActuator",
        description="Current in the magnet",
        tangodevice=tango_base + "supply/field",
        precision=60,
    ),
    f"I_{setupname}_supply": device(
        "nicos.devices.entangle.Sensor",
        description="Current output of the power supply",
        tangodevice=tango_base + "supply/actual",
    ),
}

alias_config = {
    "T": {f"T_{setupname}_vti": 200, f"T_{setupname}_sample": 190},
    "Ts": {f"T_{setupname}_sample": 200, f"T_{setupname}_vti": 190},
}

extended = dict(
    representative=f"I_{setupname}",
)

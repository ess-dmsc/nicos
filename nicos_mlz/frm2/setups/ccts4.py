description = "CCR with sapphire windows, with LS336 controller"

group = "plugplay"

includes = ["alias_T"]

tango_base = f"tango://{setupname}:10000/box/"

devices = {
    f"T_{setupname}": device(
        "nicos_mlz.devices.ccr.CCRControl",
        description="The main temperature control device of the CCR",
        stick=f"T_{setupname}_stick",
        tube=f"T_{setupname}_tube",
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_stick": device(
        "nicos.devices.entangle.TemperatureController",
        description="The control device of the sample (stick)",
        tangodevice=tango_base + "stick/control1",
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_tube": device(
        "nicos.devices.entangle.TemperatureController",
        description="The control device of the tube",
        tangodevice=tango_base + "tube/control2",
        warnlimits=(0, 300),
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_stick_range": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Heater range",
        tangodevice=tango_base + "stick/range1",
        warnlimits=("high", "medium"),
        mapping={"off": 0, "low": 1, "medium": 2, "high": 3},
        unit="",
    ),
    f"T_{setupname}_tube_range": device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Heater range",
        tangodevice=tango_base + "tube/range2",
        warnlimits=("high", "medium"),
        mapping={"off": 0, "low": 1, "medium": 2, "high": 3},
        unit="",
    ),
    f"T_{setupname}_A": device(
        "nicos.devices.entangle.Sensor",
        description="(regulation) Sample temperature",
        tangodevice=tango_base + "sample/sensora",
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_B": device(
        "nicos.devices.entangle.Sensor",
        description="Temperature at the stick",
        tangodevice=tango_base + "stick/sensorb",
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_C": device(
        "nicos.devices.entangle.Sensor",
        description="Coldhead temperature",
        tangodevice=tango_base + "coldhead/sensorc",
        unit="K",
        fmtstr="%.3f",
    ),
    f"T_{setupname}_D": device(
        "nicos.devices.entangle.Sensor",
        description="(regulation) Temperature at " "thermal coupling to the tube",
        tangodevice=tango_base + "tube/sensord",
        warnlimits=(0, 300),
        unit="K",
        fmtstr="%.3f",
    ),
    f"p_{setupname}": device(
        "nicos.devices.entangle.Sensor",
        description="Pressure in sample tube",
        tangodevice=tango_base + "pressure/ch1",
        unit="mbar",
        fmtstr="%.3f",
    ),
    #    '%s_gas_switch' % setupname: device('nicos.devices.entangle.NamedDigitalOutput',
    #        description = 'Switch for the gas valve',
    #        tangodevice = tango_base + 'plc/gas',
    #        mapping = {'on': 1, 'off': 0},
    #    ),
    #    '%s_vacuum_switch' % setupname: device('nicos.devices.entangle.NamedDigitalOutput',
    #        description = 'Switch for the vacuum valve',
    #        tangodevice = tango_base + 'plc/vacuum',
    #        mapping = {'on': 1, 'off': 0},
    #    ),
}

alias_config = {
    "T": {f"T_{setupname}_tube": 200, f"T_{setupname}_stick": 150},
    "Ts": {f"T_{setupname}_A": 100, f"T_{setupname}_B": 90, f"T_{setupname}_D": 20},
}

description = "alias for the switch12 for channel4"

group = "lowlevel"

ana4gpio = "ana4gpio03"

includes = ["ana4gpio03"]

instrument_values = configdata("instrument.values")

code_base = instrument_values["code_base"]

visibility = ()
Vadd = 2.5  # Volt

devices = {
    "detection_gas_pressure": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Pressure detection gas",
        device="ana4gpio03_ch1",
        poly=[0, 10],  # /100R0.1% *1000mA
        unit="mA",
        visibility={"metadata", "devlist", "namespace"},
    ),
    "tank_temperature_resistor": device(
        code_base + "analogencoder.Ohmmeter",
        description="Tank Resistor PT1000",
        device="ana4gpio03_ch2",
        u_high=2.5,
        u_low=0.0,
        r_arb=1000,
        unit="Ohm",
        visibility=visibility,
    ),
    "tank_temperature": device(
        code_base + "analogencoder.PTxxlinearC",
        description="Tank Temperature PT1000",
        device="tank_temperature_resistor",
        # poly = [-551.45, 440.02],
        r0=1000,
        r_cable=0.5,  # 2023-09-05 11:58:34
        alpha=0.003851,
        unit="degC",
        visibility={"metadata", "devlist", "namespace"},
    ),
    "device_temperature_resistor": device(
        code_base + "analogencoder.Ohmmeter",
        description="Device Intern Resistor PT1000",
        device="ana4gpio03_ch3",
        u_high=2.5,
        u_low=0.0,
        r_arb=1000,
        unit="Ohm",
        visibility=visibility,
    ),
    "device_temperature": device(
        code_base + "analogencoder.PTxxlinearC",
        description="Tank Temperature PT1000",
        device="device_temperature_resistor",
        # poly = [-551.45, 440.02],
        r0=1000,
        r_cable=0.0,
        alpha=0.003851,
        unit="degC",
        visibility={"metadata", "devlist", "namespace"},
    ),
    "sw01_SHT3x_Temp_Extern": device(
        code_base + "analogencoder.AnalogEncoder",
        description="SHT3x Temperature Extern",
        device="ana4gpio03_ch4",
        poly=[-66.875, 218.75 / Vadd],
        unit="degC",
        visibility={"metadata", "devlist", "namespace"},
    ),
    "sw02_LT1034BCZ_1V2": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Refvoltage 1.2V  LT1034BCZ",
        device="ana4gpio03_ch4",
        poly=[0.0, 1.0],
        unit="V",
        visibility=visibility,
    ),
    "sw03_AVDD": device(
        code_base + "analogencoder.AnalogEncoder",
        description="AVDD",
        device="ana4gpio03_ch4",
        poly=[0.0, 3.0],
        unit="V",
        visibility=visibility,
    ),
    "sw04_15V": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Pressure sensor source 15V",
        device="ana4gpio03_ch4",
        poly=[0.0, 7.2],
        unit="V",
        visibility=visibility,
    ),
    "sw05_5V0": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Raspi 5V0",
        device="ana4gpio03_ch4",
        poly=[0.0, 3.0],
        unit="V",
        visibility=visibility,
    ),
    "sw06_5V0_in": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Supply 5V0",
        device="ana4gpio03_ch4",
        poly=[0.0, 3.0],
        unit="V",
        visibility=visibility,
    ),
    "sw07_3V3": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Raspi 3V3",
        device="ana4gpio03_ch4",
        poly=[0.0, 2.0],
        unit="V",
        visibility=visibility,
    ),
    "sw08_SHT3x_Humidity_Extern": device(
        code_base + "analogencoder.AnalogEncoder",
        description="SHT3x Humidity Extern",
        device="ana4gpio03_ch4",
        poly=[-12.5, 125.0 / Vadd],
        unit="percent",
        visibility=visibility,
    ),
    "sw09_Pressuresensor_Voltage": device(
        code_base + "analogencoder.AnalogEncoder",
        description="Pressure sensor Voltage need JUMPER!",
        device="ana4gpio03_ch4",
        poly=[0.0, 12.0],
        unit="V",
        visibility=visibility,
    ),
    "channel4": device(
        "nicos.devices.generic.DeviceAlias",
        visibility={"metadata", "devlist", "namespace"},
    ),
}

alias_config = {
    "channel4": {
        "sw01_SHT3x_Temp_Extern": 120,
        "sw02_LT1034BCZ_1V2": 110,
        "sw03_AVDD": 100,
        "sw04_15V": 90,
        "sw05_5V0": 80,
        "sw06_5V0_in": 70,
        "sw07_3V3": 60,
        "sw08_SHT3x_Humidity_Extern": 50,
        "sw09_Pressuresensor_Voltage": 40,
    },
}

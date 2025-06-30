description = "The high and low voltage power supplies for the LoKI detector."

pv_root = "LOKI-DtCmn:PwrC"

hv_info = {
    "id": "HVM",
    "boards": [
        "100", 
        "101", 
        #"102", 
        #"105", 
        #"106",
        ],
    "channels": [f"{ch:>02}" for ch in range(0, 12)],
}

lv_info = {
    "id": "LVM",
    "boards": [
        "107",
        "108",
        #"110",
        #"111",
        #"112",
        #"113",
        #"114",
        #"115",
    ],
    "channels": [f"{ch:>02}" for ch in range(0, 8)],
}

hv_channels = {}
for board in hv_info["boards"]:
    for channel in hv_info["channels"]:
        key = f"HV_{board}_Ch{channel}"
        channel_info = {
            "description": f"Detector HV A7030DP module {key}",
            "board": board,
            "channel": channel,
            "pv_root_channel": f"{pv_root}-{hv_info['id']}-{board}:Ch{channel}",
        }
        hv_channels[key] = channel_info

lv_channels = {}
for board in lv_info["boards"]:
    for channel in lv_info["channels"]:
        key = f"LV_{board}_Ch{channel}"
        channel_info = {
            "description": f"Detector LV A2552 module {key} voltage",
            "board": board,
            "channel": channel,
            "pv_root_channel": f"{pv_root}-{lv_info['id']}-{board}:Ch{channel}",
        }
        lv_channels[key] = channel_info

all_channels = {**hv_channels, **lv_channels}

devices = dict()

for key, channel in all_channels.items():
    pv_root = channel["pv_root_channel"]
    channel_voltage = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        readpv=f"{pv_root}-VMon",
        unit="V"
    )
    channel_current = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        readpv=f"{pv_root}-IMon",
    )
    channel_status = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        readpv=f"{pv_root}-Status-ON",
        mapping={"Power is OFF": 0, "Power is ON": 1},
    )
    channel_power_control = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        readpv=f"{pv_root}-Pw-RB",
        writepv=f"{pv_root}-Pw",
        mapping={"OFF": 0, "ON": 1},
    )
    power_supply_channel = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description=channel["description"],
        pollinterval=0.5,
        maxage=None,
        unit="V",
        fmtstr="%.3f",
        voltage=channel_voltage,
        current=channel_current,
        status=channel_status,
        power_control=channel_power_control,
        mapping={"OFF": 0, "ON": 1},
        visibility={}
    )
    devices[f"{key}_power_supply_channel"] = power_supply_channel

# List of channels selected for a PS module (bank)
# HV
bank_0_channels_hv = [
    {"ps_type": "HV", "board": "100", "channels": [f"{ch:>02}" for ch in range(0, 12)]},
    {"ps_type": "HV", "board": "101", "channels": [f"{ch:>02}" for ch in range(0, 2)]},
]
# LV
bank_0_channels_lv = [
    {"ps_type": "LV", "board": "107", "channels": [f"{ch:>02}" for ch in range(0, 8)]},
    {"ps_type": "LV", "board": "108", "channels": [f"{ch:>02}" for ch in range(0, 6)]},
]

# HV channels
keys = []
for i in range(len(bank_0_channels_hv)):
    
    ps_type = bank_0_channels_hv[i]["ps_type"]
    board = bank_0_channels_hv[i]["board"]
    channels = bank_0_channels_hv[i]["channels"]
    
    for channel in channels: 
        key = f"{ps_type}_{board}_Ch{channel}"
        keys.append(key)

ps_channels_hv = [devices[f"{key}_power_supply_channel"] for key in keys]

# LV channels
keys = []
for i in range(len(bank_0_channels_lv)):
    
    ps_type = bank_0_channels_lv[i]["ps_type"]
    board = bank_0_channels_lv[i]["board"]
    channels = bank_0_channels_lv[i]["channels"]
    
    for channel in channels: 
        key = f"{ps_type}_{board}_Ch{channel}"
        keys.append(key)

ps_channels_lv = [devices[f"{key}_power_supply_channel"] for key in keys]

# HV device
power_supply_module_hv = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Bank 0 HV Power Supplies (Detector Carriage)",
        pollinterval=1.0,
        maxage=None,
        fmtstr="%.3f",
        ps_channels=ps_channels_hv,
        mapping={"OFF": 0, "ON": 1},
    )

# LV device
power_supply_module_lv = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Bank 0 LV Power Supplies (Detector Carriage)",
        pollinterval=1.0,
        maxage=None,
        fmtstr="%.3f",
        ps_channels=ps_channels_lv,
        mapping={"OFF": 0, "ON": 1},
    )

devices["PS_Bank_0_HV"] = power_supply_module_hv
devices["PS_Bank_0_LV"] = power_supply_module_lv
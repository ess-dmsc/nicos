description = "Power supplies configuration utils"

group = "configdata"

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

def get_channel_keys(bank_channels):
    keys = []
    for i in range(len(bank_channels)):
        ps_type = bank_channels[i]["ps_type"]
        board = bank_channels[i]["board"]
        channels = bank_channels[i]["channels"]
        
        for channel in channels: 
            key = f"{ps_type}_{board}_Ch{channel}"
            keys.append(key)
    return keys
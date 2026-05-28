description = "Detector bank power supply configuration"

group = "configdata"

hv_detector_channels = {
    "bank0": {
        "100": [f"{channel:>02}" for channel in range(0, 12)],
        "101": [f"{channel:>02}" for channel in range(0, 2)],
    },
    "bank1": {
        "101": [f"{channel:>02}" for channel in range(2, 6)],
    },
    "bank2": {
        "101": [f"{channel:>02}" for channel in range(6, 9)],
    },
    "bank5": {
        "102": [f"{channel:>02}" for channel in range(0, 7)],
    },
    "bank6": {
        "103": [f"{channel:>02}" for channel in range(0, 8)],
    },
}

hv_bm_channels = {
    "a_monitor_m0": {
        "board": 102,
        "channel": "07",
    },
    "a_monitor_m1": {
        "board": 102,
        "channel": "08",
    },
    "a_monitor_m2": {
        "board": 102,
        "channel": "09",
    },
    "a_monitor_m3": {
        "board": 102,
        "channel": "10",
    },
    "a_monitor_m4": {
        "board": 102,
        "channel": "11",
    },
    "b_monitor_m0": {
        "board": 103,
        "channel": "08",
    },
    "b_monitor_m1": {
        "board": 103,
        "channel": "09",
    },
    "b_monitor_m2": {
        "board": 105,
        "channel": "08",
    },
    "b_monitor_m3": {
        "board": 105,
        "channel": "09",
    },
    "b_monitor_m4": {
        "board": 105,
        "channel": "10",
    },
}

lv_detector_channels = {
    "bank0": {
        "106": [f"{channel:>02}" for channel in range(0, 8)],
        "107": [f"{channel:>02}" for channel in range(0, 6)],
    },
    "bank1": {
        "108": [f"{channel:>02}" for channel in [0, 1, 2, 7]],
    },
    "bank2": {
        "108": [f"{channel:>02}" for channel in range(4, 7)],
    },
    "bank5": {
        "110": [f"{channel:>02}" for channel in range(0, 7)],
    },
    "bank6": {
        "111": [f"{channel:>02}" for channel in range(0, 8)],
    },
}

lv_bm_channels = {
    "monitor_m0": {
        "board": 115,
        "channel": "00",
    },
    "monitor_m1": {
        "board": 115,
        "channel": "01",
    },
    "monitor_m2": {
        "board": 115,
        "channel": "02",
    },
    "monitor_m3": {
        "board": 115,
        "channel": "03",
    },
    "monitor_m4": {
        "board": 115,
        "channel": "04",
    },
}

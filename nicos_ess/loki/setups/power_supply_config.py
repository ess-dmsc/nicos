description = "Detector bank power supply configuration"

group = "configdata"

hv_channels = {
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

lv_channels = {
    "bank0": {
        "106": [f"{channel:>02}" for channel in range(0, 8)],
        "107": [f"{channel:>02}" for channel in range(0, 6)],
    },
    "bank1": {
        "108": [f"{channel:>02}" for channel in range(0, 4)],
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

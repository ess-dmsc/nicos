from nicos_ess.loki.setups.power_supply_config import (
    ALL_CHANNELS, 
    get_channel_keys
)

description = "Power Supplies Bank 0 for the detector carriage (LV)."

# Name of PS Bank and the list of channels selected for it.
BANK_NAME = "LV_Bank_0"
BANK_CHANNELS = [
    # Each item in the list is a set of channels.
    {"ps_type": "LV", "board": "106", "channels": [f"{ch:>02}" for ch in range(0, 8)]},
    {"ps_type": "LV", "board": "107", "channels": [f"{ch:>02}" for ch in range(0, 6)]},
]

# Keys to access channel info
keys = get_channel_keys(BANK_CHANNELS)

# Create channels
devices = dict()
ps_channels = []

for key in keys:
    channel = ALL_CHANNELS[key]
    pv_root = channel["pv_root_channel"]
    power_supply_channel = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description=channel["description"],
        board=0,  # TODO: Set board and channel properly.
        channel=0,
        pollinterval=0.5,
        maxage=None,
        ps_pv=pv_root,
        mapping={"OFF": 0, "ON": 1},
    )
    ps_channels.append(power_supply_channel)

# Bank device
power_supply_module = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Bank 0 LV Power Supplies (Detector Carriage)",
        pollinterval=1.0,
        maxage=None,
        ps_channels=ps_channels,
        mapping={"OFF": 0, "ON": 1},
    )

devices[BANK_NAME] = power_supply_module
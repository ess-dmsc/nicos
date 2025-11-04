from nicos_ess.loki.setups.power_supply_config import ALL_CHANNELS, get_channel_keys

description = "Power Supplies Bank 0 for the detector carriage (HV)."

# Name of PS Bank and the list of channels selected for it.
BANK_NAME = "HV_Bank_0"
BANK_CHANNELS = [
    # Each item in the list is a set of channels.
    {"ps_type": "HV", "board": "100", "channels": [f"{ch:>02}" for ch in range(0, 12)]},
]

# Keys to access channel info
keys = get_channel_keys(BANK_CHANNELS)

# Create channels
devices = dict()
ps_channels = []
module_num = 1

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
        # visibility={}
    )
    devices[f"M{module_num:02d}_{key}"] = power_supply_channel
    module_num += 1

channel_keys = list(devices.keys())

# Bank device
power_supply_module = device(
    "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
    description="Bank 0 HV Power Supplies (Detector Carriage)",
    pollinterval=1.0,
    maxage=None,
    ps_channels=channel_keys,
    mapping={"OFF": 0, "ON": 1},
)

devices[BANK_NAME] = power_supply_module

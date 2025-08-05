from nicos_ess.loki.setups.power_supply_config import (
    ALL_CHANNELS, 
    get_channel_keys
)

description = "Power Supplies Bank 0 for the detector carriage (HV)."

# Name of PS Bank and the list of channels selected for it.
BANK_NAME = "PS_Bank_0_HV"
BANK_CHANNELS = [
    # Each item in the list is a set of channels.
    {"ps_type": "HV", "board": "100", "channels": [f"{ch:>02}" for ch in range(0, 12)]},
    {"ps_type": "HV", "board": "101", "channels": [f"{ch:>02}" for ch in range(0, 2)]},
]

# Keys to access channel info
keys = get_channel_keys(BANK_CHANNELS)

# Create channels
devices = dict()
ps_channels = []

count = 0
for key in keys:
    # NOTE: For now, devices must be created in the same file.
    # Moving it to a reusable method power_supply_config.py lead to import errors.
    # TODO: Simplify PSChhanel with PV subscription!
    channel = ALL_CHANNELS[key]
    pv_root = channel["pv_root_channel"]
    power_supply_channel = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description=channel["description"],
        pollinterval=0.5,
        maxage=None,
        #ps_pv=pv_root,
        ps_pv="test:",
        mapping={"OFF": 0, "ON": 1},
        visibility={}
    )
    ps_channels.append(power_supply_channel)

    count +=1
    if count == 3: break

# Bank device
power_supply_module = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Bank 0 HV Power Supplies (Detector Carriage)",
        pollinterval=1.0,
        maxage=None,
        fmtstr="%.3f",
        ps_channels=ps_channels,
        mapping={"OFF": 0, "ON": 1},
    )

devices[BANK_NAME] = power_supply_module
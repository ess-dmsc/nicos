from nicos_ess.estia.setups.power_supply_config import ALL_CHANNELS, get_channel_keys

description = "Power Supply info for the Detector (HV)."

# Name of PS Bank and the list of channels selected for it.
BANK_NAME = "HV_Bank_0"
BANK_CHANNELS = [
    # Each item in the list is a set of channels.
    {"ps_type": "HV", "board": "100", "channels": [f"{ch:>02}" for ch in range(0, 12)]},
]

# Keys to access channel info
keys = get_channel_keys(BANK_CHANNELS)

devices = dict()

power_supply_module = device(
    "nicos_ess.devices.epics.caen_syx527.CaenSyx527ChannelGroup",
    description="Detector HV Power Supplies",
    precision=7.0,
    sources={key: ALL_CHANNELS[key]["pv_root_channel"] for key in keys},
)

devices[BANK_NAME] = power_supply_module

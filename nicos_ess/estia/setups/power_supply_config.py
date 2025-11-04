from nicos.core import ConfigurationError

description = "Power supplies configuration and utils"

group = "configdata"

PV_ROOT = "ESTIA-DtCmn:PwrC"

HV_INFO = {
    "id": "HVM",
    "boards": [
        "100",
    ],
    "channels": [f"{ch:>02}" for ch in range(0, 12)],
}

hv_channels = {}
for board in HV_INFO["boards"]:
    for channel in HV_INFO["channels"]:
        key = f"HV_{board}_Ch{channel}"
        channel_info = {
            "description": f"Detector HV A7030DP module {key}",
            "board": board,
            "channel": channel,
            "pv_root_channel": f"{PV_ROOT}-{HV_INFO['id']}-{board}:Ch{channel}",
        }
        hv_channels[key] = channel_info

ALL_CHANNELS = {hv_channels}


def validate_channel_key(key):
    return bool(ALL_CHANNELS.get(key))


def get_channel_keys(bank_channels):
    """Receive a list of channels sets, and return a list of keys.

    A key is a string (e.g., "HV_101_Ch02") used as an index for the ALL_CHANNELS
    dict (where the complete information of channel is stored).
    """
    keys = []
    # For each channel set (list)
    for i in range(len(bank_channels)):
        ps_type = bank_channels[i]["ps_type"]
        board = bank_channels[i]["board"]
        channels = bank_channels[i]["channels"]

        for channel in channels:
            key = f"{ps_type}_{board}_Ch{channel}"
            if not validate_channel_key(key):
                raise ConfigurationError(f"PS config: channel key not found ({key}).")
            keys.append(key)

    return keys

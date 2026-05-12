from nicos_ess.loki.setups.power_supply_config import (
    hv_bm_channels,
    hv_detector_channels,
)

description = "High voltage power supply channels for detector banks and beam monitors"

pv_root = "LOKI-DtCmn:PwrC"

devices = {}

# Power supplies for detector banks
for bank, boards in hv_detector_channels.items():
    bank_channels = []
    for board, channels in boards.items():
        for channel in channels:
            ch_name = f"hv_detector_{bank}_{board}_ch{channel}"
            ch_device = device(
                "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
                description="A power supply channel",
                board=board,
                channel=int(channel),
                pollinterval=0.5,
                maxage=None,
                ps_pv=f"{pv_root}-HVM-{board}:Ch{channel}",
                mapping={"OFF": 0, "ON": 1},
                visibility={},
            )
            bank_channels.append(ch_name)
            devices[ch_name] = ch_device
    bank_name = f"hv_detector_{bank}"
    bank_device = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Collection of power supply channels for a detector bank",
        pollinterval=1.0,
        maxage=None,
        ps_channels=bank_channels,
        mapping={"OFF": 0, "ON": 1},
    )
    devices[bank_name] = bank_device

# Power supplies for beam monitors
for monitor, channel_info in hv_bm_channels.items():
    devices[f"hv_{monitor}"] = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description="A power supply channel",
        board=channel_info["board"],
        channel=int(channel_info["channel"]),
        pollinterval=0.5,
        maxage=None,
        ps_pv=f"{pv_root}-HVM-{channel_info['board']}:Ch{channel_info['channel']}",
        mapping={"OFF": 0, "ON": 1},
    )

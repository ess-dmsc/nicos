from nicos_ess.loki.setups.power_supply_config import hv_channels

description = "High voltage power supply channels for detector banks"

pv_root = "LOKI-DtCmn:PwrC"

devices = {}
for bank, boards in hv_channels.items():
    bank_channels = []
    for board, channels in boards.items():
        for channel in channels:
            ch_name = f"hv_{bank}_{board}_{channel}"
            ch_device = device(
                "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
                description="A power supply channel",
                board=board,
                channel=int(channel.replace("Ch", "")),
                pollinterval=0.5,
                maxage=None,
                ps_pv=f"{pv_root}-HVM-{board}:{channel}",
                mapping={"OFF": 0, "ON": 1},
                visibility={},
            )
            bank_channels.append(ch_name)
            devices[ch_name] = ch_device
    bank_name = f"hv_{bank}"
    bank_device = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Collection of power supply channels for a detector bank",
        pollinterval=1.0,
        maxage=None,
        ps_channels=bank_channels,
        mapping={"OFF": 0, "ON": 1},
    )
    devices[bank_name] = bank_device

from nicos_ess.loki.setups.power_supply_config import (
    lv_bm_channels,
    lv_detector_channels,
)

description = "Low voltage power supply channels for detector banks and beam monitors"

pv_root = "LOKI-DtCmn:PwrC"

devices = {}

# Power supplies for detector banks
for bank, channels in lv_detector_channels.items():
    bank_channels = []
    for ch in channels:
        ch_name = f"lv_{bank}_module{ch['module']}"
        ch_device = device(
            "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
            description="A power supply channel",
            board=ch["board"],
            channel=int(ch["channel"]),
            pollinterval=0.5,
            maxage=None,
            ps_pv=f"{pv_root}-LVM-{ch['board']}:Ch{ch['channel']}",
            mapping={"OFF": 0, "ON": 1},
            visibility={},
        )
        bank_channels.append(ch_name)
        devices[ch_name] = ch_device
    bank_name = f"lv_{bank}"
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
for monitor, channel_info in lv_bm_channels.items():
    devices[f"lv_{monitor}"] = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description="A power supply channel",
        board=channel_info["board"],
        channel=int(channel_info["channel"]),
        pollinterval=0.5,
        maxage=None,
        ps_pv=f"{pv_root}-LVM-{channel_info['board']}:Ch{channel_info['channel']}",
        mapping={"OFF": 0, "ON": 1},
    )

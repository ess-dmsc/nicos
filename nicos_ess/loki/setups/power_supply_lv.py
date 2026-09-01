from nicos_ess.loki.setups.power_supply_config import (
    lv_bm_channels,
    lv_detector_channels,
)

description = "Low voltage power supply channels for detector banks and beam monitors"

pv_root = "LOKI-DtCmn:PwrC"

devices = {}

# Power supplies for detector banks
for bank, channels in lv_detector_channels.items():
    bank_name = f"lv_{bank}"
    devices[bank_name] = device(
        "nicos_ess.devices.epics.caen_syx527.CaenSyx527ChannelGroup",
        description="Collection of power supply channels for a detector bank",
        precision=0.1,
        sources={
            f"module{ch['module']}": (f"{pv_root}-LVM-{ch['board']}:Ch{ch['channel']}")
            for ch in channels
        },
    )

# Power supplies for beam monitors
for monitor, channel_info in lv_bm_channels.items():
    devices[f"lv_{monitor}"] = device(
        "nicos_ess.devices.epics.caen_syx527.CaenSyx527ChannelGroup",
        description="A power supply channel",
        precision=0.1,
        sources={
            monitor: (
                f"{pv_root}-LVM-{channel_info['board']}:Ch{channel_info['channel']}"
            )
        },
    )

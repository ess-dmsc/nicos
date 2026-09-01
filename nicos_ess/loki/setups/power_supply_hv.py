from nicos_ess.loki.setups.power_supply_config import (
    hv_bm_channels,
    hv_detector_channels,
)

description = "High voltage power supply channels for detector banks and beam monitors"

pv_root = "LOKI-DtCmn:PwrC"

devices = {}

# Power supplies for detector banks
for bank, channels in hv_detector_channels.items():
    bank_name = f"hv_{bank}"
    bank_device = device(
        "nicos_ess.devices.epics.caen_syx527.CaenSyx527ChannelGroup",
        description="Collection of power supply channels for a detector bank",
        precision=7.0,
        voltage_off_threshold=5.0,
        sources={
            f"module{ch['module']}": f"{pv_root}-HVM-{ch['board']}:Ch{ch['channel']}"
            for ch in channels
        },
    )
    devices[bank_name] = bank_device

# Power supplies for beam monitors
for monitor, channel_info in hv_bm_channels.items():
    devices[f"hv_{monitor}"] = device(
        "nicos_ess.devices.epics.caen_syx527.CaenSyx527ChannelGroup",
        description="A power supply channel",
        precision=7.0,
        sources={
            monitor: f"{pv_root}-HVM-{channel_info['board']}:Ch{channel_info['channel']}"
        },
    )

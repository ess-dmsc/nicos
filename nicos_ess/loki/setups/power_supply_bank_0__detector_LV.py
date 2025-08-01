from nicos_ess.loki.setups.power_supply_config import (
    ALL_CHANNELS, 
    get_channel_keys
)

description = "Power Supplies Bank 0 for the detector carriage (LV)."

# Name of PS Bank and the list of channels selected for it.
BANK_NAME = "PS_Bank_0_LV"
BANK_CHANNELS = [
    {"ps_type": "LV", "board": "107", "channels": [f"{ch:>02}" for ch in range(0, 8)]},
    {"ps_type": "LV", "board": "108", "channels": [f"{ch:>02}" for ch in range(0, 6)]},
]

# Keys to access channel info
keys = get_channel_keys(BANK_CHANNELS)

# Create channels
devices = dict()
ps_channels = []

for key in keys:
    # NOTE: For now, devices must be created in the same file.
    # Moving it to a reusable method power_supply_config.py lead to import errors.
    # TODO: Simplify PSChhanel with PV subscription!
    channel = ALL_CHANNELS[key]
    pv_root = channel["pv_root_channel"]
    channel_voltage = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        readpv=f"{pv_root}-VMon",
        unit="V"
    )
    channel_current = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        readpv=f"{pv_root}-IMon",
    )
    channel_status = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        readpv=f"{pv_root}-Status-ON",
        mapping={"Channel is OFF": 0, "Channel is ON": 1},
    )
    channel_power_control = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        readpv=f"{pv_root}-Pw-RB",
        writepv=f"{pv_root}-Pw",
        mapping={"OFF": 0, "ON": 1},
    )
    power_supply_channel = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyChannel",
        description=channel["description"],
        pollinterval=0.5,
        maxage=None,
        unit="V",
        fmtstr="%.3f",
        voltage=channel_voltage,
        current=channel_current,
        status=channel_status,
        power_control=channel_power_control,
        mapping={"OFF": 0, "ON": 1},
        visibility={}
    )
    devices[f"{key}_ps_channel"] = power_supply_channel
    ps_channels.append(power_supply_channel)

# HV device
power_supply_module = device(
        "nicos_ess.devices.epics.power_supply_channel.PowerSupplyBank",
        description="Bank 0 LV Power Supplies (Detector Carriage)",
        pollinterval=1.0,
        maxage=None,
        fmtstr="%.3f",
        ps_channels=ps_channels,
        mapping={"OFF": 0, "ON": 1},
    )

devices[BANK_NAME] = power_supply_module
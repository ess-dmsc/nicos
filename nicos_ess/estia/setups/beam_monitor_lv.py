description = "ESTIA beam monitor LVPS"

pv_root = "ESTIA-BM:PwrC-LVPS-001:"

devices = dict()

# Channel State
for i in range(1, 3):
    devices[f"channel_{i}_state"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"BM LV state {i}",
        readpv=f"{pv_root}Ch{i}Enable-RB",
    )

# Set Voltage
for i in range(1, 3):
    devices[f"channel_{i}_set_voltage"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} voltage setting",
        readpv=f"{pv_root}Ch{i}Voltage-RB",
        writepv=f"{pv_root}Ch{i}Voltage-S",
        visibility=(),
    )

# Monitored Voltage
for i in range(1, 3):
    devices[f"channel_{i}_monitor_voltage"] = device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description=f"Channel {i} voltage monitor",
        readpv=f"{pv_root}Ch{i}MeasVoltage-RB",
    )
# Set currentlimit
for i in range(1, 3):
    devices[f"channel_{i}_set_current_limit"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} current limit setting",
        readpv=f"{pv_root}Ch{i}CurrentLimit-RB",
        writepv=f"{pv_root}Ch{i}CurrentLimit-S",
        visibility=(),
    )

# Monitored Voltage
for i in range(1, 3):
    devices[f"channel_{i}_monitor_current"] = device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description=f"Channel {i} voltage monitor",
        readpv=f"{pv_root}Ch{i}MeasCurrent-RB",
    )

# Enable and Disable
for i in range(1, 3):
    devices[f"channel_{i}_enable"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description=f"Detector LVPS enable on channel{i}",
        readpv=f"{pv_root}Ch{i}Enable-RB",
        writepv=f"{pv_root}Ch{i}Enable",
        visibility=(),
    )

# Enable RB
for i in range(1, 3):
    devices[f"channel_{i}_enable_rb"] = device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description=f"Channel {i} enabled RB",
        readpv=f"{pv_root}Ch{i}Enable-RB",
    )

devices["error_message"] = device(
    "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
    description="Master enable",
    readpv=f"{pv_root}MasterEnable-RB",
    writepv=f"{pv_root}MasterEnable",
)

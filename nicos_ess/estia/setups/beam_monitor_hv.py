description = "ESTIA beam monitor HVPS"

pv_root = "ESTIA-BM:PwrC-HVPS-001:"

devices = dict()

# Channel State
for i in range(0, 2):
    devices[f"channel_{i}_state"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector HVPS state {i}",
        readpv=f"{pv_root}Ch{i}On-R",
    )

    # Error Message

    devices["error_message"] = device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description=f"Channel {i} error message",
        readpv=f"{pv_root}ErrorString-R",
    )

# ON and OFF
for i in range(0, 2):
    devices[f"enable_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description=f"Detector HVPS enable on {i}",
        readpv=f"{pv_root}Ch{i}On-S",
        writepv=f"{pv_root}Ch{i}On-S",
    )
# Monitor Voltage
for i in range(0, 2):
    devices[f"voltage_monitor_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description=f"Channel {i} voltage monitor",
        readpv=f"{pv_root}Ch{i}Voltage-R",
    )

# Set Voltage
for i in range(0, 2):
    devices[f"set_voltage_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} voltage set",
        readpv=f"{pv_root}Ch{i}VSet-R",
        writepv=f"{pv_root}Ch{i}Voltage-S",
        visibility=(),
    )

# Set Current
for i in range(0, 2):
    devices[f"set_current_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} current set",
        readpv=f"{pv_root}Ch{i}CurrSet-R",
        writepv=f"{pv_root}Ch{i}Current-S",
        visibility=(),
    )

# Monitor Current
for i in range(0, 2):
    devices[f"current_monitor_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description=f"Channel {i} current monitor",
        readpv=f"{pv_root}Ch{i}Current-R",
    )

# Ramp UP
for i in range(0, 2):
    devices[f"ramp_up_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} Ramp Up setting",
        readpv=f"{pv_root}Ch{i}RampUp-R",
        writepv=f"{pv_root}Ch{i}RampUp-S",
        visibility=(),
    )

# Ramp DOWN
for i in range(0, 2):
    devices[f"ramp_down_channel_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description=f"Channel {i} Ramp Up setting",
        readpv=f"{pv_root}Ch{i}RampDown-R",
        writepv=f"{pv_root}Ch{i}RampDown-S",
        visibility=(),
    )

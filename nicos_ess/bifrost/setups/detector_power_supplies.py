description = "The high voltage power supplies for BIFROST detector."

pv_root_1 = "BIFRO-Det:PwrC-HVPS-001:"

devices = dict()

for i in range(0, 4):
    devices[f"voltage_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector HVPS current {i}",
        readpv=f"{pv_root_1}Ch{i}-Current-R",
    )

for i in range(0, 4):
    devices[f"current_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"Detector HVPS voltage {i}",
        readpv=f"{pv_root_1}Ch{i}-Voltage-R",
    )

for i in range(0, 4):
    devices[f"status_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description=f"Detector HVPS status on {i}",
        readpv=f"{pv_root_1}Ch{i}-StatOn-R",
    )

for i in range(0, 4):
    devices[f"status_{i}"] = device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description=f"Detector HVPS enable on {i}",
        readpv=f"{pv_root_1}Ch{i}-Enable-S",
    )

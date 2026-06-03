description = "Temperature sensors for motors"

pvprefix = "PSI-ESTIARND:MC-MCU-01:"

devices = {}

for sensor in range(6, 14):
    devices[f"t_{sensor}"] = device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=f"sensor {sensor}",
        readpv=f"{pvprefix}m{sensor}-Temp",
    )

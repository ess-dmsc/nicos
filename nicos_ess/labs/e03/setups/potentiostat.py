description = "Solartron EnergyLab XM potentiostat"

pv_root = "se-ele-004:"

devices = dict(
    output_a=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsStringReadable",
        description="Digital output A on the EnergyLab XM",
        readpv=f"{pv_root}output_a-r",
    ),
    output_b=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsStringReadable",
        description="Digital output B on the EnergyLab XM",
        readpv=f"{pv_root}output_b-r",
    ),
    output_c=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsStringReadable",
        description="Digital output C on the EnergyLab XM",
        readpv=f"{pv_root}output_c-r",
    ),
)

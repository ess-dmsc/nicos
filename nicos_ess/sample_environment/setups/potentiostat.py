description = "Solartron EnergyLab XM potentiostat"

group = "plugplay"

pv_root = "se-ele-004:"

extended = dict(
    presence_signal=f"pva://{pv_root}output_a-r",
)

devices = dict(
    output_a=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsMappedReadable",
        description="Digital output A on the EnergyLab XM",
        readpv=f"{pv_root}output_a-r",
    ),
    output_b=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsMappedReadable",
        description="Digital output B on the EnergyLab XM",
        readpv=f"{pv_root}output_b-r",
    ),
    output_c=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsMappedReadable",
        description="Digital output C on the EnergyLab XM",
        readpv=f"{pv_root}output_c-r",
    ),
)

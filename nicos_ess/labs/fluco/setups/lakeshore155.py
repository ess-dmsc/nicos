description = "The Lakeshore 155."

pv_root = "E04-SEE:LS155-001:"

devices = dict(
    ls155_mode=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Current mode",
        readpv=f"{pv_root}FunctionMode-S",
    ),
    ls155_idn=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The device idn",
        readpv=f"{pv_root}IDN-R",
    ),
    ls155_amplitude_A=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="DC amplitude (current)",
        readpv=f"{pv_root}CurrAmp-R",
        writepv=f"{pv_root}CurrValue-S",
        abslimits=(-1e308, 1e308),
    ),
    ls155_amplitude_V=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="DC amplitude (current)",
        readpv=f"{pv_root}VoltAmp-R",
        writepv=f"{pv_root}VoltValue-S",
        abslimits=(-1e308, 1e308),
    ),
    ls155_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Outputting DC",
        readpv=f"{pv_root}OutputState-RBV",
        writepv=f"{pv_root}OutputState-S",
    ),
    ls155_shape=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Outputting DC",
        readpv=f"{pv_root}FunctionShape-RBV",
        writepv=f"{pv_root}FunctionShape-S",
    ),
)

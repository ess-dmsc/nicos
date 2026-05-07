description = "The Lakeshore 336 temperature controller."

pv_root = "SE-SEE:SE-LS336-004:"

devices = dict(
    ls336_004_T_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A temperature",
        readpv=f"{pv_root}KRDG0",
    ),
    ls336_004_SP_A=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel A set-point",
        readpv=f"{pv_root}SETP1",
        writepv=f"{pv_root}SETP_S1",
    ),
    ls336_004_T_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B temperature",
        readpv=f"{pv_root}KRDG1",
    ),
    ls336_004_SP_B=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel B set-point",
        readpv=f"{pv_root}SETP2",
        writepv=f"{pv_root}SETP_S2",
    ),
    ls336_004_T_C=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C temperature",
        readpv=f"{pv_root}KRDG2",
    ),
    ls336_004_SP_C=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel C set-point",
        readpv=f"{pv_root}SETP3",
        writepv=f"{pv_root}SETP_S3",
    ),
    ls336_004_T_D=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D temperature",
        readpv=f"{pv_root}KRDG3",
    ),
    ls336_004_SP_D=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel D set-point",
        readpv=f"{pv_root}SETP4",
        writepv=f"{pv_root}SETP_S4",
    ),
    ls336_004_HTR1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Heater 1 output",
        readpv=f"{pv_root}HTR1",
    ),
    ls336_004_HTR2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Heater 2 output",
        readpv=f"{pv_root}HTR2",
    ),
    ls336_004_HTR1_RANGE=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 1 range",
        readpv=f"{pv_root}RANGE1",
        writepv=f"{pv_root}RANGE_S1",
    ),
    ls336_004_HTR2_RANGE=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 2 range",
        readpv=f"{pv_root}RANGE2",
        writepv=f"{pv_root}RANGE_S2",
    ),
    ls336_004_HTR1_RAMP_RATE=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Heater 1 ramp-rate",
        readpv=f"{pv_root}RAMP1",
        writepv=f"{pv_root}RAMP_S1",
    ),
    ls336_004_HTR2_RAMP_RATE=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Heater 2 ramp-rate",
        readpv=f"{pv_root}RAMP2",
        writepv=f"{pv_root}RAMP_S2",
    ),
    ls336_004_HTR1_RAMP=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 1 ramp on/off",
        readpv=f"{pv_root}RAMPST1",
        writepv=f"{pv_root}RAMPST_S1",
    ),
    ls336_004_HTR2_RAMP=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 2 ramp on/off",
        readpv=f"{pv_root}RAMPST2",
        writepv=f"{pv_root}RAMPST_S2",
    ),
)

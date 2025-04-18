description = "The Lakeshore 336 temperature controller."

pv_root = "YMIR-SEE:SE-LS336-004:"

devices = dict(
    ls336_T_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A temperature",
        readpv="{}KRDG0".format(pv_root),
    ),
    ls336_SP_A=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel A set-point",
        readpv="{}SETP1".format(pv_root),
        writepv="{}SETP_S1".format(pv_root),
    ),
    ls336_T_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B temperature",
        readpv="{}KRDG1".format(pv_root),
    ),
    ls336_SP_B=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel B set-point",
        readpv="{}SETP2".format(pv_root),
        writepv="{}SETP_S2".format(pv_root),
    ),
    ls336_T_C=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C temperature",
        readpv="{}KRDG2".format(pv_root),
    ),
    ls336_SP_C=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel C set-point",
        readpv="{}SETP3".format(pv_root),
        writepv="{}SETP_S3".format(pv_root),
    ),
    ls336_T_D=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D temperature",
        readpv="{}KRDG3".format(pv_root),
    ),
    ls336_SP_D=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel D set-point",
        readpv="{}SETP4".format(pv_root),
        writepv="{}SETP_S4".format(pv_root),
    ),
    ls336_HTR1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Heater 1 output",
        readpv="{}HTR1".format(pv_root),
    ),
    ls336_HTR2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Heater 2 output",
        readpv="{}HTR2".format(pv_root),
    ),
    ls336_HTR1_RANGE=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 1 range",
        readpv="{}RANGE1".format(pv_root),
        writepv="{}RANGE_S1".format(pv_root),
    ),
    ls336_HTR2_RANGE=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 2 range",
        readpv="{}RANGE2".format(pv_root),
        writepv="{}RANGE_S2".format(pv_root),
    ),
    ls336_HTR1_RAMP_RATE=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Heater 1 ramp-rate",
        readpv="{}RAMP1".format(pv_root),
        writepv="{}RAMP_S1".format(pv_root),
    ),
    ls336_HTR2_RAMP_RATE=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Heater 2 ramp-rate",
        readpv="{}RAMP2".format(pv_root),
        writepv="{}RAMP_S2".format(pv_root),
    ),
    ls336_HTR1_RAMP=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 1 ramp on/off",
        readpv="{}RAMPST1".format(pv_root),
        writepv="{}RAMPST_S1".format(pv_root),
    ),
    ls336_HTR2_RAMP=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Heater 2 ramp on/off",
        readpv="{}RAMPST2".format(pv_root),
        writepv="{}RAMPST_S2".format(pv_root),
    ),
)

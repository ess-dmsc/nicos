description = "The Read-out Master Module (RMM)."

pv_root = "YMIR-Det1:NDet-RMM-001:"

devices = dict(
    rmm_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv="{}Temperature-R".format(pv_root),
    ),
    rmm_temperature_peak=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The peak temperature of the FPGA",
        readpv="{}TempPeak-R".format(pv_root),
    ),
    rmm_vccint=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCCINT sensor voltage",
        readpv="{}VCCINT-R".format(pv_root),
    ),
    rmm_vcc1v8=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCC1V8 sensor voltage",
        readpv="{}VCC1V8-R".format(pv_root),
    ),
    rmm_vadj1v8=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VADJ1V8 sensor voltage",
        readpv="{}VADJ1V8-R".format(pv_root),
    ),
    rmm_vccintiobram=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCCINTIOBRAM sensor voltage",
        readpv="{}VCCINTIOBRAM-R".format(pv_root),
    ),
    rmm_vcc1v2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCC1V2 sensor voltage",
        readpv="{}VCC1V2-R".format(pv_root),
    ),
    rmm_mgtavcc=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The MGTAVCC sensor voltage",
        readpv="{}MGTAVCC-R".format(pv_root),
    ),
    rmm_mgtavtt=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The MGTAVTT sensor voltage",
        readpv="{}MGTAVTT-R".format(pv_root),
    ),
    rmm_sync_pulse_freq=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The sync pulse frequency",
        readpv="{}SyncPulseFreq-R".format(pv_root),
    ),
    rmm_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The embedded EVR status",
        readpv="{}MRFStatus-R".format(pv_root),
    ),
    rmm_timing_mode=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The RMM timing mode",
        readpv="{}TimingMode-R".format(pv_root),
    ),
    rmm_ttl_freq=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The ttl frequency",
        readpv="YMIR-ChpSy1:Chop-Drv-na02:Frq-S",
        writepv="YMIR-ChpSy1:Chop-Drv-na02:Frq-S",
    ),
    rmm_ttl_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The ttl frequency",
        readpv="YMIR-ChpSy1:Chop-Drv-na02:BeamPosDly-S",
        writepv="YMIR-ChpSy1:Chop-Drv-na02:BeamPosDly-S",
    ),
)

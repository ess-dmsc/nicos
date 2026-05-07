description = "The Read-out Master Module (RMM)."

pv_root = "YMIR-Det1:NDet-RMM-001:"

devices = dict(
    rmm_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root}Temperature-R",
    ),
    rmm_temperature_peak=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The peak temperature of the FPGA",
        readpv=f"{pv_root}TempPeak-R",
    ),
    rmm_vccint=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCCINT sensor voltage",
        readpv=f"{pv_root}VCCINT-R",
    ),
    rmm_vcc1v8=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCC1V8 sensor voltage",
        readpv=f"{pv_root}VCC1V8-R",
    ),
    rmm_vadj1v8=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VADJ1V8 sensor voltage",
        readpv=f"{pv_root}VADJ1V8-R",
    ),
    rmm_vccintiobram=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCCINTIOBRAM sensor voltage",
        readpv=f"{pv_root}VCCINTIOBRAM-R",
    ),
    rmm_vcc1v2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The VCC1V2 sensor voltage",
        readpv=f"{pv_root}VCC1V2-R",
    ),
    rmm_mgtavcc=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The MGTAVCC sensor voltage",
        readpv=f"{pv_root}MGTAVCC-R",
    ),
    rmm_mgtavtt=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The MGTAVTT sensor voltage",
        readpv=f"{pv_root}MGTAVTT-R",
    ),
    rmm_sync_pulse_freq=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The sync pulse frequency",
        readpv=f"{pv_root}SyncPulseFreq-R",
    ),
    rmm_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The embedded EVR status",
        readpv=f"{pv_root}MRFStatus-R",
    ),
    rmm_timing_mode=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The RMM timing mode",
        readpv=f"{pv_root}TimingMode-R",
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

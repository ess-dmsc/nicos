description = "The Read-out Master Module (RMM)."

pv_root = "LOKI-DtCmn:NDet-RMM-001:"


devices = dict(
    rmm_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root}Temperature-R",
    ),
    rmm_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv=f"{pv_root}RingStatus-R",
    ),
    rmm_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv=f"{pv_root}RingBringUpOutput-R",
    ),
    rmm_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv=f"{pv_root}ConfigMessage-R",
    ),
    rmm_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv=f"{pv_root}RefClkFreqOk-R",
    ),
    rmm_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv=f"{pv_root}MrfMsg-R",
    ),
    rmm_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The source timing mode",
        readpv=f"{pv_root}TimingModeSrc-R",
    ),
    rmm_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The sync timing mode",
        readpv=f"{pv_root}TimingModeSync-R",
    ),
)

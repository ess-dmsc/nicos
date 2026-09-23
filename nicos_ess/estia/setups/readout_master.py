description = "The Read-out Master Module (RMM)."

pv_root = "ESTIA-DtCmn:NDet-RMM-001:"

devices = dict(
    rmm1_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root}MaxTemperature",
    ),
    rmm1_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv=f"{pv_root}RingStatus",
    ),
    rmm1_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv=f"{pv_root}RingBringUpOutput",
    ),
    rmm1_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv=f"{pv_root}ConfigMessage",
    ),
    rmm1_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the reference clock frequency",
        readpv=f"{pv_root}RefClkFreqOk",
    ),
    rmm1_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv=f"{pv_root}MrfMsg",
    ),
    rmm1_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The mode of timing source (local/external/mrf)",
        readpv=f"{pv_root}TimingModeSrc",
    ),
    rmm1_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The sync timing mode",
        readpv=f"{pv_root}TimingModeSync",
    ),
)

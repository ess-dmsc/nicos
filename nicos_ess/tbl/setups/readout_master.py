description = "The Read-out Master Module (RMM)."

pv_root_1 = "TBL-DtCmn:NDet-RMM-001:"
pv_root_2 = "TBL-DtCmn:NDet-RMM-002:"

devices = dict(
    rmm1_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root_1}Temperature-R",
    ),
    rmm1_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv=f"{pv_root_1}RingStatus-R",
    ),
    rmm1_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv=f"{pv_root_1}RingBringUpOutput-R",
    ),
    rmm1_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv=f"{pv_root_1}ConfigMessage-R",
    ),
    rmm1_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv=f"{pv_root_1}RefClkFreqOk-R",
    ),
    rmm1_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv=f"{pv_root_1}MrfMsg-R",
    ),
    rmm1_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The source timing mode",
        readpv=f"{pv_root_1}TimingModeSrc-R",
    ),
    rmm1_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The sync timing mode",
        readpv=f"{pv_root_1}TimingModeSync-R",
    ),
    rmm2_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root_2}MaxTemperature",
    ),
    rmm2_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv=f"{pv_root_2}RingStatus",
    ),
    rmm2_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv=f"{pv_root_2}RingBringUpOutput",
    ),
    rmm2_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv=f"{pv_root_2}ConfigMessage",
    ),
    rmm2_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv=f"{pv_root_2}RefClkFreqOk",
    ),
    rmm2_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv=f"{pv_root_2}MrfMsg",
    ),
    rmm2_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The source timing mode",
        readpv=f"{pv_root_2}TimingModeSrc",
    ),
    rmm2_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The sync timing mode",
        readpv=f"{pv_root_2}TimingModeSync",
    ),
)

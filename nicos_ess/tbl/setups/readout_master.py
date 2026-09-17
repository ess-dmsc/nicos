description = "The Read-out Master Module (RMM)."

pv_root_1 = "TBL:NDet-RMM-001:"
pv_root_2 = "TBL-DtCmn:NDet-RMM-002:"

devices = dict(
    rmm1_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv=f"{pv_root_1}MaxTemperature",
    ),
    rmm1_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv=f"{pv_root_1}RingStatus",
    ),
    rmm1_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv=f"{pv_root_1}RingBringUpOutput",
    ),
    rmm1_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv=f"{pv_root_1}ConfigMessage",
    ),
    rmm1_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv=f"{pv_root_1}RefClkFreqOk",
    ),
    rmm1_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv=f"{pv_root_1}MrfMsg",
    ),
    rmm1_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The source timing mode",
        readpv=f"{pv_root_1}TimingModeSrc",
    ),
    rmm1_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The sync timing mode",
        readpv=f"{pv_root_1}TimingModeSync",
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

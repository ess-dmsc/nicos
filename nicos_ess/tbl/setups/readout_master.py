description = "The Read-out Master Module (RMM)."

pv_root_1 = "TBL-DtCmn:NDet-RMM-001:"
pv_root_2 = "TBL-DtCmn:NDet-RMM-002:"

devices = dict(
    rmm1_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv="{}Temperature-R".format(pv_root_1),
    ),
    rmm1_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv="{}RingStatus-R".format(pv_root_1),
    ),
    rmm1_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv="{}RingBringUpOutput-R".format(pv_root_1),
    ),
    rmm1_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv="{}ConfigMessage-R".format(pv_root_1),
    ),
    rmm1_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv="{}RefClkFreqOk-R".format(pv_root_1),
    ),
    rmm1_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv="{}MrfMsg-R".format(pv_root_1),
    ),
    rmm1_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The source timing mode",
        readpv="{}TimingModeSrc-R".format(pv_root_1),
    ),
    rmm1_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The sync timing mode",
        readpv="{}TimingModeSync-R".format(pv_root_1),
    ),
    rmm2_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv="{}Temperature-R".format(pv_root_2),
    ),
    rmm2_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv="{}RingStatus-R".format(pv_root_2),
    ),
    rmm2_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv="{}RingBringUpOutput-R".format(pv_root_2),
    ),
    rmm2_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv="{}ConfigMessage-R".format(pv_root_2),
    ),
    rmm2_ref_clock_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv="{}RefClkFreqOk-R".format(pv_root_2),
    ),
    rmm2_mrf_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv="{}MrfMsg-R".format(pv_root_2),
    ),
    rmm2_timing_mode_source=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The source timing mode",
        readpv="{}TimingModeSrc-R".format(pv_root_2),
    ),
    rmm2_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The sync timing mode",
        readpv="{}TimingModeSync-R".format(pv_root_2),
    ),
    
)

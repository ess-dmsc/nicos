description = "The Read-out Master Module (RMM)."

pv_root = "BIFRO:NDet-RMM-001:"


devices = dict(
    rmm_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the hottest FPGA temperature sensor",
        readpv="{}Temperature-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_ring_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the ring",
        readpv="{}RingStatus-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_ring_bring_up_output=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The ring bring up output",
        readpv="{}RingBringUpOutput-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_config_message=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The configuration message",
        readpv="{}ConfigMessage-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_ref_clk_freq_ok=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The reference clock frequency status",
        readpv="{}RefClkFreqOk-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_mrf_msg=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The MRF message",
        readpv="{}MrfMsg-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_timing_mode_src=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The source timing mode",
        readpv="{}TimingModeSrc-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
    rmm_timing_mode_sync=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The sync timing mode",
        readpv="{}TimingModeSync-R".format(pv_root),
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
)
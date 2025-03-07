description = "NE1600 syringe pump"

pv_root = "SE-SEE:SE-NE1600-001:"

devices = dict(
    inside_diameter_1600=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The Inside diameter of the syringe",
        readpv="{}DIAMETER".format(pv_root),
        writepv="{}SET_DIAMETER".format(pv_root),
        abslimits=(-1e308, 1e308),
    ),
    pump_volume_1600=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The volume to be pumped",
        readpv="{}VOLUME".format(pv_root),
        writepv="{}SET_VOLUME".format(pv_root),
        abslimits=(-1e308, 1e308),
    ),
    pump_volume_units_1600=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The volume units",
        readpv="{}VOLUME_UNITS".format(pv_root),
        writepv="{}SET_VOLUME_UNITS".format(pv_root),
    ),
    pump_rate_1600=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump rate",
        readpv="{}RATE".format(pv_root),
        writepv="{}SET_RATE".format(pv_root),
        abslimits=(-1e308, 1e308),
    ),
    pump_rate_units_1600=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The rate units",
        readpv="{}RATE_UNITS".format(pv_root),
        writepv="{}SET_RATE_UNITS".format(pv_root),
    ),
    pump_direction_1600=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The pump direction",
        readpv="{}DIRECTION".format(pv_root),
        writepv="{}SET_DIRECTION".format(pv_root),
    ),
    volume_withdrawn_1600=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume withdrawn",
        readpv="{}VOLUME_WITHDRAWN".format(pv_root),
    ),
    volume_infused_1600=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume infused",
        readpv="{}VOLUME_INFUSED".format(pv_root),
    ),
    pump_status_1600=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pump status",
        readpv="{}STATUS_TEXT".format(pv_root),
        visibility=(),
    ),
    pump_message_1600=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pump message",
        readpv="{}MESSAGE".format(pv_root),
        visibility=(),
    ),
    seconds_to_pause_1600=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="How long to pause for",
        readpv="{}SET_PAUSE".format(pv_root),
        writepv="{}SET_PAUSE".format(pv_root),
        abslimits=(-1e308, 1e308),
    ),
    zero_volume_withdrawn_1600=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Zero volume withdrawn and infused",
        readpv="{}CLEAR_V_DISPENSED".format(pv_root),
    ),
    pump_1600=device(
        "nicos_ess.devices.epics.syringe_pump.SyringePumpController",
        description="The current operational state of the device",
        start_pv="{}RUN".format(pv_root),
        stop_pv="{}STOP".format(pv_root),
        purge_pv="{}PURGE".format(pv_root),
        pause_pv="{}PAUSE".format(pv_root),
        message_pv="{}MESSAGE".format(pv_root),
        status="pump_status_1600",
    ),
)

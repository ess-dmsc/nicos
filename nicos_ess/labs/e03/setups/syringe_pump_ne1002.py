description = "NE1002 syringe pump"

pv_root = "SE-SEE:SE-NE1002-001:"

devices = dict(
    inside_diameter_1002=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The Inside diameter of the syringe",
        readpv=f"{pv_root}DIAMETER",
        writepv=f"{pv_root}SET_DIAMETER",
        abslimits=(-1e308, 1e308),
    ),
    pump_volume_1002=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The volume to be pumped",
        readpv=f"{pv_root}VOLUME",
        writepv=f"{pv_root}SET_VOLUME",
        abslimits=(-1e308, 1e308),
    ),
    pump_volume_units_1002=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The volume units",
        readpv=f"{pv_root}VOLUME_UNITS",
        writepv=f"{pv_root}SET_VOLUME_UNITS",
    ),
    pump_rate_1002=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump rate",
        readpv=f"{pv_root}RATE",
        writepv=f"{pv_root}SET_RATE",
        abslimits=(-1e308, 1e308),
    ),
    pump_rate_units_1002=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The rate units",
        readpv=f"{pv_root}RATE_UNITS",
        writepv=f"{pv_root}SET_RATE_UNITS",
    ),
    pump_direction_1002=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The pump direction",
        readpv=f"{pv_root}DIRECTION",
        writepv=f"{pv_root}SET_DIRECTION",
    ),
    volume_withdrawn_1002=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume withdrawn",
        readpv=f"{pv_root}VOLUME_WITHDRAWN",
    ),
    volume_infused_1002=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume infused",
        readpv=f"{pv_root}VOLUME_INFUSED",
    ),
    pump_status_1002=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pump status",
        readpv=f"{pv_root}STATUS_TEXT",
        visibility=(),
    ),
    pump_message_1002=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pump message",
        readpv=f"{pv_root}MESSAGE",
        visibility=(),
    ),
    seconds_to_pause_1002=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="How long to pause for (seconds)",
        readpv=f"{pv_root}SET_PAUSE",
        writepv=f"{pv_root}SET_PAUSE",
        abslimits=(-1e308, 1e308),
    ),
    zero_volume_withdrawn_1002=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Zero volume withdrawn and infused",
        readpv=f"{pv_root}CLEAR_V_DISPENSED",
    ),
    pump_1002=device(
        "nicos_ess.devices.epics.syringe_pump.SyringePumpController",
        description="The current operational state of the device",
        start_pv=f"{pv_root}RUN",
        stop_pv=f"{pv_root}STOP",
        purge_pv=f"{pv_root}PURGE",
        pause_pv=f"{pv_root}PAUSE",
        message_pv=f"{pv_root}MESSAGE",
        status="pump_status_1002",
    ),
)

description = "NE9000 peristaltic pump"

pv_root = "SE-SEE:SE-NE9000-001:"

devices = dict(
    inside_diameter_9000=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The Inside diameter of the syringe",
        readpv=f"{pv_root}DIAMETER",
    ),
    pump_volume_9000=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The volume to be pumped",
        readpv=f"{pv_root}VOLUME",
        writepv=f"{pv_root}SET_VOLUME",
        abslimits=(-1e308, 1e308),
    ),
    pump_volume_units_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The volume units",
        readpv=f"{pv_root}VOLUME_UNITS",
        writepv=f"{pv_root}SET_VOLUME_UNITS",
    ),
    pump_rate_9000=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump rate",
        readpv=f"{pv_root}RATE",
        writepv=f"{pv_root}SET_RATE",
        abslimits=(-1e308, 1e308),
    ),
    pump_rate_units_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The rate units",
        readpv=f"{pv_root}RATE_UNITS",
        writepv=f"{pv_root}SET_RATE_UNITS",
    ),
    pump_direction_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The pump direction",
        readpv=f"{pv_root}DIRECTION",
        writepv=f"{pv_root}SET_DIRECTION",
    ),
    volume_withdrawn_9000=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume withdrawn",
        readpv=f"{pv_root}VOLUME_WITHDRAWN",
    ),
    volume_infused_9000=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume infused",
        readpv=f"{pv_root}VOLUME_INFUSED",
    ),
    pump_status_9000=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The pump status",
        readpv=f"{pv_root}STATUS",
        visibility=(),
    ),
    pump_message_9000=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pump message",
        readpv=f"{pv_root}MESSAGE",
        visibility=(),
    ),
    start_pumping_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start pumping",
        readpv=f"{pv_root}RUN",
        writepv=f"{pv_root}RUN",
    ),
    pause_pumping_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Pause pumping",
        readpv=f"{pv_root}PAUSE",
        writepv=f"{pv_root}PAUSE",
    ),
    stop_pumping_9000=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Stop pumping",
        readpv=f"{pv_root}STOP",
        writepv=f"{pv_root}STOP",
    ),
    seconds_to_pause_9000=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="How long to pause for",
        readpv=f"{pv_root}SET_PAUSE",
        writepv=f"{pv_root}SET_PAUSE",
        abslimits=(-1e308, 1e308),
    ),
    zero_volume_withdrawn_9000=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Zero volume withdrawn and infused",
        readpv=f"{pv_root}CLEAR_V_DISPENSED",
    ),
)

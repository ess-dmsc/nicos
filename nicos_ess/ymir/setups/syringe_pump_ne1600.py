description = "NE1600 syringe pump"

pv_root = "E04-SEE-FLUCO:NE1600-001:"

devices = dict(
    pump_status_1600=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The current pump status",
        readpv=f"{pv_root}STATUS_TEXT",
        visibility=(),
    ),
    syringe_pump_1600=device(
        "nicos_ess.devices.epics.syringe_pump.SyringePumpController",
        description="Single axis positioner",
        status="pump_status_1600",
        start_pv=f"{pv_root}RUN",
        stop_pv=f"{pv_root}STOP",
        purge_pv=f"{pv_root}PURGE",
        pause_pv=f"{pv_root}PAUSE",
        message_pv=f"{pv_root}MESSAGE_TEXT",
    ),
)

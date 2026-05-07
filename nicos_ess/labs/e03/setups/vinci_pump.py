description = "The Vinci high pressure syringe pump"

pv_root = "SE-SEE:SE-VINP-001:"

devices = dict(
    vinci_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure",
        readpv=f"{pv_root}Pressure-R",
        writepv=f"{pv_root}PM_Pressure-S",
    ),
    vinci_pressure_SP=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure setpoint",
        readpv=f"{pv_root}PM_Pressure-S",
        writepv=f"{pv_root}PM_Pressure-S",
    ),
    vinci_volume=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pump volume",
        readpv=f"{pv_root}Volume-R",
    ),
    vinci_flowrate=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Pump flow-rate",
        readpv=f"{pv_root}Flow-R",
    ),
    vinci_process_valve=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Status of the process valve",
        readpv=f"{pv_root}ProcValveOpened-RB",
        writepv=f"{pv_root}ProcValveOpen-S",
    ),
    vinci_tank_valve=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Status of the tank valve",
        readpv=f"{pv_root}TankValveOpened-RB",
        writepv=f"{pv_root}TankValveOpen-S",
    ),
    vinci_pump=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Status of the pump",
        readpv=f"{pv_root}Stopped-RB",
        writepv=f"{pv_root}Start-S",
    ),
)

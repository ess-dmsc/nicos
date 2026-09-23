description = "The Vinci high pressure syringe pump"

pv_root = "SE-PS:SE-VINCIP-001:"

devices = dict(
    vinci_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure",
        readpv=f"{pv_root}Pressure-R",
        writepv=f"{pv_root}PM_Pressure-S",
        nexus_config=[
            {
                "group_name": "vinci_pressure",
                "nx_class": "NXcollection",
                "units": "bar",
                "suffix": "readback",
                "source_name": f"{pv_root}Pressure-R",
                "schema": "f144",
                "topic": "dream_sample_env",
                "dataset_type": "nx_log",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
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
    transductor_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Transductor pressure",
        readpv="SE-PS:SE-PTRANS-001:Pressure-R",
        nexus_config=[
            {
                "group_name": "transductor_pressure",
                "nx_class": "NXcollection",
                "units": "bar",
                "suffix": "readback",
                "source_name": "SE-PS:SE-PTRANS-001:Pressure-R",
                "schema": "f144",
                "topic": "dream_sample_env",
                "dataset_type": "nx_log",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
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
        readpv=f"{pv_root}Start-S",
        writepv=f"{pv_root}Start-S",
    ),
    vinci_pump_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Pump mode",
        readpv=f"{pv_root}PumpMode-RB",
        writepv=f"{pv_root}PumpMode-S",
        visibility=(),
    ),
    vinci_pump_pressure_ramp=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Pressure setpoint",
        readpv=f"{pv_root}PM_PressureRamp-RB",
        writepv=f"{pv_root}PM_PressureRamp-S",
    ),
)

description = "JASCO PU-4180 HPLC pump "

pv_root = "SE:SE-JASCO-001:"

devices = dict(
    component_a=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component A",
        readpv=f"{pv_root}ComponentA-S",
        writepv=f"{pv_root}ComponentA-S",
    ),
    component_b=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component B",
        readpv=f"{pv_root}ComponentB-S",
        writepv=f"{pv_root}ComponentB-S",
    ),
    component_c=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component C",
        readpv=f"{pv_root}ComponentC-S",
        writepv=f"{pv_root}ComponentC-S",
    ),
    component_d=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component D",
        readpv=f"{pv_root}ComponentD-S",
        writepv=f"{pv_root}ComponentD-S",
    ),
    pump_flowrate=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump flowrate",
        readpv=f"{pv_root}FlowRate-S",
        writepv=f"{pv_root}FlowRate-S",
    ),
    pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The measured pressure.",
        readpv=f"{pv_root}Pressure-R",
    ),
    pressure_severity=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pressure severity.",
        readpv=f"{pv_root}Pressure-R.SEVR",
        visibility=(),
    ),
    time_to_run=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The time to run.",
        readpv=f"{pv_root}TimeRun-S",
        writepv=f"{pv_root}TimeRun-S",
    ),
    volume_to_pump=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The volume to pump.",
        readpv=f"{pv_root}Volume-S",
        writepv=f"{pv_root}Volume-S",
    ),
    time_remaining=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The time remaining.",
        readpv=f"{pv_root}TimeRemaining-R",
    ),
    volume_remaining=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume remaining.",
        readpv=f"{pv_root}VolumeRemaining-R",
    ),
    hplc_pump=device(
        "nicos_ess.devices.epics.hplc_pump.HPLCPumpController",
        description="The current operational state of the device",
        pv_root=pv_root,
        pollinterval=None,
        monitor=True,
        pva=True,
    ),
)

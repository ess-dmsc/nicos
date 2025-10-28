description = "JASCO PU-4180 HPLC pump "

pv_root = "SE:SE-JASCO-001:"

devices = dict(
    component_a=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component A",
        readpv="{}ComponentA-R".format(pv_root),
        writepv="{}ComponentA-S".format(pv_root),
    ),
    component_b=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component B",
        readpv="{}ComponentB-R".format(pv_root),
        writepv="{}ComponentB-S".format(pv_root),
    ),
    component_c=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component C",
        readpv="{}ComponentC-R".format(pv_root),
        writepv="{}ComponentC-S".format(pv_root),
    ),
    component_d=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The percentage of component D",
        readpv="{}ComponentD-S".format(pv_root),
        writepv="{}ComponentD-S".format(pv_root),
    ),
    pump_flowrate=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pump flowrate",
        readpv="{}FlowRate-S".format(pv_root),
        writepv="{}FlowRate-S".format(pv_root),
    ),
    pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The measured pressure.",
        readpv="{}Pressure-R".format(pv_root),
    ),
    pressure_severity=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The pressure severity.",
        readpv="{}Pressure-R.SEVR".format(pv_root),
        visibility=(),
    ),
    time_to_run=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The time to run.",
        readpv="{}TimeRun-S".format(pv_root),
        writepv="{}TimeRun-S".format(pv_root),
    ),
    volume_to_pump=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The volume to pump.",
        readpv="{}Volume-S".format(pv_root),
        writepv="{}Volume-S".format(pv_root),
    ),
    time_remaining=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The time remaining.",
        readpv="{}TimeRemaining-R".format(pv_root),
    ),
    volume_remaining=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The volume remaining.",
        readpv="{}VolumeRemaining-R".format(pv_root),
    ),
    pump_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The current operational state of the device",
        readpv="{}Status-R".format(pv_root),
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

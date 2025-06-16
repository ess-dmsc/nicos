# ruff: noqa: F821
# NICOS setup for SE‑VM1B cryomagnet, VTI and sample control (LS336 + Mercury)


description = "Cryo Magnet, VTI and Sample control setup (LS336 + Mercury)"

pv_root = "SE-VM1B:"


devices = dict(
    sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample temperature",
        readpv=f"{pv_root}Sample:Temp-R",
        abslimits=(0, 1505),
        userlimits=(0, 1505),
    ),
    sample_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample temperature set‑point",
        readpv=f"{pv_root}Sample:Setpoint-R",
        writepv=f"{pv_root}Sample:Setpoint-S",
        abslimits=(0, 1505),
        userlimits=(0, 1505),
    ),
    sample_heater=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample heater output",
        readpv=f"{pv_root}Sample:HeaterPower-R",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample heater range index",
        readpv=f"{pv_root}Sample:HtrRange-R",
        writepv=f"{pv_root}Sample:HtrRange-S",
    ),
    sample_calibration=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Sample sensor calibration curve header",
        readpv=f"{pv_root}Sample:Calibration-R",
    ),
    sample_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="LS336 sample loop status",
        readpv=f"{pv_root}Sample:status-R",
    ),
    vti_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="VTI temperature set-point",
        readpv=f"{pv_root}VTI:Setpoint-R",
        writepv=f"{pv_root}VTI:Setpoint-S",
        abslimits=(0, 1505),
        userlimits=(0, 1505),
    ),
    vti_temp=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="VTI temperature",
        readpv=f"{pv_root}VTI:Temp-R",
        abslimits=(0, 1505),
        userlimits=(0, 1505),
        nexus_config=[
            {
                "group_name": "cryo_magnet_1",
                "nx_class": "NXcollection",
                "units": "K",
                "suffix": "readback",
                "source_name": f"{pv_root}VTI:Temp-R",
                "schema": "f144",
                "topic": "bifrost_sample_env",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
    vti_heater=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="VTI heater output",
        readpv=f"{pv_root}VTI:HeaterPower-R",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    vti_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="VTI heater range index",
        readpv=f"{pv_root}VTI:HtrRange-R",
        writepv=f"{pv_root}VTI:HtrRange-S",
    ),
    vti_calibration=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="VTI sensor calibration curve header",
        readpv=f"{pv_root}VTI:Calibration-R",
    ),
    vti_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="VTI pressure",
        readpv=f"{pv_root}VTI:Pressure-R",
        abslimits=(0, 1100),
        userlimits=(0, 1100),
    ),
    vti_valve=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Needle‑valve opening",
        readpv=f"{pv_root}VTI:NVopening-R",
        writepv=f"{pv_root}VTI:NVopening-S",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    vti_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="LS336 VTI loop status",
        readpv=f"{pv_root}VTI:status-R",
    ),
    ln2_level=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Magnet liquid‑nitrogen level",
        readpv=f"{pv_root}Magnet:LN2-R",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    lhe_level=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Magnet liquid‑helium level",
        readpv=f"{pv_root}Magnet:LHe-R",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    mag_field=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Magnet persistent field",
        readpv=f"{pv_root}Magnet:Field-R",
        abslimits=(-15, 15),
        userlimits=(-15, 15),
    ),
    mag_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Magnet target field",
        readpv=f"{pv_root}Magnet:FieldTarget-R",
        writepv=f"{pv_root}Magnet:FieldTarget-S",
        abslimits=(-15, 15),
        userlimits=(-15, 15),
    ),
    mag_current=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Magnet power‑supply current",
        readpv=f"{pv_root}Magnet:Current-R",
    ),
    mag_ramp_rate=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Magnet field ramp rate",
        readpv=f"{pv_root}Magnet:FieldRampRate-R",
        writepv=f"{pv_root}Magnet:FieldRampRate-S",
    ),
    mag_switch_heater=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Persistent‑switch heater",
        readpv=f"{pv_root}Magnet:switchHeater-R",
        writepv=f"{pv_root}Magnet:switchHeater-S",
        states=["OFF", "ON"],
        mapping={"OFF": "OFF", "ON": "ON"},
        pollinterval=0.5,
        monitor=True,
        pva=True,
    ),
    mag_action=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="IPS action command",
        readpv=f"{pv_root}Magnet:action-R",
        writepv=f"{pv_root}Magnet:action-S",
        states=["hold", "ramp_to_set", "ramp_to_zero", "clamp"],
        mapping={
            "hold": "HOLD",
            "ramp_to_set": "RTOS",
            "ramp_to_zero": "RTOZ",
            "clamp": "CLMP",
        },
        pollinterval=0.5,
        monitor=True,
        pva=True,
    ),
    mag_status=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="IPS status string",
        readpv=f"{pv_root}Magnet:status-R",
    ),
)

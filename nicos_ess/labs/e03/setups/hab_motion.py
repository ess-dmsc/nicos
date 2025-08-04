description = "Setup for SE-HTP-003 sample holder system (non-motorrecord axes)."

pv_root = "SE:SE-HTP-003:"

devices = dict(
    hab_motor_x=device(
        "nicos_ess.devices.epics.pva.octopy_motor.OctopyMotor",
        description="Axis X motor",
        motorpv=f"{pv_root}axis-x",
        precision=0.05,
        unit="mm",
        abslimits=(0, 300),
        userlimits=(0, 300),
    ),
    hab_motor_y=device(
        "nicos_ess.devices.epics.pva.octopy_motor.OctopyMotor",
        description="Axis Y motor",
        motorpv=f"{pv_root}axis-y",
        precision=0.05,
        unit="mm",
        abslimits=(0, 300),
        userlimits=(0, 300),
    ),
    hab_motor_z=device(
        "nicos_ess.devices.epics.pva.octopy_motor.OctopyMotor",
        description="Axis Z motor",
        motorpv=f"{pv_root}axis-z",
        precision=0.05,
        unit="mm",
        abslimits=(0, 400),
        userlimits=(0, 400),
    ),
    hab_holder_has_sample=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample presence detected",
        readpv=f"{pv_root}holder-has_sample-r",
        fmtstr="%d",
    ),
    hab_holder=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Sample holder",
        writepv=f"{pv_root}holder-s",
        readpv=f"{pv_root}holder-s",
        states=["Hold", "Release"],
        mapping={"Hold": 0, "Release": 1},
    ),
    htp003_temp_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Temperature sensor 1",
        readpv=f"{pv_root}temp_1-r",
    ),
    htp003_temp_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Temperature sensor 2",
        readpv=f"{pv_root}temp_2-r",
    ),
    htp003_temp_3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Temperature sensor 3",
        readpv=f"{pv_root}temp_3-r",
    ),
    htp003_temp_4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Temperature sensor 4",
        readpv=f"{pv_root}temp_4-r",
    ),
)

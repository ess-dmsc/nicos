description = "Setup for SE-HTP-003 sample holder system (non-motorrecord axes)."

pv_root = "SE:SE-HTP-003:"

devices = dict(
    # ------------------------------------------------------------------
    # Axis X
    # ------------------------------------------------------------------
    htp003_axis_x=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis X position",
        readpv=f"{pv_root}axis-x-position-r",
        writepv=f"{pv_root}axis-x-s",
        abslimits=(0, 100),  # Adjust if needed
        userlimits=(0, 100),
    ),
    htp003_axis_x_enable=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Enable Axis X",
        readpv=f"{pv_root}axis-x-enable-s",
        writepv=f"{pv_root}axis-x-enable-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_x_home=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Home Axis X",
        readpv=f"{pv_root}axis-x-home-s",
        writepv=f"{pv_root}axis-x-home-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_x_reset=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Reset Axis X",
        readpv=f"{pv_root}axis-x-reset-s",
        writepv=f"{pv_root}axis-x-reset-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_x_halt=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Halt Axis X",
        readpv=f"{pv_root}axis-x-halt-s",
        writepv=f"{pv_root}axis-x-halt-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_x_velocity=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis X velocity",
        readpv=f"{pv_root}axis-x-velocity-s",
        writepv=f"{pv_root}axis-x-velocity-s",
    ),
    # ------------------------------------------------------------------
    # Axis Y
    # ------------------------------------------------------------------
    htp003_axis_y=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis Y position",
        readpv=f"{pv_root}axis-y-position-r",
        writepv=f"{pv_root}axis-y-s",
    ),
    htp003_axis_y_enable=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Enable Axis Y",
        readpv=f"{pv_root}axis-y-enable-s",
        writepv=f"{pv_root}axis-y-enable-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_y_home=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Home Axis Y",
        readpv=f"{pv_root}axis-y-home-s",
        writepv=f"{pv_root}axis-y-home-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_y_reset=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Reset Axis Y",
        readpv=f"{pv_root}axis-y-reset-s",
        writepv=f"{pv_root}axis-y-reset-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_y_halt=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Halt Axis Y",
        readpv=f"{pv_root}axis-y-halt-s",
        writepv=f"{pv_root}axis-y-halt-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_y_velocity=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis Y velocity",
        readpv=f"{pv_root}axis-y-velocity-s",
        writepv=f"{pv_root}axis-y-velocity-s",
    ),
    # ------------------------------------------------------------------
    # Axis Z
    # ------------------------------------------------------------------
    htp003_axis_z=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis Z position",
        readpv=f"{pv_root}axis-z-position-r",
        writepv=f"{pv_root}axis-z-s",
    ),
    htp003_axis_z_enable=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Enable Axis Z",
        readpv=f"{pv_root}axis-z-enable-s",
        writepv=f"{pv_root}axis-z-enable-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_z_home=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Home Axis Z",
        readpv=f"{pv_root}axis-z-home-s",
        writepv=f"{pv_root}axis-z-home-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_z_reset=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Reset Axis Z",
        readpv=f"{pv_root}axis-z-reset-s",
        writepv=f"{pv_root}axis-z-reset-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_z_halt=device(
        "nicos_ess.devices.epics.manual_switch.ManualSwitch",
        description="Halt Axis Z",
        readpv=f"{pv_root}axis-z-halt-s",
        writepv=f"{pv_root}axis-z-halt-s",
        states=["False", "True"],
        mapping={"False": 0, "True": 1},
    ),
    htp003_axis_z_velocity=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Axis Z velocity",
        readpv=f"{pv_root}axis-z-velocity-s",
        writepv=f"{pv_root}axis-z-velocity-s",
    ),
    # ------------------------------------------------------------------
    # Sample Holder State
    # ------------------------------------------------------------------
    htp003_holder_has_sample=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample presence detected",
        readpv=f"{pv_root}holder-has_sample-r",
    ),
    htp003_holder_state=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Sample holder state",
        readpv=f"{pv_root}holder-s",
    ),
    # ------------------------------------------------------------------
    # System Info
    # ------------------------------------------------------------------
    htp003_ip_address=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="System IP address",
        readpv=f"{pv_root}system-ipaddress-r",
    ),
    # ------------------------------------------------------------------
    # Temperature Sensors
    # ------------------------------------------------------------------
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

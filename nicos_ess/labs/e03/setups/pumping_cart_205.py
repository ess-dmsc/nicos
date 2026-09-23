description = "Setup for pumping cart 205 (SE-AUX-205)"

pv_root = "se-aux-205:"

devices = dict(
    # ------------------------------------------------------------------
    # Lakeshore temperatures
    # ------------------------------------------------------------------
    pc205_regulation_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel A (regulation)",
        readpv=f"{pv_root}tempA-r",
    ),
    pc205_sample_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel B (sample)",
        readpv=f"{pv_root}TempB-r",
    ),
    pc205_channel_c_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel C",
        readpv=f"{pv_root}TempC-r",
    ),
    pc205_channel_d_temp=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Lakeshore temperature channel D",
        readpv=f"{pv_root}TempD-r",
    ),
    # ------------------------------------------------------------------
    # Vacuum transducers on the pumping cart
    # ------------------------------------------------------------------
    pc205_pressure_sensor_1=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum transducer 1",
        readpv=f"{pv_root}P1-r",
    ),
    pc205_pressure_sensor_2=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Vacuum transducer 2",
        readpv=f"{pv_root}P2-r",
    ),
    # ------------------------------------------------------------------
    # Nitrogen level and filling control
    # ------------------------------------------------------------------
    pc205_nitrogen_level=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Liquid-nitrogen level",
        readpv=f"{pv_root}LN2-r",
    ),
    pc205_nitrogen_start_fill=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Start LN2 fill",
        readpv=f"{pv_root}LN2F-Fill-s",
        writepv=f"{pv_root}LN2F-Fill-s",
        visibility=(),
    ),
    pc205_nitrogen_auto_switch=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="LN2 auto-fill on/off",
        readpv=f"{pv_root}LN2F-Auto-s",
        writepv=f"{pv_root}LN2F-Auto-s",
        visibility=(),
    ),
    pc205_nitrogen_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="State of the LN2 filling state machine",
        readpv=f"{pv_root}LN2F-State-r",
        visibility=(),
    ),
    pc205_nitrogen_activity=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="LN2 filling in progress",
        readpv=f"{pv_root}LN2F-Filling-r",
    ),
    # ------------------------------------------------------------------
    # Flush cycle
    # ------------------------------------------------------------------
    pc205_flush_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Current state of the Flush state machine",
        readpv=f"{pv_root}Flush-State-r",
        visibility=(),
    ),
    # pc205_flush_pressure_target=device(
    #     "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
    #     description="Pressure target",
    #     readpv=f"{pv_root}MISSING!!!",
    #     writepv=f"{pv_root}MISSING!!!",
    #     visibility=(),
    # ),
    # pc205_flush_running=device(
    #     "nicos_ess.devices.epics.pva.EpicsMappedReadable",
    #     description="Flush cycle is running",
    #     readpv=f"{pv_root}MISSING!!!",
    #     visibility=(),
    # ),
    # ------------------------------------------------------------------
    # Cold valve
    # ------------------------------------------------------------------
    pc205_c_valve_position=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Cold valve current position",
        readpv=f"{pv_root}CValve-r",
    ),
    pc205_c_valve_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Cold valve target position",
        readpv=f"{pv_root}CValve-Target-s",
        writepv=f"{pv_root}CValve-Target-s",
        abslimits=(0, 100),
        userlimits=(0, 100),
    ),
    # ------------------------------------------------------------------
    # Regulator-heater channels
    # ------------------------------------------------------------------
    pc205_regulation_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Regulation heater power (readback)",
        readpv=f"{pv_root}regulation-htr-r",
    ),
    pc205_regulation_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="Regulation heater range",
        readpv=f"{pv_root}regulation-htr_range-s",
        writepv=f"{pv_root}regulation-htr_range-s",
    ),
    pc205_regulation_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Regulation temperature setpoint",
        readpv=f"{pv_root}regulation-setpoint-s",
        writepv=f"{pv_root}regulation-setpoint-s",
        abslimits=(0, 1500),
        userlimits=(0, 1500),
    ),
    # ------------------------------------------------------------------
    # Sample-heater channels
    # ------------------------------------------------------------------
    pc205_sample_heater_power=device(
        "nicos_ess.devices.epics.pva.EpicsNumericReadable",
        description="Sample heater power (readback)",
        readpv=f"{pv_root}sample-htr-r",
    ),
    pc205_sample_heater_range=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="Sample heater range",
        readpv=f"{pv_root}sample-htr_range-s",
        writepv=f"{pv_root}sample-htr_range-s",
        abslimits=(0, 16777216),
        userlimits=(0, 16777216),
    ),
    pc205_sample_temp_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Sample temperature setpoint",
        readpv=f"{pv_root}sample-setpoint-s",
        writepv=f"{pv_root}sample-setpoint-s",
        abslimits=(0, 1500),
        userlimits=(0, 1500),
    ),
    # ------------------------------------------------------------------
    # Loop 1
    # ------------------------------------------------------------------
    pc205_regulation_pid_p=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID proportional term for control regulation",
        readpv=f"{pv_root}regulation-pid_p-s",
        writepv=f"{pv_root}regulation-pid_p-s",
        visibility=(),
    ),
    pc205_regulation_pid_d=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID derivative term for control regulation",
        readpv=f"{pv_root}regulation-pid_d-s",
        writepv=f"{pv_root}regulation-pid_d-s",
        visibility=(),
    ),
    pc205_regulation_pid_i=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="PID integral term for control regulation",
        readpv=f"{pv_root}regulation-pid_i-s",
        writepv=f"{pv_root}regulation-pid_i-s",
        visibility=(),
    ),
    pc205_regulation_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Operating mode for regulation",
        readpv=f"{pv_root}regulation-mode-s",
        writepv=f"{pv_root}regulation-mode-s",
        visibility=(),
    ),
    # ------------------------------------------------------------------
    # Loop 2
    # ------------------------------------------------------------------
    pc205_sample_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Operating mode for sample",
        readpv=f"{pv_root}sample-mode-s",
        writepv=f"{pv_root}sample-mode-s",
        visibility=(),
    ),
)

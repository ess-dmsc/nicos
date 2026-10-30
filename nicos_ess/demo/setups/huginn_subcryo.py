description = "The Huginn sub cryostat."

pv_root = "Huginn:"
pv_root_ls = "Huginn_LS:"

devices = dict(
    subcryo_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Turn the sub cryo on or off",
        readpv=f"{pv_root}SUBCRYO_ONOFF",
        writepv=f"{pv_root}SUBCRYO_ONOFF_S",
    ),
    T_subcryo_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the sub cryo",
        readpv=f"{pv_root}SUBCRYO_SETP",
        writepv=f"{pv_root}SUBCRYO_SETP_S",
        abslimits=(0.0, 400),
    ),
    T_maincryo_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the main cryo",
        readpv=f"{pv_root}MAINCRYO_SETP",
        writepv=f"{pv_root}MAINCRYO_SETP",
        abslimits=(0.0, 400),
    ),
    T_sample=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The sample temperature",
        readpv=f"{pv_root_ls}KRDG2",
    ),
    T_base=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The base temperature",
        readpv=f"{pv_root_ls}KRDG3",
    ),
    T_peltier_top=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The top peltier temperature",
        readpv=f"{pv_root_ls}KRDG0",
    ),
    T_peltier_bottom=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The bottom peltier temperature",
        readpv=f"{pv_root_ls}KRDG1",
    ),
    subcryo_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The mode for the sub cryo",
        readpv=f"{pv_root}SUBCRYO_MODE",
        writepv=f"{pv_root}SUBCRYO_MODE_S",
        visibility=(),
    ),
    server_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status of the MatLab server",
        readpv=f"{pv_root}MATLAB_SERVER_STATUS",
        visibility=(),
    ),
    T_subcryo_setpoint_min=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The minimum value for the setpoint",
        readpv=f"{pv_root}SUBCRYO_SETP_MIN",
        visibility=(),
    ),
    T_subcryo_setpoint_max=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The maximum value for the setpoint",
        readpv=f"{pv_root}SUBCRYO_SETP_MAX",
        visibility=(),
    ),
    subcryo_status=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The status of the sub cryo",
        readpv=f"{pv_root}SUBCRYO_STATUS",
        visibility=(),
    ),
)

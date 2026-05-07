description = "The PACE5000 in the E03 lab."

pv_root = "SE-PS01:SE-PACE5000-001:"

devices = dict(
    pace_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pressure set-point",
        readpv=f"{pv_root}Setpoint_RBV",
        writepv=f"{pv_root}Setpoint",
    ),
    pace_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current pressure",
        readpv=f"{pv_root}Pressure_RBV",
    ),
    pace_effort=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current effort",
        readpv=f"{pv_root}Effort_RBV",
    ),
    pace_vent=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The vent status",
        readpv=f"{pv_root}Vent_RBV",
        writepv=f"{pv_root}Vent",
        visibility=(),
    ),
    pace_slew=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current slew",
        readpv=f"{pv_root}Slew_RBV",
        writepv=f"{pv_root}Slew",
        visibility=(),
    ),
    pace_slew_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The slew mode",
        readpv=f"{pv_root}SlewMode_RBV",
        writepv=f"{pv_root}SlewMode",
        visibility=(),
    ),
    pace_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Controls whether the pump is on or off",
        readpv=f"{pv_root}Control_RBV",
        writepv=f"{pv_root}Control",
        visibility=(),
    ),
)

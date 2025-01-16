description = "The PACE5000 in the E03 lab."

pv_root = "SE-PS01:SE-PACE5000-001:"

devices = dict(
    pace_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The pressure set-point",
        readpv="{}Setpoint_RBV".format(pv_root),
        writepv="{}Setpoint".format(pv_root),
    ),
    pace_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current pressure",
        readpv="{}Pressure_RBV".format(pv_root),
    ),
    pace_effort=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The current effort",
        readpv="{}Effort_RBV".format(pv_root),
    ),
    pace_vent=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The vent status",
        readpv="{}Vent_RBV".format(pv_root),
        writepv="{}Vent".format(pv_root),
        visibility=(),
    ),
    pace_slew=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current slew",
        readpv="{}Slew_RBV".format(pv_root),
        writepv="{}Slew".format(pv_root),
        visibility=(),
    ),
    pace_slew_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The slew mode",
        readpv="{}SlewMode_RBV".format(pv_root),
        writepv="{}SlewMode".format(pv_root),
        visibility=(),
    ),
    pace_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Controls whether the pump is on or off",
        readpv="{}Control_RBV".format(pv_root),
        writepv="{}Control".format(pv_root),
        visibility=(),
    ),
)

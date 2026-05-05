description = "The choppers in chopper system 4 for ODIN"

foc5_pv_root = "ODIN-ChpSy4:Chop-FOC-501:"
chic_root = "ODIN-ChpSy4:Chop-CHIC-001:"
vacuum_pv_root = "ODIN-VacInstr:Vac-VGP-"

# The Airbus controller owns the physical TDC parameterization.  The canonical
# GUI model uses 0.0 as the controller-relative Airbus phase zero.

devices = dict(
    foc5_chopper_log=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The logs from chopper controller",
        readpv="{}Log_R".format(foc5_pv_root),
        visibility=(),
    ),
    foc5_chopper_levitation_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper levitation status.",
        readpv="{}LeviStatus_R".format(foc5_pv_root),
        visibility=(),
    ),
    foc5_chopper_motor_temperature=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The temperature of the motor of the chopper",
        readpv="{}MtrTemp_R".format(foc5_pv_root),
        visibility=(),
    ),
    foc5_chopper_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper status.",
        readpv="{}ChopState_R".format(foc5_pv_root),
        visibility=(),
    ),
    foc5_chopper_speed=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The current speed.",
        readpv="{}Spd_R".format(foc5_pv_root),
        writepv="{}Spd_S".format(foc5_pv_root),
        precision=0.1,
        mapping={"14 Hz": 14, "7 Hz": 7, "0 Hz": 0},
    ),
    foc5_chopper_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The current delay.",
        readpv="{}ChopDly-S".format(foc5_pv_root),
        writepv="{}ChopDly-S".format(foc5_pv_root),
        abslimits=(0.0, 0.0),
    ),
    foc5_chopper_total_delay=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description=(
            "The total delay (MechDly-S + BeamPosDly-S + ChopDly-S). "
            "The full delay that is applied on proton on target event for "
            "the driving signal of the chopper."
        ),
        readpv="{}TotDly".format(foc5_pv_root),
        visibility=("metadata", "namespace"),
    ),
    foc5_chopper_phase=device(
        "nicos_ess.devices.transformer_devices.ChopperPhase",
        description="The phase of the chopper.",
        phase_ns_dev="foc5_chopper_delay",
        mapped_speed_dev="foc5_chopper_speed",
        offset=0.0,
        unit="degrees",
    ),
    foc5_chopper_delay_errors=device(
        "nicos_ess.devices.epics.chopper_delay_error.ChopperDelayError",
        description="The current delay.",
        readpv="{}DiffTSSamples".format(foc5_pv_root),
        unit="ns",
        visibility=("metadata", "namespace"),
    ),
    foc5_chopper_phased=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The chopper is in phase.",
        readpv="{}InPhs_R".format(foc5_pv_root),
    ),
    foc5_chopper_park_angle=device(
        "nicos_ess.devices.epics.pva.EpicsManualMappedAnalogMoveable",
        description="The chopper's park angle.",
        readpv="{}Pos_R".format(foc5_pv_root),
        writepv="{}ParkAngle_S".format(foc5_pv_root),
        visibility=(),
        mapping={
            "park opening 0": 16.955,
            "park opening 1": -44.275,
            "park opening 2": -101.215,
            "park opening 3": -155.295,
            "park opening 4": 154.425,
            "park opening 5": 105.135,
        },
    ),
    foc5_chopper_park_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The park status for the FOC5 chopper.",
        readpv="{}ParkStatus_R".format(foc5_pv_root),
    ),
    foc5_chopper_park_control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The park control for the FOC5 chopper.",
        readpv="{}C_Park".format(foc5_pv_root),
        writepv="{}C_Park".format(foc5_pv_root),
    ),
    foc5_chopper_chic=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="The status of the CHIC connection.",
        readpv="{}ConnectedR".format(chic_root),
        visibility=(),
        pva=True,
    ),
    foc5_chopper_alarms=device(
        "nicos_ess.devices.epics.chopper.ChopperAlarmsV2",
        description="The chopper alarms",
        pv_root=foc5_pv_root,
        visibility=(),
    ),
    foc5_chopper=device(
        "nicos_ess.devices.epics.chopper.OdinChopperController",
        description="The chopper controller",
        pv_root=foc5_pv_root,
        pollinterval=0.5,
        maxage=None,
        monitor=True,
        slit_edges=[
            [0.0, 50.81],
            [62.36, 110.91],
            [120.83, 166.32],
            [176.995, 218.315],
            [229.21, 266.66],
            [278.355, 316.095],
        ],
        mapping={
            "Start": "start",
            "AStart": "a_start",
            "Stop": "stop",
            "Park": "park",
        },
        speed="foc5_chopper_speed",
        total_delay="foc5_chopper_total_delay",
        park_angle="foc5_chopper_park_angle",
        delay_errors="foc5_chopper_delay_errors",
        chic_conn="foc5_chopper_chic",
        alarms="foc5_chopper_alarms",
        motor_position="upstream",
        positive_speed_rotation_direction="CW",
        resolver_positive_direction="CCW",
        parked_opening_index=0,
        tdc_resolver_position=0.0,
        park_open_angle=16.955,
        disk_delay=0.0,
    ),
    foc5_vacuum=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The vacuum pressure",
        readpv="{}200:PrsR".format(vacuum_pv_root),
        fmtstr="%.2e",
    ),
)

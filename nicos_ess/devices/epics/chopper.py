import time

from nicos import session
from nicos.core import (
    Attach,
    CommunicationError,
    DeviceMixinBase,
    InvalidValueError,
    LimitError,
    Moveable,
    MoveError,
    Override,
    Param,
    PositionError,
    Readable,
    UsageError,
    Value,
    Waitable,
    listof,
    none_or,
    oneof,
    pvname,
    status,
    tupleof,
    usermethod,
)
from nicos.core.mixins import AutoDevice, HasAutoDevices, HasPrecision, HasTimeout
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.chopper_math import angle_distance, phase_deg
from nicos_ess.devices.epics.pva import (
    EpicsManualMappedAnalogMoveable,
    EpicsMappedReadable,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    EpicsEnumParam,
    EpicsStatusOnlyReadable,
    command_channel,
    enum_command_channel,
    enum_readback_channel,
    enum_status_channel,
    get_from_cache_or,
    readback_channel,
    setpoint_channel,
    status_channel,
)


class ChopperAlarms(EpicsStatusOnlyReadable):
    """
    This device handles chopper alarms.

    Every channel carries its information in the EPICS alarm fields, so the
    value callback caches the (severity, message) pair per channel and the
    combined status is the worst alarm across all channels.
    """

    parameters = {
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
    }
    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "communication"
    _connect_channels = ("communication",)
    _epics_channels = {
        "communication": status_channel("Comm_Alrm"),
        "hardware": status_channel("HW_Alrm"),
        "interlock": status_channel("IntLock_Alrm"),
        "level": status_channel("Lvl_Alrm"),
        "position": status_channel("Pos_Alrm"),
        "power": status_channel("Pwr_Alrm"),
        "reference": status_channel("Ref_Alrm"),
        "software": status_channel("SW_Alrm"),
        "voltage": status_channel("Volt_Alrm"),
    }

    def _on_channel_update(self, update):
        ts = time.time()
        self._cache.put(
            self._name,
            self._epics.cache_key_for(update.channel),
            (update.severity, update.message),
            ts,
        )
        self._refresh_status(ts)

    def _compute_status(self, maxage=0):
        """
        Goes through all alarms in the chopper and returns the alarm encountered
        with the highest severity. All alarms are printed in the session log.
        """
        in_alarm = []
        highest_severity = status.OK
        for name in self._epics_channels:
            severity, message = self._read_channel_alarm_cached(name, maxage)
            self._log_alarm_once(name, severity, message)
            if severity == status.OK:
                continue
            if severity > highest_severity:
                highest_severity = severity
                in_alarm = [f"{name} alarm"]
            elif severity == highest_severity:
                in_alarm.append(f"{name} alarm")
        return highest_severity, ", ".join(in_alarm)

    def _read_channel_alarm_cached(self, channel, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.cache_key_for(channel),
            lambda: self._epics.get_channel_alarm(channel),
            maxage=maxage,
        )


class HasChopperGeometry(DeviceMixinBase):
    """The disc geometry for the chopper GUI, as in the NeXus file and the
    chopper records: angles in degrees anticlockwise seen from the moderator,
    from the disc's TDC mark.
    """

    parameters = {
        "slit_edges": Param(
            "Openings [start, end] as in the NeXus file",
            type=listof(listof(float)),
            default=[],
        ),
        "beam_position": Param(
            "Angle from the TDC sensor to the beam, as in the NeXus file",
            type=none_or(float),
            default=None,
            unit="degrees",
        ),
        "resolver_sign": Param(
            "+1 if the resolver reading rises while the disc turns clockwise "
            "seen from the moderator, -1 if it falls",
            type=none_or(oneof(1, -1)),
            default=None,
        ),
        "tdc_resolver_position": Param(
            "Resolver reading with the TDC mark at the TDC sensor",
            type=none_or(float),
            default=None,
            unit="degrees",
        ),
        "distance": Param(
            "Distance of the disc from the moderator along the beam, as in the "
            "NeXus file",
            type=none_or(float),
            default=None,
            unit="m",
        ),
        "guide_position": Param(
            "Where the beam is drawn, seen from the moderator",
            type=oneof("RIGHT", "UP", "LEFT", "DOWN"),
            default="DOWN",
        ),
        "visual_geometry_verified": Param(
            "Whether the chopper GUI drawing has been checked against the disc",
            type=bool,
            default=False,
        ),
    }

    def _geometry_gui_info(self):
        return {param: getattr(self, param) for param in HasChopperGeometry.parameters}


class EssChopperController(HasChopperGeometry, MappedMoveable):
    """Handles the status and hardware control for an ESS chopper system."""

    parameters = {
        "legacy_spd_sign": Param(
            "The speed device reads Spd_R (positive = clockwise seen from the "
            "moderator) instead of SpdNexus-R; remove with the switch to SpdNexus-R",
            type=bool,
            default=False,
        ),
    }

    attached_devices = {
        "state": Attach("Current state of the chopper", Readable),
        "command": Attach("Command PV of the chopper", MappedMoveable),
        "alarms": Attach("Alarms of the chopper", ChopperAlarms, optional=True),
        "speed": Attach("Speed PV of the chopper", MappedMoveable),
        "total_delay": Attach("Total applied chopper delay", Readable),
        "park_angle": Attach("Resolver park angle", Readable),
        "delay_errors": Attach("Delay-error samples", Readable),
        "chic_conn": Attach("Status of the CHIC connection", Readable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
        "mapping": Override(mandatory=False, userparam=False, volatile=True),
    }

    hardware_access = False
    valuetype = str

    def doRead(self, maxage=0):
        return self._attached_state.read()

    def doStart(self, target):
        if target.lower() == "stop":
            # Set the speed to zero to keep EPICS behaviour consistent.
            try:
                target_speed = self._attached_speed._inverse_mapping.get(0, "0")
                self._attached_speed.move(target_speed)
            except Exception:
                self.log.exception(
                    "Failed to set speed to 0 when stopping chopper. "
                    "Will still send stop command."
                )
        self._attached_command.move(target)

    def doStop(self):
        # Ignore - stopping the chopper is done via the move command.
        pass

    def doReset(self):
        # Ignore - resetting the chopper is done via the move command.
        pass

    def _getWaiters(self):
        # the park angle is BUSY whenever the disc spins
        gui_only = ("total_delay", "park_angle", "delay_errors")
        return {name: dev for name, dev in self._adevs.items() if name not in gui_only}

    def doStatus(self, maxage=0):
        if self._attached_alarms:
            stat, msg = self._attached_alarms.status(maxage)
            if stat != status.OK:
                return stat, msg
        if self._attached_chic_conn.read() != "Connected":
            return status.ERROR, "no connection to the CHIC"
        stat, msg = Waitable.doStatus(self, maxage)
        if stat != status.OK:
            return stat, msg
        return status.OK, ""

    def doReadMapping(self):
        return self._attached_command.mapping

    def get_chopper_gui_info(self):
        """Geometry and the cache keys the chopper panel subscribes to."""
        info = {
            "chopper": self.name,
            "speed_key": f"{self._attached_speed.name}/value",
            "total_delay_key": f"{self._attached_total_delay.name}/value",
            "park_angle_key": f"{self._attached_park_angle.name}/value",
            "delay_errors_key": f"{self._attached_delay_errors.name}/raw_errors",
        }
        info.update(self._geometry_gui_info())
        info["legacy_spd_sign"] = self.legacy_spd_sign
        return info


class NewChopperAlarms(ChopperAlarms):
    """Chopper alarms for the standardized ODIN/NMX chopper setup."""

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _epics_channels = {
        "communication": status_channel("Comm_Alrms"),
        "hardware": status_channel("HW_Alrms"),
        "interlock": status_channel("IntLock_Alrms"),
        "level": status_channel("Lvl_Alrm"),
        "position": status_channel("Pos_Alrms"),
        "power": status_channel("Pwr_Alrms"),
        "software": status_channel("SW_Alrms"),
        "voltage": status_channel("Volt_Alrms"),
    }


class EssChopperSpeed(EpicsManualMappedAnalogMoveable):
    """
    Chopper speed class implements doIsCompleted to ease the maw
    usage inside scripts and scans
    """

    TARGET_ZERO = "0"
    _INPHASE_STATES = {
        "Not in phase": False,
        "In phase": True,
    }

    attached_devices = {
        "in_phase": Attach("In phase ", EpicsMappedReadable),
        "state": Attach("Current state of the chopper", Readable),
    }

    def doInit(self, mode):
        EpicsManualMappedAnalogMoveable.doInit(self, mode)
        self._previous_inphase = False

    def _str_to_bool(self, inp):
        return self._INPHASE_STATES[inp]

    def doIsCompleted(self):
        """
        Return `True` if a phase-transition has been completed.

        Checking if chopper frequency change was accomplished is done by verifying
        whether it is in steady state. The in-phase flag tells whether the tachometer
        and EVR signals concur, using statistical methods on the EPICS IOC.

        Watching in-phase flag state is not sufficient, however, since its change
        is not instantaneous when we command a frequency change. Although EPICS
        has a mechanism to put flag down when speed setpoint is changed, there is
        no enough time for the state change to reach NICOS. Thus, we utilize a
        rising edge detector, `_is_completed_by_inphase_edge`, that detects the
        transition, not only the current state.

        A final caveat: the in-phase flag does not go "Not in phase"
        when set the target to 0 Hz — that is the same as sending a Stop to the
        controller and the statistics algorithm of EPICS IOC stops working. To
        handle that case we verify whether the target is zero and if it is also
        ensure the chopper state changed to "Ready": that means that the disc
        stopped and the movement is completed.
        """
        if self.target != self.TARGET_ZERO:
            return self._is_completed_by_inphase_edge()
        return self._is_completed_by_state()

    def _is_completed_by_inphase_edge(self):
        """
        This function implements a rising edge detector, as the following picture shows

          in-phase
          ^
          |
        1 |_ _ _ _ _ _ ________ ...
          |           |
          |           ^
        0 |___________|__________-> t

                      ^rising edge of the signal

        from the above chart we can extract the truth table:

        previous | current | output
        ---------|---------|-------
         0       | 0       | 0
         0       | 1       | 1
         1       | 0       | 0
         1       | 1       | 0

        and implemented it with logic gates:

        previous -----o|``-.
                       |    :----- output
        current  ------|..-`

        This function returns the output value and updates the previous value for the next iteration.
        """
        current = self._str_to_bool(self._attached_in_phase.read())
        edge_detected = current and not self._previous_inphase
        self._previous_inphase = current
        return edge_detected

    def _is_completed_by_state(self):
        return self._attached_state.read() == "Ready"


class NewEssChopperController(EssChopperController):
    """Standardized ESS chopper controller for ODIN/NMX style setups."""

    attached_devices = {
        "alarms": Attach("Alarms of the chopper", NewChopperAlarms, optional=True),
        "speed": Attach("Speed PV of the chopper", EssChopperSpeed),
    }

    parameter_overrides = {
        "mapping": Override(settable=False),
    }


# The speed PVs, with the chopper group's sign: setups set legacy_spd_sign.
SPEED_READBACK = "Spd_R"
SPEED_SETPOINT = "Spd_S"

PARK_TOLERANCE = 0.5  # deg
NO_COMMAND_HOLD = 0.5  # s
# a phase move takes two statistics windows, 70 s on YMIR; a spin-up longer
MOVE_TIMEOUT = 600.0  # s

TRANSITIONAL_STATES = (
    "Initialization",
    "Coasting",
    "Stopping",
    "I. stopping",
    "E. stopping",
)


class EssChopper(
    HasChopperGeometry, HasAutoDevices, HasTimeout, EpicsDeviceBase, Moveable
):
    """One ESS chopper disc.

    The value is the speed and phase of the disc, and the status is its state
    or what it is doing, followed by the drive's last log message. Move the
    disc with::

        maw(disc, (14, 120))     # speed, then phase
        maw(disc.speed, 14)      # Hz, as the speed PVs have it; 0 stops the disc
        maw(disc.phase, 120)     # degrees, written as ChopDly-S at the target speed
        maw(disc.position, 42)   # parks the stopped disc at a resolver position
        disc.park("ParkOpen")    # one of the IOC's park choices; then wait(disc)
        reset(disc)              # clears the drive's alarms

    Set the speed before the phase: the phase is kept as a delay, so its value
    in degrees changes with the speed. A new speed or delay restarts the IOC's
    statistics and drops InPhaseTS-R to Not in phase (evr_seq_calc 2.7.6); a
    move completes when it reads In phase again with the disc at speed.
    Stopping a script leaves the discs turning.
    """

    parameters = {
        "pv_root": Param(
            "PV prefix of the disc", type=pvname, mandatory=True, userparam=False
        ),
        "chic_root": Param(
            "PV prefix of the disc's CHIC", type=pvname, mandatory=True, userparam=False
        ),
        "legacy_spd_sign": Param(
            "Whether the speed PVs are positive clockwise seen from the moderator, "
            "the opposite of NeXus; the chopper GUI draws the disc accordingly",
            type=bool,
            default=False,
            userparam=False,
        ),
        "in_phase": Param(
            "Whether the IOC's last statistics evaluation found the disc in phase",
            type=str,
            volatile=True,
        ),
        "total_delay": Param(
            "Delay of the drive signal after the timing event: MechDly + "
            "BeamPosDly + ChopDly",
            type=float,
            unit="ns",
            volatile=True,
        ),
        "park_command": Param(
            "Last park command the drive took; the choices are those of park()",
            type=EpicsEnumParam("park"),
            volatile=True,
        ),
        "park_status": Param("Park state of the disc", type=str, volatile=True),
        "last_message": Param(
            "Last message in the drive's log", type=str, volatile=True
        ),
        "delay_mean": Param(
            "Mean TDC delay error in the last statistics evaluation",
            type=float,
            unit="ns",
            volatile=True,
        ),
        "delay_stddev": Param(
            "Standard deviation of the TDC delay error in the last statistics "
            "evaluation",
            type=float,
            unit="ns",
            volatile=True,
        ),
        "delay_fwhm": Param(
            "FWHM of the TDC delay error in the last statistics evaluation",
            type=float,
            unit="ns",
            volatile=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(
            default="Hz deg", mandatory=False, settable=False, prefercache=False
        ),
        "fmtstr": Override(default="[%.2f, %.2f]", settable=False, prefercache=False),
        "timeout": Override(default=MOVE_TIMEOUT),
    }

    valuetype = tupleof(float, float)
    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    _command_pv = "C_ExecuteUser"
    _park_pv = "C_Park"
    _park_readback_pv = "ParkCmd_RB"

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = None

    def _build_epics_channels(self):
        return {
            "state": enum_readback_channel(
                "ChopState_R",
                cache_key="state",
                affects_status=True,
                refresh_status=True,
            ),
            "in_phase": enum_status_channel("InPhaseTS-R", cache_key="in_phase"),
            "on_speed": enum_status_channel("OnSpd_R"),
            "park_status": enum_status_channel("ParkStatus_R", cache_key="park_status"),
            "dcu_state": enum_status_channel("DcuState_R"),
            "chic": enum_status_channel("ConnectedR", pv_prefix_attr="chic_root"),
            "alarm_level": enum_status_channel("Lvl_Alrm"),
            "control_mode": enum_status_channel("CtrlMd_RB"),
            "last_message": status_channel(
                "Log_R", cache_key="last_message", as_string=True
            ),
            "total_delay": readback_channel("TotDly", cache_key="total_delay"),
            "position": readback_channel(
                "Pos_R", cache_key="position", refresh_status=True
            ),
            "park_setpoint": readback_channel("ParkS_RB", refresh_status=True),
            "park_readback": enum_readback_channel(
                self._park_readback_pv, subscribe=False
            ),
            "delay_mean": readback_channel("DiffTSMean", cache_key="delay_mean"),
            "delay_stddev": readback_channel("DiffTSStdDev", cache_key="delay_stddev"),
            "delay_fwhm": readback_channel("DiffTSFWHMWidth", cache_key="delay_fwhm"),
            "delay_errors": readback_channel("DiffTSSamples", cache_key="delay_errors"),
            "command": enum_command_channel(self._command_pv),
            "park": enum_command_channel(self._park_pv),
            "park_angle": command_channel("Park_S"),
            "speed_readback": readback_channel(
                SPEED_READBACK, cache_key="speed_readback"
            ),
            "speed_setpoint": setpoint_channel(
                SPEED_SETPOINT, cache_key="speed_setpoint"
            ),
            "max_speed": readback_channel("MaxSpd_R", subscribe=False),
            "delay": setpoint_channel("ChopDly-S", cache_key="delay"),
        }

    def doInit(self, mode):
        for name, cls in (
            ("speed", ChopperSpeed),
            ("phase", ChopperPhase),
            ("position", ChopperPosition),
        ):
            self.add_autodevice(
                name,
                cls,
                chopper=self,
                maxage=0,
                visibility=self.autodevice_visibility,
            )
        EpicsDeviceBase.doInit(self, mode)

    def doShutdown(self):
        HasAutoDevices.doShutdown(self)
        EpicsDeviceBase.doShutdown(self)

    def doRead(self, maxage=0):
        return (
            self._read_channel_cached("speed_readback", maxage=maxage),
            self._phase(maxage),
        )

    def doReadTarget(self):
        return self._read_channel_cached("speed_setpoint"), self._phase(None)

    def doReadUnit(self):
        return "Hz deg"

    def valueInfo(self):
        return (
            Value(f"{self}.speed", unit="Hz", fmtstr="%.2f"),
            Value(f"{self}.phase", unit="deg", fmtstr="%.2f"),
        )

    def doIsAllowed(self, target):
        speed, phase = target
        ok, why = self._speed_allowed(speed)
        if ok and speed:
            ok, why = self._phase_allowed(phase)
        return ok, why

    def doStart(self, target):
        speed, phase = target
        self._start_speed(speed)
        if speed:
            self._start_phase(phase)

    def doIsCompleted(self):
        return self._is_done(self, maxage=0)

    def _on_channel_update(self, update):
        super()._on_channel_update(update)
        if update.channel in ("speed_readback", "speed_setpoint", "delay"):
            self._cache.put(self._name, "value", self.doRead(None), time.time())

    def _phase(self, maxage):
        """ChopDly-S at the speed setpoint, in degrees."""
        return phase_deg(
            self._read_channel_cached("delay", maxage=maxage),
            self._read_channel_cached("speed_setpoint", maxage=maxage),
        )

    def doReadIn_Phase(self):
        return self._epics.get_channel_value("in_phase")

    def doReadTotal_Delay(self):
        return self._epics.get_channel_value("total_delay")

    def doReadPark_Command(self):
        return self._epics.get_channel_value("park_readback")

    def doReadPark_Status(self):
        return self._epics.get_channel_value("park_status")

    def doReadLast_Message(self):
        return self._epics.get_channel_value("last_message")

    def doReadDelay_Mean(self):
        return self._epics.get_channel_value("delay_mean")

    def doReadDelay_Stddev(self):
        return self._epics.get_channel_value("delay_stddev")

    def doReadDelay_Fwhm(self):
        return self._epics.get_channel_value("delay_fwhm")

    @usermethod
    def park(self, position):
        """Park the stopped disc at one of the drive's park positions, as the
        IOC names them, for example ``disc.park("ParkOpen")``. ListParams(disc)
        shows the choices under park_command. ``wait(disc)`` waits until the
        disc is there."""
        choices = self.parameters["park_command"].type.vals
        if choices and position not in choices:
            raise InvalidValueError(
                self, f"{position!r} is not one of the park choices {choices}"
            )
        ok, why = self._park_allowed()
        if not ok:
            raise LimitError(self, f"parking is not allowed: {why}")
        if self._sim_intercept:
            return
        self.resetTimeout(self.target)
        self._send_park(position)

    def doReset(self):
        """Clear the drive's alarms, if it has any: "ClearAlarm" or "Clear Alarms",
        as the IOC names it."""
        if self._read_channel_cached("alarm_level", maxage=0) == "No Alarms":
            return
        for choice in self._epics.get_channel_value_choices("command"):
            if choice.replace(" ", "").lower().startswith("clearalarm"):
                self._put_command("command", choice)
                return
        raise UsageError(self, "the drive has no command to clear alarms")

    def _compute_status(self, maxage=0):
        """The reason the disc is not OK, followed by the drive's last message."""
        severity, reason = self._status_reason(maxage)
        message = self._read_channel_cached("last_message", maxage=maxage)
        return severity, "; ".join(part for part in (reason, message) if part)

    def _status_reason(self, maxage):
        def read(channel):
            return self._read_channel_cached(channel, maxage=maxage)

        if read("chic") != "Connected":
            return status.ERROR, "no connection to the CHIC"
        level = read("alarm_level")
        if level == "Warnings":
            return status.WARN, level
        if level != "No Alarms":
            return status.ERROR, level
        mode = read("control_mode")
        if mode != "Epics":
            return status.WARN, f"controlled from {mode}, not EPICS"
        state = read("state")
        if state == "Comms not ok":
            return status.ERROR, state
        if state in TRANSITIONAL_STATES:
            return status.BUSY, state
        if state == "Ready" and self._parking(read):
            return status.BUSY, "parking"
        if state == "Rotating" and read("on_speed") != "On speed":
            return status.BUSY, "changing speed"
        if state == "Rotating" and read("in_phase") != "In phase":
            return status.BUSY, "not in phase"
        return status.OK, state

    @staticmethod
    def _parking(read):
        """Whether the disc is on its way to a park. The drive parks while both
        DcuState_R and ParkStatus_R say so: YMIR's Beckhoff drive leaves
        ParkStatus_R at Parking after the park, the SKF drives DcuState_R.
        Until the drive reports Parking, seconds after a park command, the disc
        parks while it is away from ParkS_RB, which reads 0 when there is no
        park target, as after a stop."""
        if read("dcu_state") == "Parking" and read("park_status") == "Parking":
            return True
        target = read("park_setpoint")
        if angle_distance(read("position"), target) <= PARK_TOLERANCE:
            return False
        return bool(target) or read("park_status") == "Parking"

    def _is_done(self, device, maxage=None):
        """Whether a move of the disc or one of its axes is done: the disc is
        not busy, it turns at its speed setpoint in phase or stands still, and
        the device is at its target. Raises on an error status or a timeout."""
        if device._sim_intercept:
            return True
        code, message = self.status(maxage)
        if code in self.errorstates:
            raise self.errorstates[code](device, message)
        if code != status.BUSY and self._is_steady() and device.isAtTarget():
            device._targetReached()
            return True
        if device.isTimedOut():
            raise PositionError(
                device, f"not done after {device.timeout:.0f} s: {message}"
            )
        return False

    def _is_steady(self):
        """Whether the disc runs at its speed setpoint, in phase, or is stopped.
        The setpoint and InPhaseTS-R are read from the IOC: their cached values
        lag a new setpoint."""
        setpoint = self._read_channel_cached("speed_setpoint", maxage=0)
        state = self._read_channel_cached("state")
        if not setpoint:
            return state == "Ready"
        return (
            state == "Rotating"
            and self._read_channel_cached("on_speed") == "On speed"
            and self._read_channel_cached("in_phase", maxage=0) == "In phase"
        )

    def _speed_allowed(self, speed):
        if self._sim_intercept:
            return True, ""
        max_speed = self._read_channel_cached("max_speed", maxage=0)
        if max_speed and abs(speed) > max_speed:
            return False, f"the disc's maximum speed is {max_speed} Hz"
        return True, ""

    def _phase_allowed(self, phase):
        if not 0 <= phase < 360:
            return False, "the phase must be in [0, 360) degrees"
        return True, ""

    def _park_allowed(self):
        if self._sim_intercept:
            return True, ""
        if self._read_channel_cached("state", maxage=0) != "Ready":
            return False, "stop the disc before parking it"
        return True, ""

    def _start_speed(self, speed):
        """Write the speed and Start, or Stop for 0, unless the disc already
        runs steadily at that speed."""
        setpoint = self._read_channel_cached("speed_setpoint", maxage=0)
        if setpoint == speed and self._is_steady():
            return
        self._write_setpoint("speed_setpoint", speed)
        self._put_command("command", "Start" if speed else "Stop")

    def _start_phase(self, phase):
        """Write the phase as ChopDly-S at the speed setpoint, unless the disc
        is already steady at that phase."""
        if abs(phase - self._phase(0)) < 1e-6 and self._is_steady():
            return
        speed = self._read_channel_cached("speed_setpoint", maxage=0)
        self._write_setpoint("delay", phase / 360 / abs(speed) * 1e9)

    def _write_setpoint(self, channel, value):
        """Write a speed or delay. The IOC then restarts its statistics and
        drops InPhaseTS-R until the disc is in phase at the new setpoint."""
        self._epics.put_channel_value(channel, value)
        if self._read_channel_cached(
            "speed_setpoint", maxage=0
        ) and not self._acknowledged("in_phase", "Not in phase"):
            raise MoveError(
                self,
                "the IOC did not restart its in-phase statistics for the new "
                "setpoint (that needs evr_seq_calc 2.7.6 or later)",
            )

    def _send_park(self, position):
        """Send a park command. The drive reports Parking only seconds later,
        so wait for it to take the command and its new target (ParkS_RB)."""
        target = self._read_channel_cached("park_setpoint", maxage=0)
        self._put_command("park", position)
        if not self._acknowledged("park_readback", position):
            raise self._refused(f"take the park command {position}")
        # a park to the target already set leaves ParkS_RB unchanged
        self._acknowledged("park_setpoint", lambda new: new != target)

    def _park_at(self, angle):
        """Park at a resolver position. The drive acts on a change of Park_S:
        to park at the angle it already holds, send ParkSP."""
        if self._epics.get_channel_value("park_angle") == angle:
            self._put_command("park", "ParkSP")
        else:
            self._epics.put_channel_value("park_angle", angle)
        if not self._acknowledged(
            "park_setpoint", lambda new: angle_distance(new, angle) <= 0.01
        ):
            raise self._refused(f"take the park angle {angle}")

    def _put_command(self, channel, value):
        """The drive acts on a change of a command PV: to send the command it
        already holds, write its no-command choice in between ("Null" or "No
        request", as the IOC names it), and hold it long enough for the PLC to
        see it."""
        if self._epics.get_channel_value(channel) == value:
            for no_command in self._epics.get_channel_value_choices(channel):
                if no_command.replace(" ", "").lower() in ("null", "norequest"):
                    break
            else:
                raise UsageError(
                    self, f"the drive has no Null command to send {value} again"
                )
            self._epics.put_channel_value(channel, no_command)
            session.delay(NO_COMMAND_HOLD)
        self._epics.put_channel_value(channel, value)

    def _acknowledged(self, channel, expected, precision=None):
        """Wait for the IOC to acknowledge a write: False if it answers but does
        not, raises if it does not answer at all."""
        try:
            self._epics.wait_for(channel, expected, timeout=2.0, precision=precision)
        except CommunicationError:
            self._epics.get_channel_value(channel)
            return False
        return True

    def _refused(self, what):
        message = self._read_channel_cached("last_message", maxage=0)
        return MoveError(self, f"the drive did not {what}; its last message: {message}")

    def get_chopper_gui_info(self):
        """Geometry and the cache keys the chopper panel subscribes to."""
        info = {
            "chopper": self.name,
            "speed_key": f"{self.name}/speed_readback",
            "total_delay_key": f"{self.name}/total_delay",
            "park_angle_key": f"{self.name}/position",
            "delay_errors_key": f"{self.name}/delay_errors",
            "legacy_spd_sign": self.legacy_spd_sign,
        }
        info.update(self._geometry_gui_info())
        return info


class EssT0Chopper(EssChopper):
    """The DREAM T0 chopper: commands on C_Execute, parks in the ParkPos_S
    windows. Parking at an angle sets the selected window's angle."""

    _command_pv = "C_Execute"
    _park_pv = "ParkPos_S"
    _park_readback_pv = "ParkPos_RB"

    def _send_park(self, position):
        """Select a park window. Its first choice, Close, parks the disc, so it
        is no "Null" to write in between, and ParkS_RB does not follow."""
        self._epics.put_channel_value("park", position)
        if not self._acknowledged("park_readback", position):
            raise self._refused(f"take the park command {position}")

    def _park_at(self, angle):
        self._epics.put_channel_value("park_angle", angle)


class ChopperAxis(HasTimeout, AutoDevice, Moveable):
    """Speed, phase or position of an ``EssChopper`` disc, read and moved
    through it. The status is the disc's."""

    attached_devices = {
        "chopper": Attach("The chopper disc", EssChopper),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%.3f"),
        "timeout": Override(default=MOVE_TIMEOUT),
    }

    valuetype = float
    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    def doStatus(self, maxage=0):
        return self._attached_chopper.status(maxage)

    def doIsCompleted(self):
        return self._attached_chopper._is_done(self)


class ChopperSpeed(ChopperAxis):
    """Speed of the disc in Hz, with the sign of the speed PVs."""

    parameter_overrides = {
        "unit": Override(default="Hz", mandatory=False, settable=False),
    }

    def doRead(self, maxage=0):
        return self._attached_chopper._read_channel_cached(
            "speed_readback", maxage=maxage
        )

    def doReadTarget(self):
        return self._attached_chopper._read_channel_cached("speed_setpoint")

    def doIsAllowed(self, target):
        return self._attached_chopper._speed_allowed(target)

    def doStart(self, target):
        self._attached_chopper._start_speed(target)


class ChopperPhase(ChopperAxis):
    """Phase of the disc in degrees: ChopDly-S at the speed setpoint. The IOC
    has no readback, so the value is the setpoint."""

    parameter_overrides = {
        "unit": Override(default="deg", mandatory=False, settable=False),
    }

    def doRead(self, maxage=0):
        return self._attached_chopper._phase(maxage)

    def doReadTarget(self):
        return self.doRead(None)

    def doIsAllowed(self, target):
        chopper = self._attached_chopper
        ok, why = chopper._phase_allowed(target)
        if not ok or chopper._sim_intercept:
            return ok, why
        if not chopper._read_channel_cached("speed_setpoint", maxage=0):
            return False, "set a speed before the phase"
        return True, ""

    def doStart(self, target):
        self._attached_chopper._start_phase(target)


class ChopperPosition(HasPrecision, ChopperAxis):
    """Resolver position of the disc in degrees. Moving it parks the stopped
    disc there; the move completes when the drive is done and the disc is
    within the precision, which can take some seconds after the drive reports
    Ready."""

    parameter_overrides = {
        "unit": Override(default="deg", mandatory=False, settable=False),
        "precision": Override(default=0.1),
        "timeout": Override(default=60.0),
    }

    def doRead(self, maxage=0):
        return self._attached_chopper._read_channel_cached("position", maxage=maxage)

    def doIsAllowed(self, target):
        if not 0 <= target < 360:
            return False, "the position must be in [0, 360) degrees"
        return self._attached_chopper._park_allowed()

    def doStart(self, target):
        self._attached_chopper._park_at(target)

    def doIsAtTarget(self, pos, target):
        return target is None or angle_distance(pos, target) <= self.precision

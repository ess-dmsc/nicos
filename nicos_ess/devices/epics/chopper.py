import time

from nicos.core import (
    Attach,
    CommunicationError,
    DeviceMixinBase,
    Moveable,
    MoveError,
    Override,
    Param,
    Readable,
    UsageError,
    Waitable,
    listof,
    none_or,
    oneof,
    pvname,
    status,
)
from nicos.core.mixins import AutoDevice, HasAutoDevices
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.chopper_math import phase_deg
from nicos_ess.devices.epics.pva import (
    EpicsManualMappedAnalogMoveable,
    EpicsMappedReadable,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    EpicsEnumParam,
    EpicsStatusOnlyReadable,
    enum_readback_channel,
    enum_setpoint_channel,
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

TRANSITIONAL_STATES = (
    "Initialization",
    "Coasting",
    "Stopping",
    "I. stopping",
    "E. stopping",
)


class EssChopper(HasChopperGeometry, HasAutoDevices, EpicsDeviceBase, Waitable):
    """One ESS chopper disc.

    The value is the chopper state, and the status says what the disc is doing,
    followed by the drive's last log message. Move the disc with::

        maw(disc.speed, 14)    # Hz, as the speed PVs have it; 0 stops the disc
        maw(disc.phase, 120)   # degrees, written as ChopDly-S at the target speed

    Set the speed before the phase: the phase is kept as a delay, so its value
    in degrees changes with the speed. A new speed or delay restarts the IOC's
    statistics and drops InPhaseTS-R to Not in phase (evr_seq_calc 2.7.6); a
    move completes when it reads In phase again with the disc at speed.
    Stopping a script leaves the discs turning.

    The drive commands and parking take the IOC's own choices::

        disc.command = "Start"          # the choices are in ListParams(disc)
        disc.park = "ParkOpen"          # the stopped disc only; wait(disc)
        disc.park_angle = 42            # resolver position, stopped disc only
        reset(disc)                     # clear the drive's alarms
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
        "park_position": Param(
            "Resolver position of the disc", type=float, unit="deg", volatile=True
        ),
        "command": Param(
            "Command to the drive, one of the IOC's choices",
            type=EpicsEnumParam("command"),
            settable=True,
            volatile=True,
        ),
        "park": Param(
            "Park command for the stopped disc, one of the IOC's choices",
            type=EpicsEnumParam("park"),
            settable=True,
            volatile=True,
        ),
        "park_angle": Param(
            "Resolver position to park the stopped disc at",
            type=float,
            unit="deg",
            settable=True,
            volatile=True,
        ),
        "delay": Param("The phase as ChopDly-S", type=float, unit="ns", volatile=True),
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
        "unit": Override(default="", mandatory=False, settable=False),
        "fmtstr": Override(default="%s"),
    }

    valuetype = str
    errorstates = {**Waitable.errorstates, status.UNKNOWN: MoveError}

    _command_pv = "C_ExecuteUser"
    _park_pv = "C_Park"
    _park_readback_pv = "ParkCmd_RB"
    _park_setpoint_readback = True
    _park_is_command = True

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "state"

    def _build_epics_channels(self):
        return {
            "state": enum_readback_channel(
                "ChopState_R", cache_key="value", primary=True
            ),
            "in_phase": enum_status_channel("InPhaseTS-R", cache_key="in_phase"),
            "on_speed": enum_status_channel("OnSpd_R"),
            "park_status": enum_status_channel("ParkStatus_R", cache_key="park_status"),
            "chic": enum_status_channel("ConnectedR", pv_prefix_attr="chic_root"),
            "alarm_level": enum_status_channel("Lvl_Alrm"),
            "control_mode": enum_status_channel("CtrlMd_RB"),
            "last_message": status_channel(
                "Log_R", cache_key="last_message", as_string=True
            ),
            "total_delay": readback_channel("TotDly", cache_key="total_delay"),
            "park_position": readback_channel(
                "Pos_R", cache_key="park_position", refresh_status=True
            ),
            "park_setpoint": readback_channel("ParkS_RB", refresh_status=True),
            "park_readback": enum_readback_channel(
                self._park_readback_pv, subscribe=False
            ),
            "delay_mean": readback_channel("DiffTSMean", cache_key="delay_mean"),
            "delay_stddev": readback_channel("DiffTSStdDev", cache_key="delay_stddev"),
            "delay_fwhm": readback_channel("DiffTSFWHMWidth", cache_key="delay_fwhm"),
            "delay_errors": readback_channel("DiffTSSamples", cache_key="delay_errors"),
            "command": enum_setpoint_channel(self._command_pv, cache_key="command"),
            "park": enum_setpoint_channel(self._park_pv, cache_key="park"),
            "park_angle": setpoint_channel("Park_S", cache_key="park_angle"),
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
        for name, cls in (("speed", ChopperSpeed), ("phase", ChopperPhase)):
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

    def doReadIn_Phase(self):
        return self._epics.get_channel_value("in_phase")

    def doReadTotal_Delay(self):
        return self._epics.get_channel_value("total_delay")

    def doReadPark_Position(self):
        return self._epics.get_channel_value("park_position")

    def doReadCommand(self):
        return self._epics.get_channel_value("command")

    def doWriteCommand(self, value):
        self._put_command("command", value)

    def doReadPark(self):
        return self._epics.get_channel_value("park")

    def doWritePark(self, value):
        """Park the stopped disc. The drive reports Parking only seconds later,
        so wait for it to take the command and its new target (ParkS_RB)."""
        self._check_stopped()
        target = self._read_channel_cached("park_setpoint", maxage=0)
        if self._park_is_command:
            self._put_command("park", value)
        else:
            self._epics.put_channel_value("park", value)
        if not self._acknowledged("park_readback", value):
            raise self._refused(f"take the park command {value}")
        if self._park_setpoint_readback:
            # a park to the target already set leaves ParkS_RB unchanged
            self._acknowledged("park_setpoint", lambda new: new != target)

    def doReadPark_Angle(self):
        return self._epics.get_channel_value("park_angle")

    def doWritePark_Angle(self, value):
        self._check_stopped()
        self._epics.put_channel_value("park_angle", value)
        if self._park_setpoint_readback and not self._acknowledged(
            "park_setpoint", value, precision=0.01
        ):
            raise self._refused(f"take the park angle {value}")

    def doReadDelay(self):
        return self._epics.get_channel_value("delay")

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
        return status.OK, ""

    @staticmethod
    def _parking(read):
        """Whether the disc is on its way to a park. ParkStatus_R is not enough:
        YMIR's drive reports Parking seconds late and never stops reporting it.
        ParkS_RB reads 0 when there is no park target, as after a stop."""
        target = read("park_setpoint")
        distance = abs(read("park_position") - target) % 360
        if min(distance, 360 - distance) <= PARK_TOLERANCE:
            return False
        return bool(target) or read("park_status") == "Parking"

    def doReset(self):
        """Clear the drive's alarms, if it has any: "ClearAlarm" or "Clear Alarms",
        as the IOC names it."""
        if self._read_channel_cached("alarm_level", maxage=0) == "No Alarms":
            return
        for choice in self.parameters["command"].type.vals:
            if choice.replace(" ", "").lower().startswith("clearalarm"):
                self._send(choice)
                return
        raise UsageError(self, "the drive has no command to clear alarms")

    def _check_stopped(self):
        if self.read(0) != "Ready":
            raise UsageError(self, "stop the disc before parking it")

    def _send(self, command):
        self._put_command("command", command)

    def _put_command(self, channel, value):
        """The drive acts on a change of a command PV: to send the command it
        already holds, write the PV's first, no-command choice in between."""
        if self._epics.get_channel_value(channel) == value:
            no_command = self.parameters[channel].type.vals[0]
            self._epics.put_channel_value(channel, no_command)
        self._epics.put_channel_value(channel, value)

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

    def _is_steady(self):
        """Whether the disc runs at its speed setpoint, in phase, or is stopped.
        The setpoint and InPhaseTS-R are read from the IOC: their cached values
        lag a new setpoint."""
        setpoint = self._read_channel_cached("speed_setpoint", maxage=0)
        state = self.read()
        if not setpoint:
            return state == "Ready"
        return (
            state == "Rotating"
            and self._read_channel_cached("on_speed") == "On speed"
            and self._read_channel_cached("in_phase", maxage=0) == "In phase"
        )

    def get_chopper_gui_info(self):
        """Geometry and the cache keys the chopper panel subscribes to."""
        info = {
            "chopper": self.name,
            "speed_key": f"{self.name}/speed_readback",
            "total_delay_key": f"{self.name}/total_delay",
            "park_angle_key": f"{self.name}/park_position",
            "delay_errors_key": f"{self.name}/delay_errors",
            "legacy_spd_sign": self.legacy_spd_sign,
        }
        info.update(self._geometry_gui_info())
        return info


class EssT0Chopper(EssChopper):
    """The DREAM T0 chopper: commands on C_Execute, parks in the ParkPos_S
    windows. Setting the park angle sets the selected window's angle."""

    _command_pv = "C_Execute"
    _park_pv = "ParkPos_S"
    _park_readback_pv = "ParkPos_RB"
    # ParkS_RB does not follow the park target on the T0
    _park_setpoint_readback = False
    # ParkPos_S selects a park window; its first choice, Close, parks the disc
    _park_is_command = False


class ChopperAxis(AutoDevice, Moveable):
    """Speed or phase of an ``EssChopper`` disc, read and moved through it.
    The status is the disc's; a move completes when the disc is in phase at
    its new setpoint."""

    attached_devices = {
        "chopper": Attach("The chopper disc", EssChopper),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%.3f"),
    }

    valuetype = float
    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    def doStatus(self, maxage=0):
        return self._attached_chopper.status(maxage)

    def doStart(self, target):
        if not self._is_setpoint(target) or not self._attached_chopper._is_steady():
            self._write(target)

    def doIsCompleted(self):
        if self._sim_intercept:
            return True
        chopper = self._attached_chopper
        current, message = chopper.status()
        if current in self.errorstates:
            raise self.errorstates[current](self, message)
        return chopper._is_steady()


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
        if self._sim_intercept:
            return True, ""
        max_speed = self._attached_chopper._read_channel_cached("max_speed", maxage=0)
        if max_speed and abs(target) > max_speed:
            return False, f"the disc's maximum speed is {max_speed} Hz"
        return True, ""

    def _is_setpoint(self, target):
        chopper = self._attached_chopper
        return chopper._read_channel_cached("speed_setpoint", maxage=0) == target

    def _write(self, target):
        chopper = self._attached_chopper
        chopper._write_setpoint("speed_setpoint", target)
        chopper._send("Start" if target else "Stop")


class ChopperPhase(ChopperAxis):
    """Phase of the disc in degrees: ChopDly-S at the speed setpoint. The IOC
    has no readback, so the value is the setpoint."""

    parameter_overrides = {
        "unit": Override(default="deg", mandatory=False, settable=False),
    }

    def doRead(self, maxage=0):
        chopper = self._attached_chopper
        return phase_deg(
            chopper._read_channel_cached("delay", maxage=maxage),
            chopper._read_channel_cached("speed_setpoint", maxage=maxage),
        )

    def doReadTarget(self):
        return self.doRead(None)

    def doIsAllowed(self, target):
        if not 0 <= target < 360:
            return False, "the phase must be in [0, 360) degrees"
        if self._sim_intercept:
            return True, ""
        if not self._attached_chopper._read_channel_cached("speed_setpoint", maxage=0):
            return False, "set a speed before the phase"
        return True, ""

    def _is_setpoint(self, target):
        return abs(target - self.read(0)) < 1e-6

    def _write(self, target):
        chopper = self._attached_chopper
        speed = chopper._read_channel_cached("speed_setpoint", maxage=0)
        chopper._write_setpoint("delay", target / 360 / abs(speed) * 1e9)

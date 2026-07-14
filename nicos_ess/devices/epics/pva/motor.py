import math
import threading
import time
from dataclasses import replace

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Moveable,
    Override,
    Param,
    Readable,
    limits,
    oneof,
    pvname,
    status,
)
from nicos.core.errors import CommunicationError, ConfigurationError, MoveError
from nicos.core.mixins import CanDisable, HasLimits, HasOffset
from nicos.devices.abstract import Motor
from nicos.devices.epics.status import SEVERITY_TO_STATUS
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    command_channel,
    get_from_cache_or,
    readback_channel,
    setpoint_channel,
    status_channel,
    worst_status,
)
from nicos_ess.devices.mixins import CanReferenceWithWarning


class EpicsMotor(
    EpicsDeviceBase, CanDisable, CanReferenceWithWarning, HasOffset, Motor
):
    """
    This device exposes some of the functionality provided by the EPICS motor
    record. The PV names for the fields of the record (readback, speed, etc.)
    are derived by combining the motorpv-parameter with the predefined field
    names.

    The has_errorbit and has_reseterror can be provided optionally in case the
    controller supports reporting errors and a reset-mechanism that tries to
    recover from certain errors. If present, these are used when calling the
    reset()-method.

    Another optional parameter is the has_msgtxt, which contains an error message that
    may originate from the motor controller or the IOC. If it is present,
    doStatus uses it for some of the status messages.

    Devices also have an option to include a pop-up message when homing is used
    via the home_warning_msg parameter which allows for a custom confirmation
    message before homing. If the parameter is not set, then no confirmation
    message will occur before homing starts.
    """

    valuetype = float
    limit_rel_tolerance = 1e-12
    errorstates = {**Motor.errorstates, status.UNKNOWN: MoveError}

    _primary_channel = "value"
    _default_pv_prefix_attr = "motorpv"
    # One PV is enough to see that the IOC is there.
    _connect_channels = ("value",)

    parameters = {
        "motorpv": Param(
            "Name of the motor record PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "has_powerauto": Param(
            "Optional PV for auto enable power.",
            type=bool,
            default=True,
            mandatory=False,
            settable=False,
            userparam=False,
        ),
        "has_msgtxt": Param(
            "Optional PV with error message.",
            type=bool,
            default=True,
            mandatory=False,
            settable=False,
            userparam=False,
        ),
        "has_errorbit": Param(
            "Optional PV with error bit.",
            type=bool,
            default=True,
            mandatory=False,
            settable=False,
            userparam=False,
        ),
        "has_reseterror": Param(
            "Optional PV with error reset switch.",
            type=bool,
            default=True,
            mandatory=False,
            settable=False,
            userparam=False,
        ),
        "reference_direction": Param(
            "Reference run direction.",
            type=oneof("forward", "reverse"),
            default="forward",
            settable=False,
            userparam=False,
            mandatory=False,
        ),
        "position_deadband": Param(
            "Acceptable distance between target and final position.",
            type=float,
            settable=False,
            volatile=True,
            userparam=False,
            mandatory=False,
        ),
        "pv_desc": Param(
            "The description defined at the EPICS level.",
            type=str,
            settable=False,
            volatile=True,
            userparam=False,
            mandatory=False,
        ),
        "monitor_deadband": Param(
            "Deadband for monitor callback.",
            type=float,
            settable=True,
            volatile=True,
            userparam=True,
            mandatory=False,
        ),
        "hwuserlimits": Param(
            "Unchangeable hardware user limits, diallimits with applied "
            "offset and direction.",
            type=limits,
            settable=False,
            volatile=True,
            userparam=False,
            mandatory=False,
            category="limits",
            fmtstr="main",
            unit="main",
        ),
        "limitoffsets": Param(
            "Offsets to be applied to the hardware user limits.",
            type=tuple,
            default=(0.0, 0.0),
            settable=True,
            userparam=False,
            mandatory=False,
            fmtstr="main",
            unit="main",
        ),
        "use_prec": Param(
            "Format string for the readback value is based on the EPICS PREC field",
            type=bool,
            default=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        # speed, limits and offset may change from outside, can't rely on cache
        "speed": Override(volatile=True),
        "offset": Override(volatile=True, chatty=False),
        "abslimits": Override(volatile=True, mandatory=False),
        "userlimits": Override(volatile=True, chatty=False),
        # Units and precision are set by EPICS, so cannot be changed
        "unit": Override(mandatory=False, settable=False, volatile=True),
        "precision": Override(mandatory=False, settable=False, volatile=True),
    }

    def init(self):
        # Do not call Moveable init as it does some limit checks
        # which we don't want because the NICOS offset is opposite of the EPICS one.
        # Skipping EpicsDeviceBase.init too, so clone enum params here.
        self._clone_epics_enum_params()
        Readable.init(self)

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._motor_status = (status.OK, "")
        EpicsDeviceBase.doPreinit(self, mode)

    def _build_epics_channels(self):
        epics_channels = {
            "value": readback_channel(".RBV", cache_key="value", primary=True),
            "dialvalue": readback_channel(".DRBV"),
            "target": setpoint_channel(".VAL", cache_key="target"),
            "stop": command_channel(".STOP"),
            "speed": readback_channel(".VELO"),
            "offset": readback_channel(".OFF"),
            "highlimit": readback_channel(".HLM"),
            "lowlimit": readback_channel(".LLM"),
            "dialhighlimit": readback_channel(".DHLM"),
            "diallowlimit": readback_channel(".DLLM"),
            "enable": status_channel(".CNEN"),
            "set": command_channel(".SET"),
            "foff": command_channel(".FOFF"),
            "dir": readback_channel(".DIR"),
            "homeforward": readback_channel(".HOMF"),
            "homereverse": readback_channel(".HOMR"),
            "position_deadband": readback_channel(".RDBD"),
            "description": readback_channel(".DESC"),
            "monitor_deadband": readback_channel(".MDEL"),
            "prec": readback_channel(
                ".PREC",
                cache_key="fmtstr",
                affects_status=False,
                connect_on_startup=False,
                refresh_status=False,
            ),
            "maxspeed": readback_channel(".VMAX"),
            "minspeed": readback_channel(".VBAS"),
            "donemoving": status_channel(".DMOV"),
            "moving": status_channel(".MOVN"),
            "miss": status_channel(".MISS"),
            "alarm_status": status_channel(".STAT"),
            "alarm_severity": status_channel(".SEVR"),
            "softlimit": status_channel(".LVIO"),
            "lowlimitswitch": status_channel(".LLS"),
            "highlimitswitch": status_channel(".HLS"),
            "errorbit": status_channel("-Err"),
            "reseterror": command_channel("-ErrRst"),
            "powerauto": status_channel("-PwrAuto"),
            "msgtxt": status_channel("-MsgTxt"),
            "msgtxt_severity": status_channel("-MsgTxt.SEVR"),
        }

        if not self.has_errorbit:
            del epics_channels["errorbit"]
        if not self.has_reseterror:
            del epics_channels["reseterror"]
        if not self.has_powerauto:
            del epics_channels["powerauto"]
        if not self.has_msgtxt:
            del epics_channels["msgtxt"]
            del epics_channels["msgtxt_severity"]
        if not self.use_prec:
            del epics_channels["prec"]
        return epics_channels

    def _after_subscribe(self, mode):
        if mode != SIMULATION and session.sessiontype != POLLER and self.use_prec:
            self.parameters["fmtstr"].settable = False

    def _on_channel_update(self, update):
        if update.channel == "prec":
            update = replace(update, value=f"%.{update.value}f")
        super()._on_channel_update(update)
        ts = time.time()
        if update.channel == "position_deadband":
            self._cache.put(self._name, "precision", update.value, ts)
        elif update.channel == "description":
            self._cache.put(self._name, "pv_desc", update.value, ts)
        elif update.channel in ("lowlimit", "highlimit"):
            low = self._cache.get(self._name, "lowlimit", Ellipsis)
            high = self._cache.get(self._name, "highlimit", Ellipsis)
            if low is not Ellipsis and high is not Ellipsis:
                hwlimits = (low, high)
                self._cache.put(self._name, "hwuserlimits", hwlimits, ts)
                self._cache.put(
                    self._name,
                    "userlimits",
                    self._userlimits_from_hardware(hwlimits),
                    ts,
                )
        if update.channel in ("diallowlimit", "dialhighlimit"):
            # Keep the cached "abslimits" in step with the dial limits, as it
            # is the value NICOS uses; doReadAbslimits only refreshes it when
            # the parameter is polled.
            low = self._read_channel_cached("diallowlimit")
            high = self._read_channel_cached("dialhighlimit")
            self._cache.put(self._name, "abslimits", (low, high), time.time())

    def doReadSpeed(self):
        return self._epics.get_channel_value("speed")

    def doReadOffset(self):
        return self._epics.get_channel_value("offset")

    def doReadTarget(self):
        return self._read_channel_cached("target")

    def doReadAbslimits(self):
        dial_min = self._epics.get_channel_value("diallowlimit")
        dial_max = self._epics.get_channel_value("dialhighlimit")
        return dial_min, dial_max

    def doReadHwuserlimits(self):
        dial_min = self._epics.get_channel_value("diallowlimit")
        dial_max = self._epics.get_channel_value("dialhighlimit")
        if dial_min > dial_max:
            raise ConfigurationError(
                self,
                f"dial lowlimit ({dial_min}) above dial highlimit ({dial_max})",
            )
        offset = self.offset
        hw_user_min = self._epics.get_channel_value("lowlimit")
        hw_user_max = self._epics.get_channel_value("highlimit")
        if hw_user_min > hw_user_max:
            raise ConfigurationError(
                self,
                f"hardware user lowlimit ({hw_user_min}) above hardware user "
                f"highlimit ({hw_user_max})",
            )
        if not self._user_limits_fit_dial_window(
            hw_user_min, hw_user_max, dial_min, dial_max, offset
        ):
            direction = self._epics.get_channel_value("dir", as_string=True)
            raise ConfigurationError(
                self,
                f"hardware userlimits ({hw_user_min}, {hw_user_max}) are "
                f"inconsistent with dial limits ({dial_min}, {dial_max}), "
                f"offset ({offset}) and direction ({direction})",
            )
        return hw_user_min, hw_user_max

    def doReadUserlimits(self):
        return self._userlimits_from_hardware(self.hwuserlimits)

    def _userlimits_from_hardware(self, hwlimits):
        hw_umin, hw_umax = hwlimits
        omin, omax = self.limitoffsets

        umin = hw_umin + omin
        umax = hw_umax + omax

        if umax < umin:
            # Old offsets are no longer consistent with the current hardware window.
            # Fall back to the EPICS hardware user limits.
            umin, umax = hw_umin, hw_umax
            new_omin, new_omax = 0.0, 0.0
        else:
            # normal clipping logic
            umin = max(min(umin, hw_umax), hw_umin)
            umax = max(min(umax, hw_umax), hw_umin)

            new_omin = umin - hw_umin
            new_omax = umax - hw_umax

        self._setROParam(
            "limitoffsets",
            (new_omin, new_omax),
        )
        return umin, umax

    def doReadPosition_Deadband(self):
        return self._epics.get_channel_value("position_deadband")

    def doReadPv_Desc(self):
        return self._epics.get_channel_value("description")

    def doReadMonitor_Deadband(self):
        return self._epics.get_channel_value("monitor_deadband")

    def doReadPrecision(self):
        return self._epics.get_channel_value("position_deadband")

    def doIsAtTarget(self, pos=None, target=None):
        return self._read_channel_cached("miss") == 0

    def doIsCompleted(self):
        if self._sim_intercept:
            return True

        cur_status, cur_message = self.status(0)
        if cur_status in self.busystates:
            return False
        if cur_status in self.errorstates:
            raise self.errorstates[cur_status](self, cur_message)

        moving = self._read_channel_cached("moving")
        pos = self._read_channel_cached("value")
        target = self._read_channel_cached("target")
        deadband = self._read_channel_cached("position_deadband")

        # check whether target has been reached within deadband:
        if not math.isclose(target, pos, abs_tol=deadband):
            return False
        return moving == 0

    def doStart(self, value):
        if abs(self.read(0) - value) <= self.precision:
            return

        self._epics.put_channel_value("target", value)

    def doWriteSpeed(self, value):
        speed = self._get_valid_speed(value)

        if speed != value:
            self.log.warning(
                "Selected speed %s is outside the parameter limits, using %s instead.",
                value,
                speed,
            )

        self._epics.put_channel_value("speed", speed)
        return speed

    def doWriteMonitor_Deadband(self, value):
        deadband = value
        self._epics.put_channel_value("monitor_deadband", max(deadband, 0))

    def doWriteOffset(self, new_off):
        """Shift the user/dial offset via SET/FOFF."""
        if self.offset == new_off:
            return

        if self._epics.get_channel_value("moving") or not self._epics.get_channel_value(
            "donemoving"
        ):
            raise RuntimeError(f"{self}: cannot change OFF while motor is moving")

        dir_sign = (
            1 if self._epics.get_channel_value("dir", as_string=True) == "Pos" else -1
        )
        dial_now = self._epics.get_channel_value("dialvalue")
        user_target = dial_now * dir_sign + new_off  # user = dial * DIR + OFF

        # In SET mode with FOFF=0, writing VAL makes the record recalculate OFF.
        self._epics.put_channel_value("set", 1)
        try:
            self._epics.put_channel_value("foff", 0)
            self._epics.put_channel_value("target", user_target)
        finally:
            self._epics.put_channel_value("set", 0)
        self._epics.wait_for("donemoving", 1)
        self.log.info("Offset changed to %s", new_off)

    def doWriteUserlimits(self, value):
        self._checkLimits(value)

        umin, umax = value
        hwumin, hwumax = self.hwuserlimits

        omin = umin - hwumin
        omax = umax - hwumax
        self.limitoffsets = (omin, omax)

    def doAdjust(self, oldvalue, newvalue):
        # For EPICS the offset sign convention differs to that of the base
        # implementation.
        diff = oldvalue - newvalue
        self.offset -= diff

    def doStop(self):
        self._epics.put_channel_value("stop", 1)

    def doReset(self):
        if self.has_errorbit and self.has_reseterror:
            error_bit = self._read_channel_cached("errorbit")
            if error_bit == 0:
                self.log.warning("Error bit is not set, can not reset error state.")
            else:
                self._epics.put_channel_value("reseterror", 1)

    def doReference(self):
        self._epics.put_channel_value(f"home{self.reference_direction}", 1)

    def doEnable(self, on):
        self._epics.put_channel_value("enable", 1 if on else 0)

    def doSetPosition(self, pos):
        self._epics.put_channel_value("set", 1)
        try:
            self._epics.put_channel_value("foff", 1)
            self._epics.put_channel_value("target", pos)
        finally:
            self._epics.put_channel_value("set", 0)
            self._epics.put_channel_value("foff", 0)
        self._epics.wait_for("donemoving", 1)

    def isAllowed(self, pos):
        if self.userlimits == (0, 0) and self.abslimits == (0, 0):
            # No limits defined
            return True, ""
        return Moveable.isAllowed(self, pos)

    def _compute_status(self, maxage=0):
        try:
            return self._compute_status_from_pvs(maxage)
        except (TimeoutError, CommunicationError):
            return status.UNKNOWN, "lost connection to EPICS"
        except KeyError as err:
            return status.ERROR, f"error reading motor status: {err}"

    def _compute_status_from_pvs(self, maxage):
        with self._lock:
            epics_status, message = self._get_alarm_status_and_msg(maxage)
            self._motor_status = epics_status, message
        message = (message or "").strip()
        status_candidates = [self._alarm_status_candidate(epics_status, message)]

        done_moving = self._read_channel_cached("donemoving", maxage=maxage)
        moving = self._read_channel_cached("moving", maxage=maxage)
        if done_moving == 0 or moving != 0:
            homing = self._read_channel_cached(
                "homeforward", maxage=maxage
            ) or self._read_channel_cached("homereverse", maxage=maxage)
            if homing:
                status_candidates.append((status.BUSY, message or "homing"))
            else:
                target = self._read_channel_cached("target", maxage=maxage)
                status_candidates.append(
                    (status.BUSY, message or f"moving to {target}")
                )

        if self.has_powerauto:
            powerauto_enabled = self._read_channel_cached("powerauto", maxage=maxage)
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._read_channel_cached(
            "enable", maxage=maxage
        ):
            status_candidates.append((status.WARN, "motor is not enabled"))

        miss = self._read_channel_cached("miss", maxage=maxage)
        if miss != 0:
            status_candidates.append(
                (status.NOTREACHED, message or "did not reach target position.")
            )

        high_limitswitch = self._read_channel_cached("highlimitswitch", maxage=maxage)
        if high_limitswitch != 0:
            status_candidates.append((status.WARN, message or "at high limit switch."))

        low_limitswitch = self._read_channel_cached("lowlimitswitch", maxage=maxage)
        if low_limitswitch != 0:
            status_candidates.append((status.WARN, message or "at low limit switch."))

        limit_violation = self._read_channel_cached("softlimit", maxage=maxage)
        if limit_violation != 0:
            status_candidates.append((status.WARN, message or "soft limit violation."))
        return worst_status(*status_candidates)

    def _get_valid_speed(self, value):
        max_speed = self._read_channel_cached("maxspeed")
        min_speed = self._read_channel_cached("minspeed")

        # Cannot be less than min speed
        valid_speed = max(min_speed, value)

        # In EPICS if max speed is 0 then there is no limit
        if max_speed > 0.0:
            valid_speed = min(max_speed, valid_speed)

        return valid_speed

    @staticmethod
    def _alarm_status_candidate(epics_status, message):
        if epics_status in (status.ERROR, status.UNKNOWN):
            return epics_status, message or "Unknown problem in record"
        if epics_status == status.WARN:
            return status.WARN, message
        return status.OK, message

    def _get_msgtxt(self, maxage=0):
        msg_txt = self._read_channel_cached(
            "msgtxt", as_string=True, maxage=maxage
        ).strip()

        if "msgtxt_severity" in self._epics_channels:
            msg_severity = self._read_channel_cached("msgtxt_severity", maxage=maxage)
        else:
            msg_severity = 0
        msg_stat = SEVERITY_TO_STATUS.get(msg_severity, status.UNKNOWN)
        return msg_stat, msg_txt

    def _update_status_with_msgtxt(self, motor_stat, motor_msg, maxage=0):
        motor_msg = (motor_msg or "").strip()
        msg_stat, msg_txt = self._get_msgtxt(maxage)
        # MsgTxt severity can only raise the motor status, never lower it.
        merged_stat = max(msg_stat, motor_stat)

        if merged_stat == status.OK:
            merged_msg = ""
        else:
            motor_alarm_active = motor_stat != status.OK and bool(motor_msg)
            msgtxt_alarm_active = msg_stat != status.OK and bool(msg_txt)
            if motor_alarm_active and msgtxt_alarm_active:
                merged_msg = f"{msg_txt}, motor alarm: {motor_msg}"
            elif msgtxt_alarm_active:
                merged_msg = msg_txt
            else:
                merged_msg = motor_msg

        if self._motor_status != (merged_stat, merged_msg):
            self._log_epics_msg_info(merged_msg, merged_stat, motor_msg)
        return merged_stat, merged_msg

    def _get_alarm_status_and_msg(self, maxage=0):
        def _get_value_status():
            return self._epics.get_channel_alarm("value")

        motor_stat, motor_msg = get_from_cache_or(
            self, "value_status", _get_value_status, maxage=maxage
        )
        motor_msg = (motor_msg or "").strip()

        if self.has_msgtxt:
            motor_stat, motor_msg = self._update_status_with_msgtxt(
                motor_stat, motor_msg, maxage
            )
        elif motor_stat == status.OK:
            motor_msg = ""
        return motor_stat, motor_msg

    def _log_epics_msg_info(self, error_msg, stat, epics_msg):
        if stat == status.OK or stat == status.UNKNOWN:
            return
        if stat == status.WARN:
            self.log.warning("%s (%s)", error_msg, epics_msg)
        elif stat == status.ERROR:
            self.log.error("%s (%s)", error_msg, epics_msg)

    def _get_dir_sign(self):
        return (
            1 if self._epics.get_channel_value("dir", as_string=True) == "Pos" else -1
        )

    def _limit_margin(self, boundary_value):
        return abs(boundary_value) * self.limit_rel_tolerance

    def _user_limits_fit_dial_window(
        self, hw_user_min, hw_user_max, dial_window_min, dial_window_max, offset
    ):
        dir_sign = self._get_dir_sign()
        dial_from_user_low = self._user_to_dial(hw_user_min, offset)
        dial_from_user_high = self._user_to_dial(hw_user_max, offset)
        if dir_sign > 0:
            dial_min = dial_from_user_low
            dial_max = dial_from_user_high
        else:
            dial_min = dial_from_user_high
            dial_max = dial_from_user_low
        min_margin = self._limit_margin(dial_window_min)
        max_margin = self._limit_margin(dial_window_max)
        return (
            dial_window_min - min_margin <= dial_min
            and dial_max <= dial_window_max + max_margin
        )

    def _user_to_dial(self, val, offset=None):
        """
        Convert a user-coordinate value to dial (hardware) units.

        user = dial * DIR + OFF; dial = (user - OFF) / DIR
        """
        if offset is None:
            offset = self.offset
        return (val - offset) / self._get_dir_sign()

    def _checkLimits(self, limits):
        """
        Validate that requested *user* limits lie inside the *dial* abs-limits.

        NICOS base version adds the offset; for EPICS we have to subtract it.
        """
        umin, umax = limits
        dial_window_min, dial_window_max = self.abslimits

        if umin > umax:
            raise ConfigurationError(
                self,
                f"user minimum ({umin}) above user maximum ({umax})",
            )

        dir_sign = self._get_dir_sign()
        dial_from_user_low = self._user_to_dial(umin)
        dial_from_user_high = self._user_to_dial(umax)
        if dir_sign > 0:
            umin_hw = dial_from_user_low
            umax_hw = dial_from_user_high
        else:
            umin_hw = dial_from_user_high
            umax_hw = dial_from_user_low

        min_margin = self._limit_margin(dial_window_min)
        max_margin = self._limit_margin(dial_window_max)

        if umin_hw < dial_window_min - min_margin:
            raise ConfigurationError(
                self,
                f"user minimum ({umin}, dial {umin_hw} with offset "
                f"{self.offset}) below absolute minimum ({dial_window_min})",
            )
        if umax_hw > dial_window_max + max_margin:
            raise ConfigurationError(
                self,
                f"user maximum ({umax}, dial {umax_hw} with offset "
                f"{self.offset}) above absolute maximum ({dial_window_max})",
            )

    def _check_in_range(self, curval, userlimits):
        if userlimits == (0, 0) and self.abslimits == (0, 0):
            # No limits defined, so must be in range
            return status.OK, ""

        return HasLimits._check_in_range(self, curval, userlimits)


class EpicsJogMotor(EpicsMotor):
    """
    EPICS motor wrapper that behaves like a speed controller.
    - start(+v): set JVEL=v and jog forward
    - start(-v): set JVEL=|v| and jog reverse
    - start(0): stop and clear jog fields
    Other behaviour (limits, enable, error handling, readbacks) is the same
    as EpicsMotor, but this device never issues .VAL moves.

    Notes on readbacks in this subclass:
    - "jog_velocity" is the raw EPICS .JVEL (usually small and never actually 0).
    - "value" is a synthetic NICOS-side signal: signed speed based on jog_dir,
      and set to 0 when stopping, etc.
    """

    parameters = {
        "jog_dir": Param(
            "Current jogging direction: -1 reverse, 0 stopped/unknown, +1 forward",
            type=int,
            settable=True,
        )
    }

    parameter_overrides = {"speed": Override(userparam=False)}

    def _build_epics_channels(self):
        epics_channels = super()._build_epics_channels()
        epics_channels.update(
            {
                "target": setpoint_channel(
                    ".JVEL",
                    cache_key=None,
                    subscribe=False,
                    connect_on_startup=False,
                ),
                "jog_velocity": readback_channel(".JVEL", cache_key="jog_velocity"),
                "value": status_channel(".JVEL", cache_key="value"),
                "jogforward": readback_channel(".JOGF"),
                "jogreverse": readback_channel(".JOGR"),
            }
        )
        return epics_channels

    def doReadSpeed(self):
        return self._epics.get_channel_value("jog_velocity")

    def _read_jog_with_sign(self, maxage=0):
        jvel = abs(self._read_channel_cached("jog_velocity", maxage=maxage))
        if self.jog_dir < 0:
            return -jvel
        if self.jog_dir > 0:
            return jvel
        return 0.0

    def doRead(self, maxage=0):
        return self._read_jog_with_sign(maxage)

    def doReadTarget(self):
        return self._read_jog_with_sign()

    def doReadAbslimits(self):
        max_speed = self._epics.get_channel_value("maxspeed")
        return -max_speed, max_speed

    def doWriteUserlimits(self, value):
        self.log.warning(
            "Userlimits changes on jog motors are not supported yet and will "
            "be ignored."
        )
        return self.userlimits

    def doReadUserlimits(self):
        max_speed = self._epics.get_channel_value("maxspeed")
        return -max_speed, max_speed

    def doWriteSpeed(self, value):
        self.log.warning(
            "Speed parameter is not used for changing speed, use target value instead."
        )
        return self.speed

    def _get_valid_speed(self, value):
        max_speed = self._read_channel_cached("maxspeed")
        min_speed = self._read_channel_cached("minspeed")

        # Cannot be less than min speed
        valid_speed = max(min_speed, value)

        # In EPICS if max speed is 0 then there is no limit
        if max_speed > 0.0:
            valid_speed = min(max_speed, valid_speed)

        if valid_speed > abs(value):
            self.log.warning(
                f"Selected jog speed {abs(value)} is below hardware minimum, "
                f"using {valid_speed} {self.unit} instead.",
            )

        return valid_speed

    def doStart(self, value):
        if value == 0:
            self.jog_dir = 0
            self.stop()
            return

        jog_speed = self._get_valid_speed(abs(value))

        # JVEL updates may arrive before the direction callbacks.
        self.stop()
        self._epics.wait_for("donemoving", 1)

        self.jog_dir = 1 if value > 0 else -1
        self._epics.put_channel_value("jog_velocity", jog_speed)

        jf = self._read_channel_cached("jogforward")
        jr = self._read_channel_cached("jogreverse")
        if not (jf or jr):
            self._epics.put_channel_value(
                "jogforward" if value > 0 else "jogreverse", 1
            )
        elif value > 0 and jr:
            self._epics.put_channel_value("jogreverse", 0)
            self._epics.wait_for("donemoving", 1)
            self._epics.put_channel_value("jogforward", 1)
        elif value < 0 and jf:
            self._epics.put_channel_value("jogforward", 0)
            self._epics.wait_for("donemoving", 1)
            self._epics.put_channel_value("jogreverse", 1)

    def doStop(self):
        self.jog_dir = 0
        self._epics.put_channel_value("jogforward", 0)
        self._epics.put_channel_value("jogreverse", 0)
        self._epics.put_channel_value("stop", 1)
        self._publish_jog_value(0.0, time.time())

    def doIsCompleted(self):
        if self._sim_intercept:
            return True
        moving = self._read_channel_cached("moving")
        return moving == 0

    def _compute_status_from_pvs(self, maxage):
        with self._lock:
            epics_status, message = self._get_alarm_status_and_msg(maxage)
            self._motor_status = epics_status, message
        if epics_status in (status.ERROR, status.UNKNOWN):
            return epics_status, message or "Unknown problem in record"
        elif epics_status == status.WARN:
            return status.WARN, message

        done_moving = self._read_channel_cached("donemoving", maxage=maxage)
        moving = self._read_channel_cached("moving", maxage=maxage)
        if done_moving == 0 or moving != 0:
            return status.BUSY, message or "moving"

        if self.has_powerauto:
            powerauto_enabled = self._read_channel_cached("powerauto", maxage=maxage)
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._read_channel_cached(
            "enable", maxage=maxage
        ):
            return status.WARN, "motor is not enabled"

        high_limitswitch = self._read_channel_cached("highlimitswitch", maxage=maxage)
        if high_limitswitch != 0:
            return status.WARN, message or "at high limit switch."

        low_limitswitch = self._read_channel_cached("lowlimitswitch", maxage=maxage)
        if low_limitswitch != 0:
            return status.WARN, message or "at low limit switch."
        limit_violation = self._read_channel_cached("softlimit", maxage=maxage)
        if limit_violation != 0:
            return status.WARN, message or "soft limit violation."

        return status.OK, message

    def doReadUnit(self):
        raw_unit = self._epics.get_channel_units("value")
        return f"{raw_unit}/s" if raw_unit else "units/s"

    def _on_channel_update(self, update):
        ts = time.time()

        if update.channel == "jog_velocity":
            self._cache.put(self._name, "jog_velocity", update.value, ts)
            self._publish_jog_value(update.value, ts)
            return

        # Update the signed "value" when direction or moving state changes.
        if update.channel in ("jogforward", "jogreverse"):
            cur_jvel = abs(self._read_channel_cached("jog_velocity"))
            other = "jogreverse" if update.channel == "jogforward" else "jogforward"
            sign = 1 if update.channel == "jogforward" else -1
            if update.value == 1:
                self._cache.put(self._name, "jog_dir", sign, ts)
                self._publish_jog_value(cur_jvel, ts)
            elif not self._read_channel_cached(other):
                self._cache.put(self._name, "jog_dir", 0, ts)
                self._publish_jog_value(cur_jvel, ts)
            self._cache.put(self._name, update.channel, update.value, ts)
            return

        if update.channel == "value":
            self._cache.put(
                self._name, "value_status", (update.severity, update.message), ts
            )
            self._refresh_status(ts)
            return

        super()._on_channel_update(update)

    def _publish_jog_value(self, raw_velocity, timestamp):
        if self.jog_dir < 0:
            value = -abs(raw_velocity)
        elif self.jog_dir > 0:
            value = abs(raw_velocity)
        else:
            value = 0.0
        self._cache.put(self._name, "value", value, timestamp)
        self._cache.put(self._name, "target", value, timestamp)


class SmaractPiezoMotor(EpicsMotor):
    """
    This device is a subclass of EpicsMotor that is used for the piezo motors
    from Smaract.
    """

    parameters = {
        "stepfrequency": Param(
            "Step frequency of the piezo motor.",
            type=float,
            settable=True,
            volatile=True,
            userparam=True,
        ),
        "stepsizeforward": Param(
            "Step size forward of the piezo motor.",
            type=float,
            settable=True,
            volatile=True,
            userparam=True,
        ),
        "stepsizereverse": Param(
            "Step size reverse of the piezo motor.",
            type=float,
            settable=True,
            volatile=True,
            userparam=True,
        ),
        "mclfrequency": Param(
            "MCL frequency of the piezo motor.",
            type=int,
            settable=True,
            volatile=True,
            userparam=True,
        ),
    }

    parameter_overrides = {
        "has_errorbit": Override(default=False),
        "has_reseterror": Override(default=False),
        "has_powerauto": Override(default=False),
    }

    def _build_epics_channels(self):
        epics_channels = super()._build_epics_channels()
        epics_channels.update(
            {
                # Smaract: CNEN changes do not trigger a status recompute.
                "enable": readback_channel(".CNEN"),
                "stepfrequency": readback_channel("StepFreq"),
                "stepsizeforward": readback_channel("StepSizeFwd"),
                "stepsizereverse": readback_channel("StepSizeRev"),
                "mclfrequency": readback_channel("MaxCtrlLFreq"),
                "mclfrequency_rb": readback_channel("MaxCtrlLFreq"),
            }
        )
        # The Smaract IOC provides -MsgTxt but no -MsgTxt.SEVR record.
        epics_channels.pop("msgtxt_severity", None)
        return epics_channels

    def doReadStepfrequency(self):
        return self._epics.get_channel_value("stepfrequency")

    def doWriteStepfrequency(self, value):
        if value < 0:
            raise ValueError("Step frequency must be non-negative.")
        self._epics.put_channel_value("stepfrequency", value)

    def doReadStepsizeforward(self):
        return self._epics.get_channel_value("stepsizeforward")

    def doWriteStepsizeforward(self, value):
        if value < 0:
            raise ValueError("Step size forward must be non-negative.")
        self._epics.put_channel_value("stepsizeforward", value)

    def doReadStepsizereverse(self):
        return self._epics.get_channel_value("stepsizereverse")

    def doWriteStepsizereverse(self, value):
        if value < 0:
            raise ValueError("Step size reverse must be non-negative.")
        self._epics.put_channel_value("stepsizereverse", value)

    def doReadMclfrequency(self):
        return self._epics.get_channel_value("mclfrequency_rb")

    def doWriteMclfrequency(self, value):
        if value < 0:
            raise ValueError("MCL frequency must be non-negative.")
        self._epics.put_channel_value("mclfrequency", value)

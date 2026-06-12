import math
import threading
import time

from nicos.core import (
    Moveable,
    Override,
    Param,
    limits,
    oneof,
    pvname,
    status,
)
from nicos.core.errors import ConfigurationError, MoveError
from nicos.core.mixins import CanDisable, HasLimits, HasOffset
from nicos.devices.abstract import CanReference, Motor
from nicos.devices.epics.status import SEVERITY_TO_STATUS
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    RecordInfo,
    RecordType,
    get_from_cache_or,
)


class EpicsMotor(EpicsDeviceBase, CanDisable, CanReference, HasOffset, Motor):
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
    """

    valuetype = float
    limit_rel_tolerance = 1e-12
    errorstates = {**Motor.errorstates, status.UNKNOWN: MoveError}
    _startup_moveable_limits_pending = False

    _primary_field = "value"
    _default_root_attr = "motorpv"

    def _pvs_to_connect(self):
        return [self.motorpv]

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

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._motor_status = (status.OK, "")
        EpicsDeviceBase.doPreinit(self, mode)

    def _build_record_fields(self):
        record_fields = {
            "value": RecordInfo("value", ".RBV", RecordType.BOTH),
            "dialvalue": RecordInfo("", ".DRBV", RecordType.VALUE),
            "target": RecordInfo("target", ".VAL", RecordType.VALUE),
            "stop": RecordInfo("", ".STOP", RecordType.VALUE),
            "speed": RecordInfo("", ".VELO", RecordType.VALUE),
            "offset": RecordInfo("", ".OFF", RecordType.VALUE),
            "highlimit": RecordInfo("", ".HLM", RecordType.VALUE),
            "lowlimit": RecordInfo("", ".LLM", RecordType.VALUE),
            "dialhighlimit": RecordInfo("", ".DHLM", RecordType.VALUE),
            "diallowlimit": RecordInfo("", ".DLLM", RecordType.VALUE),
            "enable": RecordInfo("", ".CNEN", RecordType.BOTH),
            "set": RecordInfo("", ".SET", RecordType.VALUE),
            "foff": RecordInfo("", ".FOFF", RecordType.VALUE),
            "dir": RecordInfo("", ".DIR", RecordType.VALUE),
            "homeforward": RecordInfo("", ".HOMF", RecordType.VALUE),
            "homereverse": RecordInfo("", ".HOMR", RecordType.VALUE),
            "position_deadband": RecordInfo("", ".RDBD", RecordType.VALUE),
            "description": RecordInfo("", ".DESC", RecordType.VALUE),
            "monitor_deadband": RecordInfo("", ".MDEL", RecordType.VALUE),
            "maxspeed": RecordInfo("", ".VMAX", RecordType.VALUE),
            "minspeed": RecordInfo("", ".VBAS", RecordType.VALUE),
            "donemoving": RecordInfo("", ".DMOV", RecordType.STATUS),
            "moving": RecordInfo("", ".MOVN", RecordType.STATUS),
            "miss": RecordInfo("", ".MISS", RecordType.STATUS),
            "alarm_status": RecordInfo("", ".STAT", RecordType.STATUS),
            "alarm_severity": RecordInfo("", ".SEVR", RecordType.STATUS),
            "softlimit": RecordInfo("", ".LVIO", RecordType.STATUS),
            "lowlimitswitch": RecordInfo("", ".LLS", RecordType.STATUS),
            "highlimitswitch": RecordInfo("", ".HLS", RecordType.STATUS),
            "errorbit": RecordInfo("", "-Err", RecordType.STATUS),
            "reseterror": RecordInfo("", "-ErrRst", RecordType.STATUS),
            "powerauto": RecordInfo("", "-PwrAuto", RecordType.STATUS),
            "msgtxt": RecordInfo("", "-MsgTxt", RecordType.STATUS),
            "msgtxt_severity": RecordInfo("", "-MsgTxt.SEVR", RecordType.STATUS),
        }

        if not self.has_errorbit:
            del record_fields["errorbit"]
        if not self.has_reseterror:
            del record_fields["reseterror"]
        if not self.has_powerauto:
            del record_fields["powerauto"]
        if not self.has_msgtxt:
            del record_fields["msgtxt"]
            del record_fields["msgtxt_severity"]
        return record_fields

    def _after_subscribe(self, mode):
        self._startup_moveable_limits_pending = (
            self._uses_moveable_startup_limit_compat()
        )

    def doRead(self, maxage=0):
        return self._read_cached("value", maxage=maxage)

    def doReadSpeed(self):
        return self._epics.get_pv("speed")

    def doReadOffset(self):
        return self._epics.get_pv("offset")

    def doReadTarget(self):
        return self._read_cached("target")

    def doReadAbslimits(self):
        dial_min = self._epics.get_pv("diallowlimit")
        dial_max = self._epics.get_pv("dialhighlimit")
        return dial_min, dial_max

    def doReadHwuserlimits(self):
        dial_min = self._epics.get_pv("diallowlimit")
        dial_max = self._epics.get_pv("dialhighlimit")
        if dial_min > dial_max:
            raise ConfigurationError(
                self,
                f"dial lowlimit ({dial_min}) above dial highlimit ({dial_max})",
            )
        offset = self.offset
        hw_user_min = self._epics.get_pv("lowlimit")
        hw_user_max = self._epics.get_pv("highlimit")
        if hw_user_min > hw_user_max:
            raise ConfigurationError(
                self,
                f"hardware user lowlimit ({hw_user_min}) above hardware user "
                f"highlimit ({hw_user_max})",
            )
        if not self._user_limits_fit_dial_window(
            hw_user_min, hw_user_max, dial_min, dial_max, offset
        ):
            direction = self._epics.get_pv("dir", as_string=True)
            raise ConfigurationError(
                self,
                f"hardware userlimits ({hw_user_min}, {hw_user_max}) are "
                f"inconsistent with dial limits ({dial_min}, {dial_max}), "
                f"offset ({offset}) and direction ({direction})",
            )
        return hw_user_min, hw_user_max

    def doReadUserlimits(self):
        # Moveable.init() compares userlimits against (abslimits - offset) using
        # the NICOS HasOffset convention. EPICS uses the opposite sign
        # convention, so expose the same boundary-form limits once during init
        # and switch back to the regular EPICS user coordinates afterwards.
        if self._startup_moveable_limits_pending:
            # Validate that EPICS record limits are internally consistent even
            # when we return the NICOS-compatible startup boundary values.
            self.doReadHwuserlimits()
            self._startup_moveable_limits_pending = False
            dial_min, dial_max = self.abslimits
            offset = self.offset
            return dial_min - offset, dial_max - offset

        hw_umin, hw_umax = self.hwuserlimits
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
        return self._epics.get_pv("position_deadband")

    def doReadPv_Desc(self):
        return self._epics.get_pv("description")

    def doReadMonitor_Deadband(self):
        return self._epics.get_pv("monitor_deadband")

    def doReadPrecision(self):
        return self._epics.get_pv("position_deadband")

    def doIsAtTarget(self, pos=None, target=None):
        return self._read_cached("miss") == 0

    def doIsCompleted(self):
        if self._sim_intercept:
            return True

        cur_status, cur_message = self.status(0)
        if cur_status in self.busystates:
            return False
        if cur_status in self.errorstates:
            raise self.errorstates[cur_status](self, cur_message)

        moving = self._read_cached("moving")
        pos = self._read_cached("value")
        target = self._read_cached("target")
        deadband = self._read_cached("position_deadband")

        # check whether target has been reached within deadband:
        if not math.isclose(target, pos, abs_tol=deadband):
            return False
        return moving == 0

    def doStart(self, value):
        if abs(self.read(0) - value) <= self.precision:
            return

        self._cache_status_if_higher((status.BUSY, "Moving abs"))
        self._epics.put_pv("target", value)

    def doWriteSpeed(self, value):
        speed = self._get_valid_speed(value)

        if speed != value:
            self.log.warning(
                "Selected speed %s is outside the parameter limits, using %s instead.",
                value,
                speed,
            )

        self._epics.put_pv("speed", speed)
        return speed

    def doWriteMonitor_Deadband(self, value):
        deadband = value
        self._epics.put_pv("monitor_deadband", max(deadband, 0))

    def doWriteOffset(self, new_off):
        """Shift the user ↔ dial offset via SET/FOFF; limits follow automatically."""
        if self.offset == new_off:
            return

        if self._epics.get_pv("moving") or not self._epics.get_pv("donemoving"):
            raise RuntimeError(f"{self}: cannot change OFF while motor is moving")

        dir_sign = 1 if self._epics.get_pv("dir", as_string=True) == "Pos" else -1
        dial_now = self._epics.get_pv("dialvalue")
        user_target = dial_now * dir_sign + new_off  # user = dial * DIR + OFF

        # In SET mode with FOFF=0, writing VAL makes the record recalculate OFF.
        self._epics.put_pv("set", 1)
        self._epics.put_pv("foff", 0)
        self._epics.put_pv("target", user_target)
        self._epics.put_pv("set", 0)
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
        self._epics.put_pv("stop", 1)

    def doReset(self):
        if self.has_errorbit and self.has_reseterror:
            error_bit = self._read_cached("errorbit")
            if error_bit == 0:
                self.log.warning("Error bit is not set, can not reset error state.")
            else:
                self._epics.put_pv("reseterror", 1)

    def doReference(self):
        self._epics.put_pv(f"home{self.reference_direction}", 1)

    def doEnable(self, on):
        self._epics.put_pv("enable", 1 if on else 0)

    def doSetPosition(self, pos):
        self._epics.put_pv("set", 1)
        self._epics.put_pv("foff", 1)
        self._epics.put_pv("target", pos)
        self._epics.put_pv("set", 0)
        self._epics.put_pv("foff", 0)

    def isAllowed(self, pos):
        if self.userlimits == (0, 0) and self.abslimits == (0, 0):
            # No limits defined
            return True, ""
        return Moveable.isAllowed(self, pos)

    def _compute_status(self, maxage=0):
        try:
            return self._compute_status_from_pvs(maxage)
        except TimeoutError:
            return status.UNKNOWN, "lost connection to EPICS"
        except KeyError as err:
            return status.ERROR, f"error reading motor status: {err}"

    def _compute_status_from_pvs(self, maxage):
        with self._lock:
            epics_status, message = self._get_alarm_status_and_msg(maxage)
            self._motor_status = epics_status, message
        message = (message or "").strip()
        status_candidates = [self._alarm_status_candidate(epics_status, message)]

        done_moving = self._read_cached("donemoving", maxage=maxage)
        moving = self._read_cached("moving", maxage=maxage)
        if done_moving == 0 or moving != 0:
            homing = self._read_cached(
                "homeforward", maxage=maxage
            ) or self._read_cached("homereverse", maxage=maxage)
            if homing:
                status_candidates.append((status.BUSY, message or "homing"))
            else:
                target = self._read_cached("target", maxage=maxage)
                status_candidates.append(
                    (status.BUSY, message or f"moving to {target}")
                )

        if self.has_powerauto:
            powerauto_enabled = self._read_cached("powerauto", maxage=maxage)
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._read_cached("enable", maxage=maxage):
            status_candidates.append((status.WARN, "motor is not enabled"))

        miss = self._read_cached("miss", maxage=maxage)
        if miss != 0:
            status_candidates.append(
                (status.NOTREACHED, message or "did not reach target position.")
            )

        high_limitswitch = self._read_cached("highlimitswitch", maxage=maxage)
        if high_limitswitch != 0:
            status_candidates.append((status.WARN, message or "at high limit switch."))

        low_limitswitch = self._read_cached("lowlimitswitch", maxage=maxage)
        if low_limitswitch != 0:
            status_candidates.append((status.WARN, message or "at low limit switch."))

        limit_violation = self._read_cached("softlimit", maxage=maxage)
        if limit_violation != 0:
            status_candidates.append((status.WARN, message or "soft limit violation."))
        return self._select_highest_status(status_candidates)

    def _get_valid_speed(self, value):
        max_speed = self._read_cached("maxspeed")
        min_speed = self._read_cached("minspeed")

        # Cannot be less than min speed
        valid_speed = max(min_speed, value)

        # In EPICS if max speed is 0 then there is no limit
        if max_speed > 0.0:
            valid_speed = min(max_speed, valid_speed)

        return valid_speed

    @staticmethod
    def _select_highest_status(status_candidates):
        return max(status_candidates, key=lambda status_candidate: status_candidate[0])

    @staticmethod
    def _alarm_status_candidate(epics_status, message):
        if epics_status in (status.ERROR, status.UNKNOWN):
            return epics_status, message or "Unknown problem in record"
        if epics_status == status.WARN:
            return status.WARN, message
        return status.OK, message

    def _cache_status_if_higher(self, candidate_status):
        if self._cache is None:
            return
        try:
            current_status = self._compute_status()
        except Exception:
            # Keep the current cached state if status cannot be determined
            # reliably at this point.
            return
        if candidate_status[0] > current_status[0]:
            self._cache.put(self._name, "status", candidate_status, time.time())

    def _get_msgtxt(self, maxage=0):
        msg_txt = self._read_cached("msgtxt", as_string=True, maxage=maxage).strip()

        if "msgtxt_severity" in self._record_fields:
            msg_severity = self._read_cached("msgtxt_severity", maxage=maxage)
        else:
            msg_severity = 0
        msg_stat = SEVERITY_TO_STATUS.get(msg_severity, status.UNKNOWN)
        return msg_stat, msg_txt

    def increase_severity_if_msgtxt_severity_higher(self, msg_stat, motor_stat):
        return max(msg_stat, motor_stat)

    def _update_status_with_msgtxt(self, motor_stat, motor_msg, maxage=0):
        motor_msg = (motor_msg or "").strip()
        msg_stat, msg_txt = self._get_msgtxt(maxage)
        merged_stat = self.increase_severity_if_msgtxt_severity_higher(
            msg_stat, motor_stat
        )

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
            return self._epics.get_alarm_status("value")

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
        return 1 if self._epics.get_pv("dir", as_string=True) == "Pos" else -1

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

        user = dial * DIR + OFF      ⇒     dial = (user - OFF) / DIR
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
                f"user minimum ({umin}) below absolute minimum ({dial_window_min})",
            )
        if umax_hw > dial_window_max + max_margin:
            raise ConfigurationError(
                self,
                f"user maximum ({umax}) above absolute maximum ({dial_window_max})",
            )

    def _check_in_range(self, curval, userlimits):
        if userlimits == (0, 0) and self.abslimits == (0, 0):
            # No limits defined, so must be in range
            return status.OK, ""

        return HasLimits._check_in_range(self, curval, userlimits)

    def _uses_moveable_startup_limit_compat(self):
        return (
            "userlimits" not in self._config
            and "limitoffsets" not in self._config
            and self.limitoffsets in ((0.0, 0.0), (0, 0))
        )


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

    def _build_record_fields(self):
        record_fields = super()._build_record_fields()
        record_fields.update(
            {
                "target": RecordInfo("", ".JVEL", RecordType.VALUE),
                "jog_velocity": RecordInfo("jog_velocity", ".JVEL", RecordType.VALUE),
                "value": RecordInfo("value", ".JVEL", RecordType.STATUS),
                "jogforward": RecordInfo("", ".JOGF", RecordType.VALUE),
                "jogreverse": RecordInfo("", ".JOGR", RecordType.VALUE),
            }
        )
        return record_fields

    def doReadSpeed(self):
        return self._epics.get_pv("jog_velocity")

    def _read_jog_with_sign(self, maxage=0):
        jvel = abs(self._read_cached("jog_velocity", maxage=maxage))
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
        max_speed = self._epics.get_pv("maxspeed")
        return -max_speed, max_speed

    def doWriteUserlimits(self, value):
        self.log.warning(
            "Userlimits changes on jog motors are not supported yet and will "
            "be ignored."
        )
        return self.userlimits

    def doReadUserlimits(self):
        max_speed = self._epics.get_pv("maxspeed")
        return -max_speed, max_speed

    def doWriteSpeed(self, value):
        self.log.warning(
            "Speed parameter is not used for changing speed, use target value instead."
        )
        return self.speed

    def _get_valid_speed(self, value):
        max_speed = self._read_cached("maxspeed")
        min_speed = self._read_cached("minspeed")

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
            self._cache.put(self._name, "status", (status.OK, "stopped"), time.time())
            return

        jog_speed = self._get_valid_speed(abs(value))

        self.jog_dir = 1 if value > 0 else -1

        # JVEL updates may arrive before the direction callbacks.
        self.stop()
        self._epics.wait_for("donemoving", 1)

        self._epics.put_pv("jog_velocity", jog_speed)

        jf = self._read_cached("jogforward")
        jr = self._read_cached("jogreverse")
        if not (jf or jr):
            self._epics.put_pv("jogforward" if value > 0 else "jogreverse", 1)
        elif value > 0 and jr:
            self._epics.put_pv("jogreverse", 0)
            self._epics.wait_for("donemoving", 1)
            self._epics.put_pv("jogforward", 1)
        elif value < 0 and jf:
            self._epics.put_pv("jogforward", 0)
            self._epics.wait_for("donemoving", 1)
            self._epics.put_pv("jogreverse", 1)

        self._cache.put(self._name, "status", (status.BUSY, "moving"), time.time())

    def doStop(self):
        self.jog_dir = 0
        self._epics.put_pv("jogforward", 0)
        self._epics.put_pv("jogreverse", 0)
        self._epics.put_pv("stop", 1)
        self._cache.put(self._name, "value", 0.0, time.time())

    def doIsCompleted(self):
        if self._sim_intercept:
            return True
        moving = self._read_cached("moving")
        return moving == 0

    def _compute_status(self, maxage=0):
        with self._lock:
            epics_status, message = self._get_alarm_status_and_msg(maxage)
            self._motor_status = epics_status, message
        if epics_status in (status.ERROR, status.UNKNOWN):
            return epics_status, message or "Unknown problem in record"
        elif epics_status == status.WARN:
            return status.WARN, message

        done_moving = self._read_cached("donemoving", maxage=maxage)
        moving = self._read_cached("moving", maxage=maxage)
        if done_moving == 0 or moving != 0:
            return status.BUSY, message or "moving"

        if self.has_powerauto:
            powerauto_enabled = self._read_cached("powerauto", maxage=maxage)
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._read_cached("enable", maxage=maxage):
            return status.WARN, "motor is not enabled"

        high_limitswitch = self._read_cached("highlimitswitch", maxage=maxage)
        if high_limitswitch != 0:
            return status.WARN, message or "at high limit switch."

        low_limitswitch = self._read_cached("lowlimitswitch", maxage=maxage)
        if low_limitswitch != 0:
            return status.WARN, message or "at low limit switch."
        limit_violation = self._read_cached("softlimit", maxage=maxage)
        if limit_violation != 0:
            return status.WARN, message or "soft limit violation."

        return status.OK, message

    def doReadUnit(self):
        raw_unit = self._epics.get_units("value")
        return f"{raw_unit}/s" if raw_unit else "units/s"

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()

        if param == "jog_velocity":
            self._cache.put(self._name, "jog_velocity", value, ts)
            signed = -abs(value) if self.jog_dir < 0 else abs(value)
            self._cache.put(self._name, "value", signed, ts)
            return

        # Update the signed "value" when direction or moving state changes.
        if param in ("jogforward", "jogreverse"):
            cur_jvel = abs(self._read_cached("jog_velocity"))
            other = "jogreverse" if param == "jogforward" else "jogforward"
            sign = 1 if param == "jogforward" else -1
            if value == 1:
                self._cache.put(self._name, "jog_dir", sign, ts)
                self._cache.put(self._name, "value", sign * cur_jvel, ts)
            elif not self._read_cached(other):
                self._cache.put(self._name, "jog_dir", 0, ts)
                self._cache.put(self._name, "value", 0.0, ts)
            self._cache.put(self._name, param, value, ts)
            return

        if param == "value":
            self._cache.put(self._name, "value_status", (severity, message), ts)
            self._refresh_status(ts)
            return

        super()._value_change_callback(
            name, param, value, units, limits, severity, message, **kwargs
        )


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

    def _build_record_fields(self):
        record_fields = {
            "value": RecordInfo("value", ".RBV", RecordType.BOTH),
            "dialvalue": RecordInfo("", ".DRBV", RecordType.VALUE),
            "target": RecordInfo("target", ".VAL", RecordType.VALUE),
            "stop": RecordInfo("", ".STOP", RecordType.VALUE),
            "speed": RecordInfo("", ".VELO", RecordType.VALUE),
            "offset": RecordInfo("", ".OFF", RecordType.VALUE),
            "highlimit": RecordInfo("", ".HLM", RecordType.VALUE),
            "lowlimit": RecordInfo("", ".LLM", RecordType.VALUE),
            "dialhighlimit": RecordInfo("", ".DHLM", RecordType.VALUE),
            "diallowlimit": RecordInfo("", ".DLLM", RecordType.VALUE),
            "enable": RecordInfo("", ".CNEN", RecordType.VALUE),
            "set": RecordInfo("", ".SET", RecordType.VALUE),
            "foff": RecordInfo("", ".FOFF", RecordType.VALUE),
            "dir": RecordInfo("", ".DIR", RecordType.VALUE),
            "homeforward": RecordInfo("", ".HOMF", RecordType.VALUE),
            "homereverse": RecordInfo("", ".HOMR", RecordType.VALUE),
            "position_deadband": RecordInfo("", ".RDBD", RecordType.VALUE),
            "description": RecordInfo("", ".DESC", RecordType.VALUE),
            "monitor_deadband": RecordInfo("", ".MDEL", RecordType.VALUE),
            "maxspeed": RecordInfo("", ".VMAX", RecordType.VALUE),
            "donemoving": RecordInfo("", ".DMOV", RecordType.STATUS),
            "moving": RecordInfo("", ".MOVN", RecordType.STATUS),
            "miss": RecordInfo("", ".MISS", RecordType.STATUS),
            "alarm_status": RecordInfo("", ".STAT", RecordType.STATUS),
            "alarm_severity": RecordInfo("", ".SEVR", RecordType.STATUS),
            "softlimit": RecordInfo("", ".LVIO", RecordType.STATUS),
            "lowlimitswitch": RecordInfo("", ".LLS", RecordType.STATUS),
            "highlimitswitch": RecordInfo("", ".HLS", RecordType.STATUS),
            "msgtxt": RecordInfo("", "-MsgTxt", RecordType.STATUS),
            "stepfrequency": RecordInfo("", "StepFreq", RecordType.VALUE),
            "stepsizeforward": RecordInfo("", "StepSizeFwd", RecordType.VALUE),
            "stepsizereverse": RecordInfo("", "StepSizeRev", RecordType.VALUE),
            "mclfrequency": RecordInfo("", "MaxCtrlLFreq", RecordType.VALUE),
            "mclfrequency_rb": RecordInfo("", "MaxCtrlLFreq", RecordType.VALUE),
        }

        if not self.has_msgtxt:
            del record_fields["msgtxt"]
        return record_fields

    def doReadStepfrequency(self):
        return self._epics.get_pv("stepfrequency")

    def doWriteStepfrequency(self, value):
        if value < 0:
            raise ValueError("Step frequency must be non-negative.")
        self._epics.put_pv("stepfrequency", value)

    def doReadStepsizeforward(self):
        return self._epics.get_pv("stepsizeforward")

    def doWriteStepsizeforward(self, value):
        if value < 0:
            raise ValueError("Step size forward must be non-negative.")
        self._epics.put_pv("stepsizeforward", value)

    def doReadStepsizereverse(self):
        return self._epics.get_pv("stepsizereverse")

    def doWriteStepsizereverse(self, value):
        if value < 0:
            raise ValueError("Step size reverse must be non-negative.")
        self._epics.put_pv("stepsizereverse", value)

    def doReadMclfrequency(self):
        return self._epics.get_pv("mclfrequency_rb")

    def doWriteMclfrequency(self, value):
        if value < 0:
            raise ValueError("MCL frequency must be non-negative.")
        self._epics.put_pv("mclfrequency", value)

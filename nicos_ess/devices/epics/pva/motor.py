import copy
import threading
import time

from nicos import session
from nicos.core import POLLER, Moveable, Override, Param, oneof, pvname, status
from nicos.core.errors import ConfigurationError
from nicos.core.mixins import CanDisable, HasLimits, HasOffset
from nicos.devices.abstract import CanReference, Motor
from nicos.devices.epics.status import SEVERITY_TO_STATUS
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class EpicsMotor(EpicsParameters, CanDisable, CanReference, HasOffset, Motor):
    """
    This device exposes some of the functionality provided by the EPICS motor
    record. The PV names for the fields of the record (readback, speed, etc.)
    are derived by combining the motorpv-parameter with the predefined field
    names.

    The has_errorbit and has_reseterror can be provided optionally in case the
    controller supports reporting errors and a reset-mechanism that tries to
    recover from certain errors. If present, these are used when calling the
    reset()-method.

    Another optional parameter is the has_errormsg, which contains an error message that
    may originate from the motor controller or the IOC. If it is present,
    doStatus uses it for some of the status messages.
    """

    valuetype = float

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
        "has_errormsg": Param(
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
        self._epics_subscriptions = []
        self._motor_status = (status.OK, "")
        self._record_fields = {
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
            "unit": RecordInfo("unit", ".EGU", RecordType.VALUE),
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
            "errorbit": RecordInfo("", "-Err", RecordType.STATUS),
            "reseterror": RecordInfo("", "-ErrRst", RecordType.STATUS),
            "powerauto": RecordInfo("", "-PwrAuto", RecordType.STATUS),
            "errormsg": RecordInfo("", "-MsgTxt", RecordType.STATUS),
            "errormsg_severity": RecordInfo("", "-MsgTxt.SEVR", RecordType.STATUS),
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check PV exists
        self._epics_wrapper.connect_pv(self.motorpv)

        if not self.has_errorbit:
            del self._record_fields["errorbit"]
        if not self.has_reseterror:
            del self._record_fields["reseterror"]
        if not self.has_powerauto:
            del self._record_fields["powerauto"]
        if not self.has_errormsg:
            del self._record_fields["errormsg"]
            del self._record_fields["errormsg_severity"]

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            for k, v in self._record_fields.items():
                if v.record_type in [RecordType.VALUE, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.motorpv}{v.pv_suffix}",
                            k,
                            self._value_change_callback,
                            self._connection_change_callback,
                        )
                    )
                if v.record_type in [RecordType.STATUS, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.motorpv}{v.pv_suffix}",
                            k,
                            self._status_change_callback,
                            self._connection_change_callback,
                        )
                    )

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("value")

    def doReadUnit(self):
        return self._get_cached_pv_or_ask("unit")

    def doReadSpeed(self):
        return self._get_cached_pv_or_ask("speed")

    def doReadOffset(self):
        return self._get_cached_pv_or_ask("offset")

    def doReadTarget(self):
        return self._get_cached_pv_or_ask("target")

    def doReadAbslimits(self):
        absmin = self._get_cached_pv_or_ask("diallowlimit")
        absmax = self._get_cached_pv_or_ask("dialhighlimit")
        return absmin, absmax

    def doReadUserlimits(self):
        umin = self._get_cached_pv_or_ask("lowlimit")
        umax = self._get_cached_pv_or_ask("highlimit")
        limits = (umin, umax)
        self._checkLimits(limits)
        return umin, umax

    def doReadPosition_Deadband(self):
        return self._get_cached_pv_or_ask("position_deadband")

    def doReadPv_Desc(self):
        return self._get_cached_pv_or_ask("description")

    def doReadMonitor_Deadband(self):
        return self._get_cached_pv_or_ask("monitor_deadband")

    def doReadPrecision(self):
        return self._get_cached_pv_or_ask("position_deadband")

    def doIsAtTarget(self, pos=None, target=None):
        return self._get_cached_pv_or_ask("miss") == 0

    def doIsCompleted(self):
        moving = self._get_cached_pv_or_ask("moving")
        pos = self._get_cached_pv_or_ask("value")
        target = self._get_cached_pv_or_ask("target")
        deadband = self._get_cached_pv_or_ask("position_deadband")

        if abs(target - pos) > deadband:
            return False

        return moving == 0

    def doStart(self, value):
        if abs(self.read(0) - value) <= self.precision:
            return

        self._cache.put(self._name, "status", (status.BUSY, "Moving abs"), time.time())
        self._put_pv("target", value)

    def doWriteSpeed(self, value):
        speed = self._get_valid_speed(value)

        if speed != value:
            self.log.warning(
                "Selected speed %s is outside the parameter limits, using %s instead.",
                value,
                speed,
            )

        self._put_pv("speed", speed)
        return speed

    def doWriteMonitor_Deadband(self, value):
        deadband = value
        self._put_pv("monitor_deadband", max(deadband, 0))

    def doWriteOffset(self, new_off):
        """Shift the user ↔ dial offset via SET/FOFF; limits follow automatically."""
        if self.offset == new_off:
            return

        if self._get_pv("moving") or not self._get_pv("donemoving"):
            raise RuntimeError(f"{self}: cannot change OFF while motor is moving")

        # Calculate the user value that makes OFF = new_off
        dir_sign = 1 if self._get_pv("dir", as_string=True) == "Pos" else -1
        dial_now = self._get_pv("dialvalue")
        user_target = dial_now * dir_sign + new_off  # user = dial·DIR + OFF

        # Enter calibration mode with variable offset
        self._put_pv("set", 1)
        self._put_pv("foff", 0)

        # Write VAL – record calculates OFF and shifts HLM/LLM
        self._put_pv("target", user_target)

        # Leave calibration mode
        self._put_pv("set", 0)

        self._cache.put(self._name, "offset", new_off, time.time())
        self.log.info("Offset changed to %s", new_off)

    def doWriteUserlimits(self, value):
        self._checkLimits(value)
        low, high = value
        self._put_pv("lowlimit", low)
        self._put_pv("highlimit", high)

    def doAdjust(self, oldvalue, newvalue):
        # For EPICS the offset sign convention differs to that of the base
        # implementation.
        diff = oldvalue - newvalue
        self.offset -= diff

    def doStop(self):
        self._put_pv("stop", 1)

    def doReset(self):
        if self.has_errorbit and self.has_reseterror:
            error_bit = self._get_cached_pv_or_ask("errorbit")
            if error_bit == 0:
                self.log.warning("Error bit is not set, can not reset error state.")
            else:
                self._put_pv("reseterror", 1)

    def doReference(self):
        self._put_pv("home%s" % self.reference_direction, 1)

    def doEnable(self, on):
        self._put_pv("enable", 1 if on else 0)

    def doSetPosition(self, pos):
        self._put_pv("set", 1)
        self._put_pv("foff", 1)
        self._put_pv("target", pos)
        self._put_pv("set", 0)
        self._put_pv("foff", 0)

    def isAllowed(self, pos):
        if self.userlimits == (0, 0) and self.abslimits == (0, 0):
            # No limits defined
            return True, ""
        return Moveable.isAllowed(self, pos)

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        with self._lock:
            epics_status, message = self._get_alarm_status_and_msg()
            self._motor_status = epics_status, message
        if epics_status == status.ERROR:
            return status.ERROR, message or "Unknown problem in record"
        elif epics_status == status.WARN:
            return status.WARN, message

        done_moving = self._get_cached_pv_or_ask("donemoving")
        moving = self._get_cached_pv_or_ask("moving")
        if done_moving == 0 or moving != 0:
            if self._get_cached_pv_or_ask("homeforward") or self._get_cached_pv_or_ask(
                "homereverse"
            ):
                return status.BUSY, message or "homing"
            return status.BUSY, message or f"moving to {self.target}"

        if self.has_powerauto:
            powerauto_enabled = self._get_cached_pv_or_ask("powerauto")
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._get_cached_pv_or_ask("enable"):
            return status.WARN, "motor is not enabled"

        miss = self._get_cached_pv_or_ask("miss")
        if miss != 0:
            return (status.NOTREACHED, message or "did not reach target position.")

        high_limitswitch = self._get_cached_pv_or_ask("highlimitswitch")
        if high_limitswitch != 0:
            return status.WARN, message or "at high limit switch."

        low_limitswitch = self._get_cached_pv_or_ask("lowlimitswitch")
        if low_limitswitch != 0:
            return status.WARN, message or "at low limit switch."

        limit_violation = self._get_cached_pv_or_ask("softlimit")
        if limit_violation != 0:
            return status.WARN, message or "soft limit violation."

        return status.OK, message

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = self._record_fields[param].cache_key
        cache_key = param if not cache_key else cache_key
        self._cache.put(self._name, cache_key, value, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = self._record_fields[param].cache_key
        cache_key = param if not cache_key else cache_key

        if param == "value":
            self._cache.put(self._name, "value_status", (severity, message), time_stamp)
        else:
            self._cache.put(self._name, cache_key, value, time_stamp)
        self._cache.put(self._name, "status", self._do_status(), time_stamp)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["value"].cache_key:
            return

        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.ERROR, "communication failure"),
                time.time(),
            )

    def _get_cached_pv_or_ask(self, param, as_string=False):
        """
        Gets the PV value from the cache if possible, else get it from the device.
        """
        return get_from_cache_or(
            self,
            param,
            lambda: self._get_pv(param, as_string),
        )

    def _get_pv(self, param, as_string=False):
        return self._epics_wrapper.get_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", as_string
        )

    def _put_pv(self, param, value):
        self._epics_wrapper.put_pv_value(
            f"{self.motorpv}{self._record_fields[param].pv_suffix}", value
        )

    def _get_valid_speed(self, value):
        max_speed = self._get_cached_pv_or_ask("maxspeed")

        # Cannot be negative
        valid_speed = max(0.0, value)

        # In EPICS if max speed is 0 then there is no limit
        if max_speed > 0.0:
            valid_speed = min(max_speed, valid_speed)

        return valid_speed

    def _get_errormsg(self):
        msg_txt = self._get_cached_pv_or_ask("errormsg", as_string=True)

        msg_stat = SEVERITY_TO_STATUS.get(
            self._get_cached_pv_or_ask("errormsg_severity"), status.UNKNOWN
        )
        return msg_stat, msg_txt

    def increase_severity_if_msgtxt_severity_higher(self, msg_stat, motor_stat):
        return max(msg_stat, motor_stat)

    def _update_status_with_errormsg(self, motor_stat, motor_msg):
        msg_stat, msg_txt = self._get_errormsg()
        if motor_stat == status.UNKNOWN:
            motor_stat = status.ERROR
        motor_stat = self.increase_severity_if_msgtxt_severity_higher(
            msg_stat, motor_stat
        )
        if self._motor_status != (motor_stat, msg_txt):
            self._log_epics_msg_info(msg_txt, motor_stat, motor_msg)
        return motor_stat, msg_txt

    def _get_alarm_status_and_msg(self):
        def _get_value_status():
            pv = f"{self.motorpv}{self._record_fields['value'].pv_suffix}"
            return self._epics_wrapper.get_alarm_status(pv)

        motor_stat, motor_msg = get_from_cache_or(
            self, "value_status", _get_value_status
        )

        if self.has_errormsg:
            motor_stat, motor_msg = self._update_status_with_errormsg(
                motor_stat, motor_msg
            )
        return motor_stat, motor_msg

    def _log_epics_msg_info(self, error_msg, stat, epics_msg):
        if stat == status.OK or stat == status.UNKNOWN:
            return
        if stat == status.WARN:
            self.log.warning("%s (%s)", error_msg, epics_msg)
        elif stat == status.ERROR:
            self.log.error("%s (%s)", error_msg, epics_msg)

    def _user_to_dial(self, val):
        """
        Convert a user-coordinate value to dial (hardware) units.

        user = dial * DIR + OFF      ⇒     dial = (user - OFF) / DIR
        """
        dir_sign = 1 if self._get_pv("dir", as_string=True) == "Pos" else -1
        return (val - self.offset) / dir_sign

    def _checkLimits(self, limits):
        """
        Validate that requested *user* limits lie inside the *dial* abs-limits.

        NICOS base version adds the offset; for EPICS we have to subtract it.
        """
        umin, umax = limits
        amin, amax = self.abslimits  # dial / hardware numbers

        umin_hw = self._user_to_dial(umin)  # convert to dial units
        umax_hw = self._user_to_dial(umax)

        if umin_hw > umax_hw:
            raise ConfigurationError(
                self,
                f"user minimum ({umin}) above user maximum ({umax})",
            )
        if umin_hw < amin - abs(amin * 1e-12):
            raise ConfigurationError(
                self,
                f"user minimum ({umin}) below absolute minimum ({amin})",
            )
        if umax_hw > amax + abs(amax * 1e-12):
            raise ConfigurationError(
                self,
                f"user maximum ({umax}) above absolute maximum ({amax})",
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

    def doPreinit(self, mode):
        super().doPreinit(mode)
        self._record_fields.update(
            {
                "target": RecordInfo(
                    "", ".JVEL", RecordType.VALUE
                ),  # override cache key (unchanged)
                "jog_velocity": RecordInfo("jog_velocity", ".JVEL", RecordType.VALUE),
                "value": RecordInfo(
                    "value", ".JVEL", RecordType.STATUS
                ),  # STATUS-only on purpose
                "jogforward": RecordInfo("", ".JOGF", RecordType.VALUE),
                "jogreverse": RecordInfo("", ".JOGR", RecordType.VALUE),
            }
        )

    def doReadSpeed(self):
        return self._get_cached_pv_or_ask("jog_velocity")

    def _read_jog_with_sign(self):
        jvel = abs(self._get_cached_pv_or_ask("jog_velocity"))
        if self.jog_dir < 0:
            return -jvel
        if self.jog_dir > 0:
            return jvel
        return 0.0

    def doRead(self, maxage=0):
        return self._read_jog_with_sign()

    def doReadTarget(self):
        return self._read_jog_with_sign()

    def doWriteSpeed(self, value):
        speed = self._get_valid_speed(abs(value))
        if speed != abs(value):
            self.log.warning(
                "Selected jog speed %s is outside limits, using %s instead.",
                value,
                speed,
            )
        # Write raw speed to .JVEL via jog_velocity
        self._put_pv("jog_velocity", speed)
        return speed

    def _wait_until(self, pv_name, expected_value, timeout=5.0):
        """Set up a subscription and wait until the PV reaches the expected value."""
        event = threading.Event()

        def callback(name, param, value, units, limits, severity, message, **kwargs):
            if value == expected_value:
                event.set()

        sub = self._epics_wrapper.subscribe(
            f"{self.motorpv}{self._record_fields[pv_name].pv_suffix}",
            pv_name,
            callback,
        )
        try:
            # already done? exit immediately
            current_value = self._get_cached_pv_or_ask(pv_name)
            if current_value == expected_value:
                return
            # wait for callback to signal completion
            if not event.wait(timeout):
                raise TimeoutError(
                    f"Timeout waiting for {pv_name} to become {expected_value}"
                )
        finally:
            self._epics_wrapper.close_subscription(sub)

    def doStart(self, value):
        if value == 0:
            self.jog_dir = 0
            self.stop()
            self._cache.put(self._name, "status", (status.OK, "stopped"), time.time())
            return

        jog_speed = self._get_valid_speed(abs(value))
        self.jog_dir = 1 if value > 0 else -1  # <-- set before writing JVEL

        # remove this later when EPICS motor record supports speed changes on the fly
        # stop any existing motion first
        self.stop()
        self._wait_until("donemoving", 1)

        # write .JVEL (raw jog_velocity); callbacks will synthesize "value"
        self._put_pv("jog_velocity", jog_speed)

        jf = self._get_cached_pv_or_ask("jogforward")
        jr = self._get_cached_pv_or_ask("jogreverse")
        if not (jf or jr):
            self._put_pv("jogforward" if value > 0 else "jogreverse", 1)
        elif value > 0 and jr:
            self._put_pv("jogreverse", 0)
            self._wait_until("donemoving", 1)
            self._put_pv("jogforward", 1)
        elif value < 0 and jf:
            self._put_pv("jogforward", 0)
            self._wait_until("donemoving", 1)
            self._put_pv("jogreverse", 1)

        self._cache.put(self._name, "status", (status.BUSY, "moving"), time.time())

    def doStop(self):
        self.jog_dir = 0
        self._put_pv("jogforward", 0)
        self._put_pv("jogreverse", 0)
        self._put_pv("stop", 1)
        self._cache.put(self._name, "value", 0.0, time.time())

    def doIsCompleted(self):
        moving = self._get_cached_pv_or_ask("moving")
        return moving == 0

    def _do_status(self):
        with self._lock:
            epics_status, message = self._get_alarm_status()
            self._motor_status = epics_status, message
        if epics_status == status.ERROR:
            return status.ERROR, message or "Unknown problem in record"
        elif epics_status == status.WARN:
            return status.WARN, message

        done_moving = self._get_cached_pv_or_ask("donemoving")
        moving = self._get_cached_pv_or_ask("moving")
        if done_moving == 0 or moving != 0:
            return status.BUSY, message or "moving"

        if self.has_powerauto:
            powerauto_enabled = self._get_cached_pv_or_ask("powerauto")
        else:
            powerauto_enabled = 0

        if not powerauto_enabled and not self._get_cached_pv_or_ask("enable"):
            return status.WARN, "motor is not enabled"

        high_limitswitch = self._get_cached_pv_or_ask("highlimitswitch")
        if high_limitswitch != 0:
            return status.WARN, message or "at high limit switch."

        low_limitswitch = self._get_cached_pv_or_ask("lowlimitswitch")
        if low_limitswitch != 0:
            return status.WARN, message or "at low limit switch."

        limit_violation = self._get_cached_pv_or_ask("softlimit")
        if limit_violation != 0:
            return status.WARN, message or "soft limit violation."

        return status.OK, message

    def doReadUnit(self):
        raw_unit = self._get_pv("unit", as_string=True)
        unit = f"{raw_unit}/s" if raw_unit else "units/s"
        return unit

    def _value_change_callback(self, name, param, value, *args, **kwargs):
        time_stamp = time.time()
        cache_key = self._record_fields[param].cache_key or param

        if param == "jog_velocity":
            self._cache.put(self._name, "jog_velocity", value, time_stamp)
            signed = -abs(value) if self.jog_dir < 0 else abs(value)
            self._cache.put(self._name, "value", signed, time_stamp)
            return

        # Update the signed "value" when direction or moving state changes
        cur_jvel = abs(self._get_cached_pv_or_ask("jog_velocity"))
        if param == "jogforward":
            if value == 1:
                self._cache.put(self._name, "jog_dir", 1, time_stamp)
                self._cache.put(self._name, "value", cur_jvel, time_stamp)
            else:
                # check if we are still jogging in reverse
                jog_rev = self._get_cached_pv_or_ask("jogreverse")
                if not jog_rev:
                    self._cache.put(self._name, "jog_dir", 0, time_stamp)
                    self._cache.put(self._name, "value", 0.0, time_stamp)
        elif param == "jogreverse":
            if value == 1:
                self._cache.put(self._name, "jog_dir", -1, time_stamp)
                self._cache.put(self._name, "value", -cur_jvel, time_stamp)
            else:
                # check if we are still jogging forward
                jog_fwd = self._get_cached_pv_or_ask("jogforward")
                if not jog_fwd:
                    self._cache.put(self._name, "jog_dir", 0, time_stamp)
                    self._cache.put(self._name, "value", 0.0, time_stamp)

        self._cache.put(self._name, cache_key, value, time_stamp)


class SmaractPiezoMotor(EpicsMotor):
    """
    This device is a subclass of EpicsMotor that is used for the piezo motors
    from Smaract.
    """

    parameters = {
        "openloop": Param(
            "Open-loop control mode of the piezo motor.",
            type=bool,
            settable=True,
            volatile=True,
            userparam=True,
        ),
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

    def doPreinit(self, mode):
        self._lock = threading.Lock()
        self._epics_subscriptions = []
        self._motor_status = (status.OK, "")
        self._record_fields = {
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
            "unit": RecordInfo("unit", ".EGU", RecordType.VALUE),
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
            "errorbit": RecordInfo("", "-Err", RecordType.STATUS),
            "reseterror": RecordInfo("", "-ErrRst", RecordType.STATUS),
            "powerauto": RecordInfo("", "-PwrAuto", RecordType.STATUS),
            "errormsg": RecordInfo("", "-MsgTxt", RecordType.STATUS),
            "openloop": RecordInfo("", ".URIP", RecordType.VALUE),
            "openloop_rb": RecordInfo("", "-openLoop", RecordType.VALUE),
            "stepfrequency": RecordInfo("", "-STEPFREQ", RecordType.VALUE),
            "stepsizeforward": RecordInfo("", "-STEPSIZEF", RecordType.VALUE),
            "stepsizereverse": RecordInfo("", "-STEPSIZER", RecordType.VALUE),
            "mclfrequency": RecordInfo("", "-setMclFreq", RecordType.VALUE),
            "mclfrequency_rb": RecordInfo("", "-Freq-MCL-RB", RecordType.VALUE),
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check PV exists
        self._epics_wrapper.connect_pv(self.motorpv)

        if not self.has_errorbit:
            del self._record_fields["errorbit"]
        if not self.has_reseterror:
            del self._record_fields["reseterror"]
        if not self.has_powerauto:
            del self._record_fields["powerauto"]
        if not self.has_errormsg:
            del self._record_fields["errormsg"]

    def doReadOpenloop(self):
        return bool(self._get_cached_pv_or_ask("openloop_rb"))

    def doWriteOpenloop(self, value):
        self._put_pv("openloop", int(value))

    def doReadStepfrequency(self):
        return self._get_cached_pv_or_ask("stepfrequency")

    def doWriteStepfrequency(self, value):
        if value < 0:
            raise ValueError("Step frequency must be non-negative.")
        self._put_pv("stepfrequency", value)

    def doReadStepsizeforward(self):
        return self._get_cached_pv_or_ask("stepsizeforward")

    def doWriteStepsizeforward(self, value):
        if value < 0:
            raise ValueError("Step size forward must be non-negative.")
        self._put_pv("stepsizeforward", value)

    def doReadStepsizereverse(self):
        return self._get_cached_pv_or_ask("stepsizereverse")

    def doWriteStepsizereverse(self, value):
        if value < 0:
            raise ValueError("Step size reverse must be non-negative.")
        self._put_pv("stepsizereverse", value)

    def doReadMclfrequency(self):
        return self._get_cached_pv_or_ask("mclfrequency_rb")

    def doWriteMclfrequency(self, value):
        if value < 0:
            raise ValueError("MCL frequency must be non-negative.")
        self._put_pv("mclfrequency", value)

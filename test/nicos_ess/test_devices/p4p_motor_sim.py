#!/usr/bin/env python3
"""
p4p-based simulated EPICS motor record with correct NTScalar metadata,
no double pvput issues, working MDEL monitor deadband, and a CA-like
"record alias" so you can:

  pvget  SIM:M1        -> reads RBV
  pvput  SIM:M1 10     -> writes VAL
  pvmonitor SIM:M1     -> monitors RBV (MDEL throttled)

Notes about pvlist:
- With PVAccess/p4p, the server advertises channels. Since we export
  all field PVs (SIM:M1.<FIELD>), tools like 'pvlist' will show them.
  That differs from CA record listings and is expected for PVA.

Changes:
- Added a root alias PV (prefix with no '.FIELD') which posts RBV and
  forwards puts to VAL.
- Alias carries the same EGU/PREC and user limit meta as VAL/RBV.
"""

from __future__ import annotations

import argparse
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any

from p4p.nt import NTScalar, NTEnum
from p4p.server import Server
from p4p.server.thread import SharedPV


# ----------------------------
# Helpers and constants
# ----------------------------

@dataclass
class MotorConfig:
    egu: str = "mm"
    prec: int = 3
    user_limits: Tuple[float, float] = (-1e3, 1e3)
    dial_limits: Tuple[float, float] = (-1e3, 1e3)
    velo: float = 5.0
    vbas: float = 0.0
    vmax: float = 0.0
    accl: float = 1.0
    hvel: float = 2.0
    jvel: float = 2.0
    jar:  float = 0.0
    rdbd: float = 0.001
    spdb: float = 0.0
    dly:  float = 0.0
    off:  float = 0.0
    dir_pos: bool = True  # DIR 0=Pos, 1=Neg


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _set_bit(flags: int, bit: int, on: bool) -> int:
    mask = 1 << (bit - 1)
    return (flags | mask) if on else (flags & ~mask)


MSTA_DIRECTION  = 1
MSTA_DONE       = 2
MSTA_PLUS_LS    = 3
MSTA_HOMELS     = 4
MSTA_HOME       = 8
MSTA_MOVING     = 11
MSTA_MINUS_LS   = 14
MSTA_HOMED      = 15


# ----------------------------
# Motion model
# ----------------------------

class MotorState:
    def __init__(self, cfg: MotorConfig):
        self.cfg = cfg
        self.dir_rec = 0 if cfg.dir_pos else 1
        self.off = cfg.off

        self.dial_pos = 0.0
        self.dial_target = 0.0

        self.dmov = 1
        self.movn = 0
        self.hls = 0
        self.lls = 0
        self.lvio = 0
        self.msta = 0

        self._vel_now = 0.0
        self._moving = False
        self._last_ts = time.monotonic()
        self._dmov_ready_ts = 0.0

        self._homing = False
        self._jogging = False
        self._home_pos = 0.0

        self.set_mode = 0
        self.foff = 0
        self.cnen = 1

    def _sign(self) -> float:
        return +1.0 if self.dir_rec == 0 else -1.0

    def user_from_dial(self, d: float) -> float:
        return d * self._sign() + self.off

    def dial_from_user(self, u: float) -> float:
        return (u - self.off) * self._sign()

    def _limit_v(self, v: float) -> float:
        v = max(self.cfg.vbas, v)
        if self.cfg.vmax > 0.0:
            v = min(v, self.cfg.vmax)
        return v

    def _start_motion(self, d_target: float, dir_override: Optional[bool] = None) -> None:
        self.lvio = 0
        self.dial_target = d_target
        self._moving = True
        self._jogging = False
        self.movn = 1
        self.dmov = 0
        self._dmov_ready_ts = 0.0
        dir_positive = (self.dial_target - self.dial_pos) >= 0.0 if dir_override is None else bool(dir_override)
        self.msta = _set_bit(self.msta, MSTA_DIRECTION, dir_positive)
        self.msta = _set_bit(self.msta, MSTA_MOVING, True)
        self.msta = _set_bit(self.msta, MSTA_DONE, False)

    def _arm_dmov_pulse_without_motion(self) -> None:
        self._moving = False
        self._jogging = False
        self.movn = 0
        self.dmov = 0
        self._dmov_ready_ts = time.monotonic() + max(self.cfg.dly, 0.0)
        self.msta = _set_bit(self.msta, MSTA_MOVING, False)
        self.msta = _set_bit(self.msta, MSTA_DONE, False)

    def move_user(self, u: float) -> Optional[str]:
        if abs(u - self.user_from_dial(self.dial_pos)) < max(self.cfg.spdb, 0.0):
            self._arm_dmov_pulse_without_motion()
            return None
        return self.move_dial(self.dial_from_user(u))

    def move_dial(self, d: float) -> Optional[str]:
        lo_u, hi_u = self.cfg.user_limits
        lo_d, hi_d = self.cfg.dial_limits

        if abs(self.user_from_dial(d) - self.user_from_dial(self.dial_pos)) < max(self.cfg.spdb, 0.0):
            self._arm_dmov_pulse_without_motion()
            return None

        if not (lo_d <= d <= hi_d):
            self.lvio = 1
            return f"Target {d:g} outside dial limits [{lo_d:g}, {hi_d:g}]"
        u = self.user_from_dial(d)
        if not (lo_u <= u <= hi_u):
            self.lvio = 1
            return f"Target {u:g} outside user limits [{lo_u:g}, {hi_u:g}]"

        self._start_motion(d)
        return None

    def stop(self) -> None:
        self._moving = False
        self._jogging = False
        self.movn = 0
        self._vel_now = 0.0
        self.dial_target = self.dial_pos
        self._dmov_ready_ts = time.monotonic() + max(self.cfg.dly, 0.0)
        self.dmov = 0
        self._homing = False
        self.msta = _set_bit(self.msta, MSTA_MOVING, False)
        self.msta = _set_bit(self.msta, MSTA_DONE, False)

    def home(self, forward: bool) -> None:
        if self._moving:
            self.stop()
        self._homing = True
        self._jogging = False
        self._start_motion(self._home_pos, dir_override=bool(forward))

    def jog(self, forward: bool, on: bool) -> None:
        if on:
            d = self.cfg.dial_limits[1] if forward else self.cfg.dial_limits[0]
            self._homing = False
            self._jogging = True
            self._start_motion(d, dir_override=bool(forward))
        else:
            self.stop()

    def _finish_at_target(self, now: float) -> None:
        """Common 'in-position' finishing sequence."""
        self._moving = False
        self._jogging = False
        self.movn = 0
        self._vel_now = 0.0
        self._dmov_ready_ts = now + max(self.cfg.dly, 0.0)
        self.msta = _set_bit(self.msta, MSTA_MOVING, False)
        self.msta = _set_bit(self.msta, MSTA_DONE, False)

    def step(self, now: float) -> None:
        dt = max(0.0, now - self._last_ts)
        self._last_ts = now

        lo_d, hi_d = self.cfg.dial_limits
        self.hls = 1 if self.dial_pos >= hi_d else 0
        self.lls = 1 if self.dial_pos <= lo_d else 0
        self.msta = _set_bit(self.msta, MSTA_PLUS_LS, bool(self.hls))
        self.msta = _set_bit(self.msta, MSTA_MINUS_LS, bool(self.lls))

        at_home = abs(self.dial_pos - self._home_pos) <= max(self.cfg.rdbd, 1e-6)
        self.msta = _set_bit(self.msta, MSTA_HOME, at_home)
        self.msta = _set_bit(self.msta, MSTA_HOMELS, at_home)

        # Handle DMOV pulse after settle delay
        if not self._moving:
            # check if home, set homed bit
            if self._homing and at_home:
                self.msta = _set_bit(self.msta, MSTA_HOMED, True)
                self._homing = False

            if self.dmov == 0 and self._dmov_ready_ts > 0 and now >= self._dmov_ready_ts:
                self.dmov = 1
                self.msta = _set_bit(self.msta, MSTA_DONE, True)
            return

        target = self.dial_target
        pos = self.dial_pos
        dist = target - pos
        adist = abs(dist)

        # If already effectively at target (use RDBD instead of epsilon), finish
        if adist <= max(self.cfg.rdbd, 1e-12):
            self.dial_pos = target
            self._finish_at_target(now)
            if self._homing and at_home:
                self.msta = _set_bit(self.msta, MSTA_HOMED, True)
                self._homing = False
            return

        # Choose velocity and accel limits
        if self._homing:
            v_target = self.cfg.hvel
        elif self._jogging:
            v_target = self.cfg.jvel if self.cfg.jvel > 0.0 else self.cfg.velo
        else:
            v_target = self.cfg.velo
        v_target = self._limit_v(v_target)
        a = self.cfg.jar if (self._jogging and self.cfg.jar > 0.0) else v_target / max(self.cfg.accl, 1e-6)

        # Speed update (bang-bang with braking distance)
        v = self._vel_now
        s_stop = (v * v) / (2 * max(a, 1e-9))
        if adist <= s_stop:
            v = max(0.0, v - a * dt)
        else:
            v = min(v_target, v + a * dt)

        # --- OVERSHOOT-PROOF STEP ---
        # Move no more than remaining distance; if we'd hit/past target, snap there.
        step_mag = v * dt
        if step_mag >= adist or v <= 1e-9:
            # We can reach (or are effectively at) target this tick.
            self.dial_pos = target
            self._finish_at_target(now)
            if self._homing and at_home:
                self.msta = _set_bit(self.msta, MSTA_HOMED, True)
                self._homing = False
            self._vel_now = 0.0
            return

        # Otherwise move toward target without overshooting
        self.dial_pos = pos + (step_mag if dist > 0 else -step_mag)
        self._vel_now = v

        # Limit switches clamp
        if self.dial_pos > hi_d:
            self.dial_pos = hi_d
            self._vel_now = 0.0
            self._finish_at_target(now)
        elif self.dial_pos < lo_d:
            self.dial_pos = lo_d
            self._vel_now = 0.0
            self._finish_at_target(now)


# ----------------------------
# PV layer
# ----------------------------

class PVs:
    """Create SharedPVs with correct meta, safe puts, and MDEL throttling.
       Also creates a root alias PV at '<prefix>' mapping VAL/RBV semantics.
    """
    def __init__(self, prefix: str, cfg: MotorConfig, write_cb):
        self.prefix = prefix.rstrip(":")
        self.cfg = cfg
        self.write_cb = write_cb
        self.pvs: Dict[str, SharedPV] = {}
        self.nts: Dict[str, NTScalar] = {}
        self._last_sent: Dict[str, Tuple[Any, int, str]] = {}
        self._mdel: float = 0.0  # EGU deadband for RBV/DRBV posting

        # Root/alias PV (no ".FIELD")
        self.root_nt: Optional[NTScalar] = None
        self.root_pv: Optional[SharedPV] = None
        self._last_root: Optional[Tuple[Any, int, str]] = None

        # Build PVs
        self._mk_motor_pvs()
        self._mk_root_alias()

    # --- utils

    def _ntwrap_and_update(self, suffix: str, value, meta_updates: Dict[str, Any]) -> None:
        """Build a fresh NT value (no in-place mutation of current()), apply meta updates, post."""
        pv = self.pvs[suffix]
        nt = self.nts[suffix]
        V = nt.wrap(value, timestamp=time.time())
        try:
            if nt.code() == 'd':
                V['display.units'] = self.cfg.egu
                V['display.precision'] = int(self.cfg.prec)
        except Exception:
            pass
        for k, v in meta_updates.items():
            try:
                V[k] = v
            except Exception:
                pass
        pv.post(V)

    def _post_meta(self, suffix: str, updates: Dict[str, Any]) -> None:
        pv = self.pvs[suffix]
        nt = self.nts[suffix]
        cur = pv.current()
        try:
            cur_val = cur['value']
        except Exception:
            cur_val = cur if not isinstance(cur, dict) else 0
        self._ntwrap_and_update(suffix, cur_val, updates)

    def _post_num(self, suffix: str, value: float | int, severity: int = 0, message: str = "", *, force: bool = False) -> None:
        """Only post when value/severity/message actually change, with MDEL for RBV/DRBV."""
        prev = self._last_sent.get(suffix)
        if suffix in ("RBV", "DRBV") and not force:
            if isinstance(value, (int, float)) and prev is not None and isinstance(prev[0], (int, float)):
                if self._mdel > 0.0 and abs(float(value) - float(prev[0])) < self._mdel and severity == prev[1] and message == prev[2]:
                    return
        if prev is not None and prev == (value, severity, message) and not force:
            return
        self.pvs[suffix].post(value, timestamp=time.time(), severity=severity, message=message)
        self._last_sent[suffix] = (value, severity, message)

    # --- root/alias helpers

    def _mk_root_alias(self) -> None:
        """Create '<prefix>' PV which:
           - GET/MONITOR => RBV (user units)
           - PUT(value)  => VAL write
        """
        nt = NTScalar('d', display=True, control=True, valueAlarm=True, form=True)
        self.root_nt = nt
        pv = SharedPV(nt=nt)
        self.root_pv = pv

        V = nt.wrap(0.0, timestamp=time.time())
        V["display.units"] = self.cfg.egu
        V["display.precision"] = int(self.cfg.prec)
        ulo, uhi = self.cfg.user_limits
        V["display.limitLow"] = ulo; V["display.limitHigh"] = uhi
        V["control.limitLow"] = ulo; V["control.limitHigh"] = uhi
        V["valueAlarm.lowAlarmLimit"] = ulo; V["valueAlarm.highAlarmLimit"] = uhi
        V["alarm.severity"] = 0
        V["alarm.status"] = 0
        V["alarm.message"] = "NO_ALARM"
        pv.open(V)

        @pv.put
        def _alias_put(pv_obj, op):
            raw = op.value()
            try:
                new = float(raw['value'])
            except Exception as e:
                try:
                    new = float(raw)
                except Exception:
                    op.done(error=f"Bad put payload for {self.prefix}: {e}")
                    return
            # Don't echo setpoint here; aliases follow RBV. Just forward to VAL.
            self.write_cb("VAL", new)
            op.done()

    def _post_root_num(self, value: float | int, severity: int = 0, message: str = "", *, force: bool = False) -> None:
        """Post to alias '<prefix>' with MDEL throttling (like RBV)."""
        prev = self._last_root
        if not force and isinstance(value, (int, float)) and prev is not None and isinstance(prev[0], (int, float)):
            if self._mdel > 0.0 and abs(float(value) - float(prev[0])) < self._mdel and severity == prev[1] and message == prev[2]:
                return
        if prev is not None and prev == (value, severity, message) and not force:
            return
        assert self.root_pv is not None
        self.root_pv.post(value, timestamp=time.time(), severity=severity, message=message)
        self._last_root = (value, severity, message)

    def _post_root_meta(self, updates: Dict[str, Any]) -> None:
        if self.root_pv is None or self.root_nt is None:
            return
        cur = self.root_pv.current()
        try:
            cur_val = cur['value']
        except Exception:
            cur_val = cur if not isinstance(cur, dict) else 0.0
        V = self.root_nt.wrap(cur_val, timestamp=time.time())
        # keep standard float meta aligned
        V["display.units"] = self.cfg.egu
        V["display.precision"] = int(self.cfg.prec)
        for k, v in updates.items():
            try:
                V[k] = v
            except Exception:
                pass
        self.root_pv.post(V)

    def set_mdel(self, new: float) -> None:
        self._mdel = max(0.0, float(new))
        # echo back (store-only semantics)
        self.pvs["MDEL"].post(self._mdel, timestamp=time.time())

    # --- makers

    def _mk_float(
        self,
        suffix: str,
        init: float,
        writeable: bool = True,
        display_limits: Optional[Tuple[float, float]] = None,
        control_limits: Optional[Tuple[float, float]] = None,
        with_alarm: bool = True,
    ) -> None:
        nt = NTScalar('d', display=True, control=True, valueAlarm=with_alarm, form=True)
        self.nts[suffix] = nt
        pv = SharedPV(nt=nt)
        self.pvs[suffix] = pv

        V = nt.wrap(init, timestamp=time.time())
        V["display.units"] = self.cfg.egu
        V["display.precision"] = int(self.cfg.prec)
        if display_limits is not None:
            V["display.limitLow"], V["display.limitHigh"] = display_limits
        if control_limits is not None:
            V["control.limitLow"], V["control.limitHigh"] = control_limits
            if with_alarm:
                V["valueAlarm.lowAlarmLimit"], V["valueAlarm.highAlarmLimit"] = control_limits
        V["alarm.severity"] = 0
        V["alarm.status"] = 0
        V["alarm.message"] = "NO_ALARM"
        pv.open(V)

        if writeable:
            @pv.put
            def _on_put(pv_obj, op):
                raw = op.value()
                try:
                    new = float(raw['value'])
                except Exception as e:
                    try:
                        new = float(raw)
                    except Exception:
                        op.done(error=f"Bad put payload for {self.prefix}.{suffix}: {e}")
                        return

                # Avoid duplicate posts on drive-like setpoints; the motor layer
                # (sync_drive_echo_to_target/position) will publish the authoritative value.
                if suffix in ("VAL", "DVAL", "RVAL"):
                    self.write_cb(suffix, new)
                    op.done()
                    return

                # All other float PVs (VELO, ACCL, limits, etc.) should echo immediately.
                self.write_cb(suffix, new)
                pv_obj.post(new, timestamp=time.time())
                self._last_sent[suffix] = (new, 0, "")
                op.done()

    def _mk_enum(self, suffix: str, choices, init_index: int = 0, writeable: bool = True) -> None:
        """
        Create an NTEnum PV that behaves like a RECCHOICE.
        Accepts puts as int index (0/1), string ("Pos"/"Neg"), or NTEnum-shaped payloads.
        """
        choices = list(choices)
        nt = NTEnum(display=True, control=True)
        self.nts[suffix] = nt

        idx = int(init_index)
        if not (0 <= idx < len(choices)):
            raise ValueError(f"enum index {idx} out of range 0..{len(choices) - 1}")

        # Build the initial NTEnum Value
        V = nt.wrap(idx, choices=list(choices), timestamp=time.time())
        V["display.limitLow"] = 0
        V["display.limitHigh"] = len(choices) - 1
        V["control.limitLow"] = 0
        V["control.limitHigh"] = len(choices) - 1
        V["control.minStep"] = 1
        V["alarm.severity"] = 0
        V["alarm.status"] = 0
        V["alarm.message"] = "NO_ALARM"

        # IMPORTANT: pass the fully-wrapped Value directly; don't also pass nt or call pv.open(V)
        pv = SharedPV(initial=V)
        self.pvs[suffix] = pv

        # Keep base meta so we can restore it after each put
        base_display = V["display"]
        base_control = V["control"]
        base_alarm = V["alarm"]

        def _parse_enum_put(payload) -> int:
            """
            Accepts:
              - {'value': {'index': i, 'choices': [...]}}  (NTEnum-shaped)
              - {'value': 'Pos'} / {'value': 1}            (scalar dict)
              - 'Pos' / 1                                   (raw)
            Returns integer index into choices.
            """
            v = payload
            if isinstance(v, dict):
                v = v.get("value", v)
                if isinstance(v, dict):
                    if "index" in v:  # proper NTEnum payload
                        v = v["index"]
                    elif "value" in v:  # sometimes nested scalar
                        v = v["value"]

            if isinstance(v, str):
                s = v.strip()
                if s.lstrip("-").isdigit():
                    idx2 = int(s)
                else:
                    try:
                        idx2 = choices.index(s)
                    except ValueError:
                        lower = [c.lower() for c in choices]
                        idx2 = lower.index(s.lower())
            else:
                idx2 = int(v)

            if not (0 <= idx2 < len(choices)):
                raise ValueError(f"enum index {idx2} out of range 0..{len(choices) - 1}")
            return idx2

        if writeable:
            @pv.put
            def _on_put(pv_obj, op, *, _nt=nt, _choices=choices):
                raw = op.value()
                try:
                    new_idx = _parse_enum_put(raw)
                except Exception as e:
                    op.done(error=f"Bad put payload for {self.prefix}.{suffix}: {e}")
                    return

                # Notify higher layer (Motor._handle_put) with the chosen index
                self.write_cb(suffix, new_idx)

                # Rebuild a fresh NTEnum Value and restore meta sections
                newV = _nt.wrap(new_idx, choices=list(_choices), timestamp=time.time())
                newV["display"] = base_display
                newV["control"] = base_control
                newV["alarm"] = base_alarm

                pv_obj.post(newV)
                self._last_sent[suffix] = (new_idx, 0, "")
                op.done()

    def _mk_int(self, suffix: str, init: int, code: str = 'h', writeable=True) -> None:
        nt = NTScalar(code, display=True, control=True, form=True)
        self.nts[suffix] = nt
        pv = SharedPV(nt=nt)
        self.pvs[suffix] = pv

        V = nt.wrap(int(init), timestamp=time.time())
        V["alarm.severity"] = 0
        V["alarm.status"] = 0
        V["alarm.message"] = "NO_ALARM"
        pv.open(V)

        if writeable:
            @pv.put
            def _on_put(pv_obj, op):
                raw = op.value()
                try:
                    new = int(raw['value'])
                except Exception as e:
                    try:
                        new = int(raw)
                    except Exception:
                        op.done(error=f"Bad put payload for {self.prefix}.{suffix}: {e}")
                        return
                self.write_cb(suffix, new)
                pv_obj.post(new, timestamp=time.time())
                self._last_sent[suffix] = (new, 0, "")
                op.done()

    def _mk_str(self, suffix: str, init: str, writeable=True) -> None:
        nt = NTScalar('s', display=True, form=True)
        self.nts[suffix] = nt
        pv = SharedPV(nt=nt)
        self.pvs[suffix] = pv
        V = nt.wrap(str(init), timestamp=time.time())
        V["alarm.severity"] = 0
        V["alarm.status"] = 0
        V["alarm.message"] = "NO_ALARM"
        pv.open(V)

        if writeable:
            @pv.put
            def _on_put(pv_obj, op):
                raw = op.value()
                try:
                    new = str(raw['value'])
                except Exception as e:
                    try:
                        new = str(raw)
                    except Exception:
                        op.done(error=f"Bad put payload for {self.prefix}.{suffix}: {e}")
                        return
                self.write_cb(suffix, new)
                pv_obj.post(new, timestamp=time.time())
                self._last_sent[suffix] = (new, 0, "")
                op.done()

    def _mk_motor_pvs(self) -> None:
        u_lo, u_hi = self.cfg.user_limits
        d_lo, d_hi = self.cfg.dial_limits

        # Drives
        self._mk_float("VAL",  0.0, True,  display_limits=(u_lo, u_hi), control_limits=(u_lo, u_hi))
        self._mk_float("DVAL", 0.0, True,  display_limits=(d_lo, d_hi), control_limits=(d_lo, d_hi))
        self._mk_float("RVAL", 0.0, True,  display_limits=(d_lo, d_hi), control_limits=(d_lo, d_hi))
        self._mk_float("RLV",  0.0, True,  display_limits=(u_lo, u_hi), control_limits=(u_lo, u_hi))

        # Readbacks/status
        self._mk_float("RBV",  0.0, False, display_limits=(u_lo, u_hi), control_limits=(u_lo, u_hi))
        self._mk_float("DRBV", 0.0, False, display_limits=(d_lo, d_hi), control_limits=(d_lo, d_hi))
        self._mk_int("DMOV", 1, 'h', False)
        self._mk_int("MOVN", 0, 'h', False)
        self._mk_int("MSTA", 0, 'I', False)
        self._mk_int("MISS", 0, 'h', False)

        # Motion params
        self._mk_float("VELO", self.cfg.velo, True)
        self._mk_float("VBAS", self.cfg.vbas, True)
        self._mk_float("VMAX", self.cfg.vmax, True)
        self._mk_float("ACCL", self.cfg.accl, True)
        self._mk_float("HVEL", self.cfg.hvel, True)
        self._mk_float("JVEL", self.cfg.jvel, True)
        self._mk_float("JAR",  self.cfg.jar,  True)
        self._mk_float("RDBD", self.cfg.rdbd, True)
        self._mk_float("SPDB", self.cfg.spdb, True)
        self._mk_float("DLY",  self.cfg.dly,  True)

        # Mapping / calibration / enable
        self._mk_enum("DIR", ["Pos", "Neg"], 0 if self.cfg.dir_pos else 1, True)
        self._mk_float("OFF", self.cfg.off, True)
        self._mk_int("SET",   0, 'h', True)
        self._mk_int("FOFF",  0, 'h', True)
        self._mk_int("CNEN",  1, 'h', True)

        # Limits mirrors/flags
        self._mk_float("HLM",  self.cfg.user_limits[1], True)
        self._mk_float("LLM",  self.cfg.user_limits[0], True)
        self._mk_float("DHLM", self.cfg.dial_limits[1], True)
        self._mk_float("DLLM", self.cfg.dial_limits[0], True)
        self._mk_int("LVIO", 0, 'h', False)
        self._mk_int("HLS",  0, 'h', False)
        self._mk_int("LLS",  0, 'h', False)

        # Commands
        self._mk_int("STOP", 0, 'h', True)
        self._mk_int("HOMF", 0, 'h', True)
        self._mk_int("HOMR", 0, 'h', True)
        self._mk_int("JOGF", 0, 'h', True)
        self._mk_int("JOGR", 0, 'h', True)

        # Misc
        self._mk_float("MDEL", 0.0, True)     # monitor deadband (EGU) – throttles RBV/DRBV
        self._mk_str("DESC",  "", True)

        # Formatting/units
        self._mk_str("EGU",  self.cfg.egu, True)
        self._mk_int("PREC", int(self.cfg.prec), 'h', True)

    # --- high-level posts

    def post_status_snapshot(self, state: MotorState) -> None:
        """
        Publish the current status/readbacks.
        Ensures a *forced* RBV/DRBV (and alias) post when motion completes,
        so MDEL doesn't suppress the final in-position value.
        """
        sev = 2 if (state.hls or state.lls) else 0
        msg = "at hardware limit" if sev else ""

        # Detect important edges using the last posted values.
        prev_movn = self._last_sent.get("MOVN", (None, None, None))[0]
        prev_dmov = self._last_sent.get("DMOV", (None, None, None))[0]
        force_final = (prev_movn == 1 and int(state.movn) == 0) or \
                      (prev_dmov == 0 and int(state.dmov) == 1)

        # RBV/DRBV (and root alias) respect MDEL except on the completion edges above.
        rbv = state.user_from_dial(state.dial_pos)
        self._post_num("DRBV", state.dial_pos, severity=sev, message=msg, force=force_final)
        self._post_num("RBV", rbv, severity=sev, message=msg, force=force_final)
        self._post_root_num(rbv, severity=sev, message=msg, force=force_final)

        # Ints and flags (only when changed).
        self._post_num("DMOV", int(state.dmov))
        self._post_num("MOVN", int(state.movn))
        self._post_num("LVIO", int(state.lvio))
        self._post_num("HLS", int(state.hls))
        self._post_num("LLS", int(state.lls))
        self._post_num("MSTA", int(state.msta))
        # set homing fields to 0 once the homing is done
        self._post_num("HOMF", int(state._homing))
        self._post_num("HOMR", int(state._homing))

    def sync_drive_echo_to_target(self, state: MotorState) -> None:
        self._post_num("DVAL", state.dial_target)
        self._post_num("RVAL", state.dial_target)
        self._post_num("VAL",  state.user_from_dial(state.dial_target))

    def sync_drive_echo_to_position(self, state: MotorState) -> None:
        self._post_num("DVAL", state.dial_pos)
        self._post_num("RVAL", state.dial_pos)
        self._post_num("VAL",  state.user_from_dial(state.dial_pos))
        # keep alias aligned immediately when we hard-sync to position
        self._post_root_num(state.user_from_dial(state.dial_pos), force=True)

    def update_float_meta_all(self, units: Optional[str] = None, precision: Optional[int] = None) -> None:
        for suffix, nt in self.nts.items():
            try:
                if nt.code() != 'd':
                    continue
            except Exception:
                continue
            updates = {}
            if units is not None:
                updates['display.units'] = units
            if precision is not None:
                updates['display.precision'] = int(precision)
            if updates:
                self._post_meta(suffix, updates)
        # update alias too
        alias_updates = {}
        if units is not None: alias_updates['display.units'] = units
        if precision is not None: alias_updates['display.precision'] = int(precision)
        if alias_updates:
            self._post_root_meta(alias_updates)


# ----------------------------
# Motor server
# ----------------------------

class Motor:
    def __init__(self, prefix: str, cfg: MotorConfig, tick_hz: float = 10.0):
        self.cfg = cfg
        self.state = MotorState(cfg)
        self.lock = threading.RLock()
        self.tick = 1.0 / tick_hz
        self.stop_evt = threading.Event()

        def _on_write(suffix: str, value):
            with self.lock:
                self._handle_put(suffix, value)

        self.pvs = PVs(prefix, cfg, _on_write)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _repost_limits_meta(self) -> None:
        u_lo, u_hi = self.cfg.user_limits
        d_lo, d_hi = self.cfg.dial_limits
        up_u = {'display.limitLow': u_lo, 'display.limitHigh': u_hi,
                'control.limitLow': u_lo, 'control.limitHigh': u_hi,
                'valueAlarm.lowAlarmLimit': u_lo, 'valueAlarm.highAlarmLimit': u_hi}
        up_d = {'display.limitLow': d_lo, 'display.limitHigh': d_hi,
                'control.limitLow': d_lo, 'control.limitHigh': d_hi,
                'valueAlarm.lowAlarmLimit': d_lo, 'valueAlarm.highAlarmLimit': d_hi}
        self.pvs._post_meta("VAL",  up_u)
        self.pvs._post_meta("RBV",  up_u)
        self.pvs._post_meta("DVAL", up_d)
        self.pvs._post_meta("DRBV", up_d)
        # alias uses user limits
        self.pvs._post_root_meta(up_u)

        self.pvs._post_num("LLM", u_lo)
        self.pvs._post_num("HLM", u_hi)
        self.pvs._post_num("DLLM", d_lo)
        self.pvs._post_num("DHLM", d_hi)

    def _sync_user_from_dial_limits(self) -> None:
        d_lo, d_hi = self.cfg.dial_limits
        lo_u = self.state.user_from_dial(d_lo)
        hi_u = self.state.user_from_dial(d_hi)
        if lo_u > hi_u:
            lo_u, hi_u = hi_u, lo_u
        self.cfg.user_limits = (lo_u, hi_u)
        self._repost_limits_meta()

    def _sync_dial_from_user_limits(self) -> None:
        u_lo, u_hi = self.cfg.user_limits
        lo_d = self.state.dial_from_user(u_lo)
        hi_d = self.state.dial_from_user(u_hi)
        if lo_d > hi_d:
            lo_d, hi_d = hi_d, lo_d
        self.cfg.dial_limits = (lo_d, hi_d)
        self._repost_limits_meta()

    def _handle_put(self, suffix: str, value):
        s = self.state
        c = self.cfg

        def clamp_vel(v):
            v = max(0.0, float(v))
            if c.vmax > 0.0:
                v = min(v, c.vmax)
            return max(c.vbas, v)

        def _handle_drive_put(kind: str, fvalue: float):
            if s.set_mode == 1 and s.foff == 0 and kind == "VAL":
                new_off = float(fvalue) - (s.dial_pos * s._sign())
                delta = new_off - s.off
                s.off = new_off
                self.pvs._post_num("OFF", s.off)
                u_lo, u_hi = c.user_limits
                c.user_limits = (u_lo + delta, u_hi + delta)
                self._sync_dial_from_user_limits()
                self.pvs._post_num("VAL", float(fvalue))
                self.pvs.post_status_snapshot(s)
                s._arm_dmov_pulse_without_motion()
                return

            if s.set_mode == 1 and s.foff == 1:
                if kind == "VAL":
                    d = s.dial_from_user(float(fvalue))
                else:
                    d = float(fvalue)
                d = _clamp(d, c.dial_limits[0], c.dial_limits[1])
                s.dial_pos = d
                s.dial_target = d
                s._moving = False
                s.movn = 0
                s._vel_now = 0.0
                s._homing = False
                s._jogging = False
                s._arm_dmov_pulse_without_motion()
                self.pvs.sync_drive_echo_to_position(s)
                self.pvs.post_status_snapshot(s)
                return

            if kind == "VAL":
                s.move_user(float(fvalue))
                self.pvs.sync_drive_echo_to_target(s)
            else:
                s.move_dial(float(fvalue))
                self.pvs.sync_drive_echo_to_target(s)

        if suffix in ("VAL", "DVAL", "RVAL"):
            _handle_drive_put(suffix, float(value))

        elif suffix == "RLV":
            u = s.user_from_dial(s.dial_pos) + float(value)
            _handle_drive_put("VAL", u)
            self.pvs._post_num("RLV", 0)

        elif suffix == "STOP":
            s.stop()
            self.pvs.sync_drive_echo_to_position(s)

        elif suffix == "HOMF":
            if int(value) == 1:
                s.home(forward=True)
            self.pvs._post_num("HOMF", 0)
            self.pvs.sync_drive_echo_to_target(s)

        elif suffix == "HOMR":
            if int(value) == 1:
                s.home(forward=False)
            self.pvs._post_num("HOMR", 0)
            self.pvs.sync_drive_echo_to_target(s)

        elif suffix == "JOGF":
            s.jog(forward=True, on=bool(int(value)))
            if not int(value):
                self.pvs.sync_drive_echo_to_position(s)

        elif suffix == "JOGR":
            s.jog(forward=False, on=bool(int(value)))
            if not int(value):
                self.pvs.sync_drive_echo_to_position(s)

        elif suffix == "DIR":
            prev_dir = s.dir_rec
            s.dir_rec = 0 if int(value) == 0 else 1
            self.pvs._post_num("VAL", s.user_from_dial(s.dial_pos))
            if s.dir_rec != prev_dir:
                self._sync_user_from_dial_limits()

        elif suffix == "OFF":
            old_off = s.off
            s.off = float(value)
            self.pvs._post_num("VAL", s.user_from_dial(s.dial_pos))
            delta = s.off - old_off
            u_lo, u_hi = c.user_limits
            c.user_limits = (u_lo + delta, u_hi + delta)
            self._sync_dial_from_user_limits()

        elif suffix == "SET":
            s.set_mode = 1 if int(value) else 0
            self.pvs._post_num("SET", int(s.set_mode))

        elif suffix == "FOFF":
            s.foff = 1 if int(value) else 0
            self.pvs._post_num("FOFF", int(s.foff))

        elif suffix == "CNEN":
            s.cnen = 1 if int(value) else 0
            self.pvs._post_num("CNEN", int(s.cnen))

        elif suffix == "EGU":
            self.cfg.egu = str(value)
            self.pvs.update_float_meta_all(units=self.cfg.egu)

        elif suffix == "PREC":
            self.cfg.prec = int(value)
            self.pvs.update_float_meta_all(precision=self.cfg.prec)

        elif suffix == "VELO":
            self.cfg.velo = clamp_vel(value)

        elif suffix == "JVEL":
            self.cfg.jvel = clamp_vel(value)

        elif suffix == "HVEL":
            self.cfg.hvel = clamp_vel(value)

        elif suffix == "VBAS":
            self.cfg.vbas = max(0.0, float(value))
            self.cfg.velo = max(self.cfg.velo, self.cfg.vbas)
            self.cfg.jvel = max(self.cfg.jvel, self.cfg.vbas)
            self.cfg.hvel = max(self.cfg.hvel, self.cfg.vbas)

        elif suffix == "VMAX":
            self.cfg.vmax = max(0.0, float(value))
            if self.cfg.vmax > 0.0:
                self.cfg.velo = min(self.cfg.velo, self.cfg.vmax)
                self.cfg.jvel = min(self.cfg.jvel, self.cfg.vmax)
                self.cfg.hvel = min(self.cfg.hvel, self.cfg.vmax)

        elif suffix == "ACCL":
            self.cfg.accl = max(1e-3, float(value))

        elif suffix == "JAR":
            self.cfg.jar = max(0.0, float(value))

        elif suffix == "RDBD":
            self.cfg.rdbd = max(0.0, float(value))

        elif suffix == "SPDB":
            self.cfg.spdb = max(0.0, float(value))

        elif suffix == "DLY":
            self.cfg.dly = max(0.0, float(value))

        elif suffix == "MDEL":
            self.pvs.set_mdel(float(value))

        elif suffix in ("HLM", "LLM", "DHLM", "DLLM"):
            v = float(value)
            if suffix == "HLM":
                lo_u, _ = c.user_limits
                c.user_limits = (lo_u, v)
                self._sync_dial_from_user_limits()
            elif suffix == "LLM":
                _, hi_u = c.user_limits
                c.user_limits = (v, hi_u)
                self._sync_dial_from_user_limits()
            elif suffix == "DHLM":
                lo_d, _ = c.dial_limits
                c.dial_limits = (lo_d, v)
                self._sync_user_from_dial_limits()
            elif suffix == "DLLM":
                _, hi_d = c.dial_limits
                c.dial_limits = (v, hi_d)
                self._sync_user_from_dial_limits()

            u = s.user_from_dial(s.dial_target)
            s.lvio = int(not (c.user_limits[0] <= u <= c.user_limits[1]) or
                        not (c.dial_limits[0] <= s.dial_target <= c.dial_limits[1]))

        # stored only: DESC

        self.pvs.post_status_snapshot(s)

    def _run(self) -> None:
        next_tick = time.monotonic()
        while not self.stop_evt.is_set():
            with self.lock:
                self.state.step(time.monotonic())
                self.pvs.post_status_snapshot(self.state)
            next_tick += self.tick
            time.sleep(max(0.0, next_tick - time.monotonic()))

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stop_evt.set()
        try:
            self.thread.join(timeout=1.0)
        except Exception:
            pass


# ----------------------------
# Factory & server wiring
# ----------------------------

def create_motor(prefix: str, cfg: Optional[MotorConfig] = None, tick_hz: float = 50.0) -> Motor:
    return Motor(prefix, cfg or MotorConfig(), tick_hz=tick_hz)

def build_provider_dict(motors: Dict[str, Motor]) -> Dict[str, SharedPV]:
    out: Dict[str, SharedPV] = {}
    for m in motors.values():
        # field PVs
        out.update({f"{m.pvs.prefix}.{k}": pv for k, pv in m.pvs.pvs.items()})
        # root alias PV (record-like)
        if m.pvs.root_pv is not None:
            out[m.pvs.prefix] = m.pvs.root_pv
    return out


# ----------------------------
# CLI
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Simulated EPICS motor record (p4p/PVA) with metadata + MDEL + VAL/RBV alias at '<prefix>'.")
    ap.add_argument("--prefix", default="SIM:M1", help="PV prefix (e.g., 'SIM:M1')")
    ap.add_argument("--tick-hz", type=float, default=10.0, help="Simulation tick frequency")
    ap.add_argument("--egu", default="mm", help="Engineering units string")
    ap.add_argument("--prec", type=int, default=3, help="Display precision (display.precision)")
    ap.add_argument("--llm", type=float, default=-1000.0, help="User low limit (VAL/RBV)")
    ap.add_argument("--hlm", type=float, default=+1000.0, help="User high limit (VAL/RBV)")
    ap.add_argument("--dllm", type=float, default=-1000.0, help="Dial low limit (DVAL/DRBV)")
    ap.add_argument("--dhlm", type=float, default=+1000.0, help="Dial high limit (DVAL/DRBV)")
    ap.add_argument("--velo", type=float, default=5.0, help="Motion VELO (EGU/s)")
    ap.add_argument("--vbas", type=float, default=0.0, help="Motion VBAS (EGU/s)")
    ap.add_argument("--vmax", type=float, default=0.0, help="Max velocity VMAX (EGU/s, 0=unlimited)")
    ap.add_argument("--accl", type=float, default=1.0, help="ACCL (seconds to VELO)")
    ap.add_argument("--hvel", type=float, default=2.0, help="Homing velocity")
    ap.add_argument("--jvel", type=float, default=2.0, help="Jog velocity")
    ap.add_argument("--jar",  type=float, default=0.0, help="Jog acceleration (EGU/s^2); 0=>use ACCL")
    ap.add_argument("--rdbd", type=float, default=0.001, help="In-position deadband (EGU)")
    ap.add_argument("--spdb", type=float, default=0.0, help="Set point deadband (EGU)")
    ap.add_argument("--dly",  type=float, default=0.0, help="DMOV settle delay (s)")
    ap.add_argument("--off",  type=float, default=0.0, help="User offset OFF")
    ap.add_argument("--dir",  type=int, default=0, help="DIR (0=Pos, 1=Neg)")
    ap.add_argument("--mdel", type=float, default=0.1, help="Initial MDEL deadband (EGU) for RBV/DRBV")
    args = ap.parse_args()

    cfg = MotorConfig(
        egu=args.egu,
        prec=args.prec,
        user_limits=(args.llm, args.hlm),
        dial_limits=(args.dllm, args.dhlm),
        velo=args.velo,
        vbas=args.vbas,
        vmax=args.vmax,
        accl=args.accl,
        hvel=args.hvel,
        jvel=args.jvel,
        jar=args.jar,
        rdbd=args.rdbd,
        spdb=args.spdb,
        dly=args.dly,
        off=args.off,
        dir_pos=(args.dir == 0),
    )

    motor = create_motor(args.prefix, cfg, tick_hz=args.tick_hz).start()
    provider = build_provider_dict({args.prefix: motor})

    # initialize MDEL after PVs exist
    motor.pvs.set_mdel(args.mdel)

    print(f"[sim-motor] Serving PVA motor at prefix '{args.prefix}'. "
          f"Alias '{args.prefix}' maps GET/MONITOR->RBV and PUT->VAL. Press Ctrl+C to exit.")
    try:
        with Server(providers=[provider]) as S:
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[sim-motor] Shutting down...")
    finally:
        motor.stop()


if __name__ == "__main__":
    main()

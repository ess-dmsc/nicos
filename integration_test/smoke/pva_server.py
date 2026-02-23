"""Local PVA server used by the smoke integration stack.

Provides:
- TEST:SMOKE:READ.RBV (readable scalar)
- TEST:SMOKE:MOVE.RBV (moveable readback)
- TEST:SMOKE:MOVE.VAL (moveable setpoint)

Writing MOVE.VAL updates MOVE.RBV after a short delay to simulate motion.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.thread import SharedPV


@dataclass(frozen=True)
class SmokePvNames:
    readable: str = "TEST:SMOKE:READ.RBV"
    move_read: str = "TEST:SMOKE:MOVE.RBV"
    move_write: str = "TEST:SMOKE:MOVE.VAL"


def _make_float_pv(init: float, *, units: str, low: float, high: float) -> SharedPV:
    nt = NTScalar("d", display=True, control=True, valueAlarm=True, form=True)
    pv = SharedPV(nt=nt)

    wrapped = nt.wrap(float(init), timestamp=time.time())
    wrapped["display.units"] = units
    wrapped["display.precision"] = 3
    wrapped["display.limitLow"] = float(low)
    wrapped["display.limitHigh"] = float(high)
    wrapped["control.limitLow"] = float(low)
    wrapped["control.limitHigh"] = float(high)
    wrapped["alarm.severity"] = 0
    wrapped["alarm.status"] = 0
    wrapped["alarm.message"] = "NO_ALARM"
    pv.open(wrapped)

    @pv.put
    def _on_put(pv_obj, op):
        raw = op.value()
        try:
            new_value = float(raw["value"])
        except Exception:
            new_value = float(raw)
        pv_obj.post(new_value, timestamp=time.time())
        op.done()

    return pv


class SmokePvaServer:
    """Small in-process PVA server for smoke runs."""

    def __init__(self, *, move_delay_s: float = 0.35):
        self.names = SmokePvNames()
        self.move_delay_s = float(move_delay_s)

        self._readable_pv = _make_float_pv(1.23, units="A", low=-1e3, high=1e3)
        self._move_read_pv = _make_float_pv(0.0, units="Hz", low=0.0, high=100.0)
        self._move_write_pv = _make_float_pv(0.0, units="Hz", low=0.0, high=100.0)

        @self._move_write_pv.put
        def _on_move_put(pv_obj, op):
            raw = op.value()
            try:
                target = float(raw["value"])
            except Exception:
                target = float(raw)

            # Write target immediately, then update readback asynchronously.
            pv_obj.post(target, timestamp=time.time())

            def _finish_motion():
                time.sleep(self.move_delay_s)
                self._move_read_pv.post(target, timestamp=time.time())

            threading.Thread(target=_finish_motion, daemon=True).start()
            op.done()

        self._providers = {
            self.names.readable: self._readable_pv,
            self.names.move_read: self._move_read_pv,
            self.names.move_write: self._move_write_pv,
        }

        self._stop_evt = threading.Event()
        self._ready_evt = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._exc = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return

            self._stop_evt.clear()
            self._ready_evt.clear()
            self._exc = None

            def _run() -> None:
                try:
                    with Server(providers=[self._providers]):
                        self._ready_evt.set()
                        self._stop_evt.wait()
                except Exception as err:  # pragma: no cover - defensive path
                    self._exc = err
                    self._ready_evt.set()

            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()

        self._ready_evt.wait(timeout=5.0)
        if self._exc is not None:
            raise self._exc

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._thread = None

        if thread is None:
            return

        self._stop_evt.set()
        thread.join(timeout=5.0)

import threading
import time

from p4p.nt import NTEnum, NTScalar
from p4p.server import Server
from p4p.server.thread import SharedPV


def make_float_pv(init: float, *, units: str = "mm", precision: int = 3) -> SharedPV:
    nt = NTScalar("d", display=True, control=True, valueAlarm=True, form=True)
    pv = SharedPV(nt=nt)

    V = nt.wrap(float(init), timestamp=time.time())
    V["display.units"] = units
    V["display.precision"] = int(precision)
    V["alarm.severity"] = 0
    V["alarm.status"] = 0
    V["alarm.message"] = "NO_ALARM"
    pv.open(V)

    @pv.put
    def _on_put(pv_obj, op):
        raw = op.value()
        try:
            new = float(raw["value"])
        except Exception:
            new = float(raw)
        pv_obj.post(new, timestamp=time.time())
        op.done()

    return pv


def make_int_pv(init: int) -> SharedPV:
    nt = NTScalar("h", display=True, control=True, form=True)
    pv = SharedPV(nt=nt)

    V = nt.wrap(int(init), timestamp=time.time())
    V["alarm.severity"] = 0
    V["alarm.status"] = 0
    V["alarm.message"] = "NO_ALARM"
    pv.open(V)

    @pv.put
    def _on_put(pv_obj, op):
        raw = op.value()
        try:
            new = int(raw["value"])
        except Exception:
            new = int(raw)
        pv_obj.post(new, timestamp=time.time())
        op.done()

    return pv


def make_str_pv(init: str) -> SharedPV:
    nt = NTScalar("s", display=True)  # no form=True
    pv = SharedPV(nt=nt)

    V = nt.wrap(str(init), timestamp=time.time())
    V["alarm.severity"] = 0
    V["alarm.status"] = 0
    V["alarm.message"] = "NO_ALARM"
    pv.open(V)

    @pv.put
    def _on_put(pv_obj, op):
        raw = op.value()

        try:
            v = raw["value"]
        except Exception:
            v = raw

        # Be defensive: sometimes "value" may itself be nested.
        if isinstance(v, dict) and "value" in v:
            v = v["value"]

        if isinstance(v, (bytes, bytearray, memoryview)):
            new = bytes(v).decode(errors="replace")
        elif isinstance(v, str):
            # Drop any p4p string subclass (eg ntstr) without calling its __str__.
            new = v[:]
        else:
            new = str(v)

        pv_obj.post(new, timestamp=time.time())
        op.done()

    return pv


def make_array_float_pv(init: list[float]) -> SharedPV:
    # array of double
    nt = NTScalar("ad", display=True, form=True)
    pv = SharedPV(nt=nt)

    V = nt.wrap(list(init), timestamp=time.time())
    V["alarm.severity"] = 0
    V["alarm.status"] = 0
    V["alarm.message"] = "NO_ALARM"
    pv.open(V)

    @pv.put
    def _on_put(pv_obj, op):
        raw = op.value()
        try:
            seq = raw["value"]
        except Exception:
            seq = raw
        pv_obj.post([float(x) for x in seq], timestamp=time.time())
        op.done()

    return pv


def make_enum_pv(choices: list[str], *, init_index: int = 0) -> SharedPV:
    # This is basically your working pattern. Don't get clever here.
    nt = NTEnum(display=True, control=True)

    idx = int(init_index)
    if not (0 <= idx < len(choices)):
        raise ValueError("init_index out of range")

    V = nt.wrap(idx, choices=list(choices), timestamp=time.time())
    V["display.limitLow"] = 0
    V["display.limitHigh"] = len(choices) - 1
    V["display.description"] = "Enum PV"
    V["control.limitLow"] = 0
    V["control.limitHigh"] = len(choices) - 1
    V["control.minStep"] = 1
    V["alarm.severity"] = 0
    V["alarm.status"] = 0
    V["alarm.message"] = "NO_ALARM"

    class Handler:
        def put(self, pv, op, *, _nt=nt, _choices=choices, base_meta=V):
            raw = op.value()
            new_idx = int(raw["value"]["index"])
            if new_idx < 0 or new_idx >= len(_choices):
                op.done(error="enum index out of range")
                return

            newV = _nt.wrap(new_idx, choices=list(_choices), timestamp=time.time())
            newV["display"] = base_meta["display"]
            newV["control"] = base_meta["control"]
            newV["alarm"] = base_meta["alarm"]
            pv.post(newV)
            op.done()

    return SharedPV(initial=V, handler=Handler())


class PvaServer:
    def __init__(self, providers):
        self._providers = providers
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

            def _run():
                try:
                    with Server(providers=[self._providers]) as _srv:
                        # "server is up" signal; it doesn't guarantee reachability yet,
                        # so tests should still do ctx.get/pv.post to force activity.
                        self._ready_evt.set()
                        self._stop_evt.wait()
                except Exception as e:
                    self._exc = e
                    self._ready_evt.set()

            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()

        # wait until thread entered the Server context (or failed)
        self._ready_evt.wait(timeout=5.0)
        if self._exc is not None:
            raise self._exc

    def stop(self) -> None:
        with self._lock:
            t = self._thread
            self._thread = None

        if t is None:
            return

        self._stop_evt.set()
        t.join(timeout=5.0)

    def restart(self) -> None:
        self.stop()
        self.start()

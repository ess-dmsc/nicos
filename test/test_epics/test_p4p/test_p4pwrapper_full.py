from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

import numpy as np
import pytest
from p4p.client.thread import Context
from p4p.server.thread import SharedPV

from nicos.core import status
from nicos.devices.epics.pva.p4p import P4pWrapper
from nicos.devices.epics.status import SEVERITY_TO_STATUS

from test.test_epics.test_p4p.utils.p4p_doubles import EventSink
from test.test_epics.test_p4p.utils.pva_server import (
    PvaServer,
    make_array_float_pv,
    make_enum_pv,
    make_float_pv,
    make_int_pv,
    make_str_pv,
)

_ENUM_CHOICES = ["Alpha", "Beta", "Gamma", "Delta"]
_TIMEOUT = 5.0 # seconds

def _any_non_ok_alarm_severity() -> tuple[int, int]:
    # Return (epics_sev_int, nicos_status_int)
    for sev, st in SEVERITY_TO_STATUS.items():
        if st in (status.WARN, status.ERROR):
            return sev, st
    # fallback (shouldn't really happen)
    sev = next(iter(SEVERITY_TO_STATUS))
    return sev, SEVERITY_TO_STATUS[sev]


def wait_for(predicate, *, timeout: float = _TIMEOUT, interval: float = 0.02) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError("timeout waiting for condition")


@dataclass(frozen=True)
class PvaRig:
    prefix: str
    pvs: dict[str, SharedPV]
    providers: dict[str, SharedPV]
    server: PvaServer
    ctx: Context

    def name(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"


@pytest.fixture(scope="module")
def pva_rig() -> PvaRig:
    prefix = f"TEST:P4PWRAP:{uuid.uuid4().hex[:8]}"

    pvs: dict[str, SharedPV] = {
        "Float": make_float_pv(1.25, units="mm"),
        "Int": make_int_pv(7),
        "Str": make_str_pv("hello"),
        "Arr": make_array_float_pv([1.0, 2.0, 3.0]),
        "Enum": make_enum_pv(_ENUM_CHOICES, init_index=1),
    }

    providers = {f"{prefix}:{k}": v for k, v in pvs.items()}
    srv = PvaServer(providers)
    srv.start()

    ctx = Context("pva", nt=False)
    rig = PvaRig(
        prefix=prefix,
        pvs=pvs,
        providers=providers,
        server=srv,
        ctx=ctx,
    )

    # Reachability probe: do one get via a temporary wrapper.
    probe = P4pWrapper(timeout=2.0, context=ctx)
    try:
        wait_for(lambda: _can_get(probe, rig.name("Float")), timeout=_TIMEOUT)
    except AssertionError:
        srv.stop()
        pytest.skip("p4p PVA server not reachable in this environment")

    try:
        yield rig
    finally:
        try:
            srv.stop()
        finally:
            try:
                ctx.close()
            except Exception:
                pass


@pytest.fixture()
def pva_wrapper(pva_rig: PvaRig) -> P4pWrapper:
    # Fresh wrapper per test to avoid leaked monitor state / refcnt / caches.
    return P4pWrapper(timeout=2.0, context=pva_rig.ctx)


@pytest.fixture(autouse=True)
def _reset_pvs(pva_rig: PvaRig):
    pva_rig.ctx.put(pva_rig.name("Float"), 1.25, wait=True, timeout=2.0, process="true")
    pva_rig.ctx.put(pva_rig.name("Int"), 7, wait=True, timeout=2.0, process="true")
    pva_rig.ctx.put(
        pva_rig.name("Str"), "hello", wait=True, timeout=2.0, process="true"
    )
    pva_rig.ctx.put(
        pva_rig.name("Arr"), [1.0, 2.0, 3.0], wait=True, timeout=2.0, process="true"
    )
    pva_rig.ctx.put(pva_rig.name("Enum"), 1, wait=True, timeout=2.0, process="true")

    yield


def _can_get(pva_wrapper: P4pWrapper, pvname: str) -> bool:
    try:
        pva_wrapper.get_pv_value(pvname)
        return True
    except Exception:
        return False


def test_get_smoke(pva_rig: PvaRig, pva_wrapper: P4pWrapper):
    assert pva_wrapper.get_pv_value(pva_rig.name("Float")) == pytest.approx(1.25)
    assert pva_wrapper.get_pv_value(pva_rig.name("Int")) == 7
    assert pva_wrapper.get_pv_value(pva_rig.name("Str"), as_string=True) == "hello"

    arr = pva_wrapper.get_pv_value(pva_rig.name("Arr"))
    assert isinstance(arr, np.ndarray)
    assert np.allclose(arr, np.array([1.0, 2.0, 3.0]))

    # Enum: raw index, and as_string() maps via choices
    assert pva_wrapper.get_pv_value(pva_rig.name("Enum")) == 1
    assert pva_wrapper.get_pv_value(pva_rig.name("Enum"), as_string=True) == "Beta"


def test_put_roundtrip_smoke_using_wrapper_put(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    pva_wrapper.put_pv_value(pva_rig.name("Float"), 9.5, wait=True)
    wait_for(lambda: abs(pva_wrapper.get_pv_value(pva_rig.name("Float")) - 9.5) < 1e-9)

    pva_wrapper.put_pv_value(pva_rig.name("Int"), 42, wait=True)
    wait_for(lambda: pva_wrapper.get_pv_value(pva_rig.name("Int")) == 42)

    pva_wrapper.put_pv_value(pva_rig.name("Str"), "world", wait=True)
    wait_for(
        lambda: pva_wrapper.get_pv_value(pva_rig.name("Str"), as_string=True) == "world"
    )

    # Enum: put by index
    pva_wrapper.put_pv_value(pva_rig.name("Enum"), 3, wait=True)
    wait_for(lambda: pva_wrapper.get_pv_value(pva_rig.name("Enum")) == 3)
    assert pva_wrapper.get_pv_value(pva_rig.name("Enum"), as_string=True) == "Delta"


def test_monitor_change_and_connection_callbacks(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    pvname = pva_rig.name("Float")
    pv = pva_rig.pvs["Float"]

    change = EventSink()
    conn = EventSink()

    sub = pva_wrapper.subscribe(pvname, "value", change, conn)

    try:
        # Trigger a value update from server side (monitor path)
        pv.post(2.5, timestamp=time.time())
        change.wait_calls(1, timeout=_TIMEOUT)

        args, _ = change.calls[-1]
        assert args[0] == pvname
        assert args[1] == "value"
        assert args[2] == pytest.approx(2.5)

        # Connection should have come up at least once, but only once for this pv/param.
        conn.wait_calls(1, timeout=_TIMEOUT)
        assert conn.calls[0][0] == (pvname, "value", True)

        # Alarm-only-ish update: post same value but with alarm severity/message.
        sev_key, expected_nicos = _any_non_ok_alarm_severity()
        pv.post(2.5, timestamp=time.time(), severity=sev_key, message="test alarm")
        change.wait_calls(2, timeout=_TIMEOUT)

        args, _ = change.calls[-1]
        assert args[2] == pytest.approx(2.5)
        assert args[5] == expected_nicos
        assert args[6] == "test alarm"
    finally:
        pva_wrapper.close_subscription(sub)


def test_multiple_subscriptions_single_conn_up(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    pvname = pva_rig.name("Int")
    pv = pva_rig.pvs["Int"]

    conn = EventSink()
    ch1 = EventSink()
    ch2 = EventSink()

    sub1 = pva_wrapper.subscribe(pvname, "status", ch1, conn)
    sub2 = pva_wrapper.subscribe(pvname, "status", ch2, conn)

    try:
        pv.post(100, timestamp=time.time())
        ch1.wait_calls(1, timeout=_TIMEOUT)
        ch2.wait_calls(1, timeout=_TIMEOUT)

        # Still only one "connected" for (pvname, pvparam)
        conn.wait_calls(1, timeout=_TIMEOUT)
        assert len(conn.calls) == 1
        assert conn.calls[0][0] == (pvname, "status", True)
    finally:
        pva_wrapper.close_subscription(sub1)
        pva_wrapper.close_subscription(sub2)


def test_two_subscriptions_slow_connection_callback_ends_connected(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    """
    Regression for: notify_disconnect=True + multiple subs + slow connection callback
    could leave final device state "disconnected" during startup.
    """
    pvname = pva_rig.name("Float")
    pvparam = "readpv.cache_key"  # same key, like devices do
    pv = pva_rig.pvs["Float"]

    ch1 = EventSink()
    ch2 = EventSink()

    conn_calls_lock = threading.Lock()
    conn_calls = []  # list of tuples: (ts, is_connected, kwargs)

    def slow_conn_cb(_pvname, _pvparam, is_connected, **kwargs):
        with conn_calls_lock:
            conn_calls.append((time.time(), is_connected, dict(kwargs)))
        time.sleep(0.5)

    def has_up():
        with conn_calls_lock:
            return any(call[1] is True for call in conn_calls)

    sub1 = pva_wrapper.subscribe(pvname, pvparam, ch1, slow_conn_cb)
    sub2 = pva_wrapper.subscribe(pvname, pvparam, ch2, slow_conn_cb)

    try:
        pv.post(1.26, timestamp=time.time())
        pv.post(1.27, timestamp=time.time())

        ch1.wait_calls(1, timeout=_TIMEOUT)
        ch2.wait_calls(1, timeout=_TIMEOUT)

        wait_for(
            has_up,
            timeout=_TIMEOUT,
            interval=0.02,
        )

        with conn_calls_lock:
            first_up_idx = next(i for i, c in enumerate(conn_calls) if c[1] is True)
            assert not any(c[1] is False for c in conn_calls[first_up_idx + 1 :])

        wait_for(
            lambda: pva_wrapper._conn_refcnt.get((pvname, pvparam), 0) > 0,
            timeout=_TIMEOUT,
            interval=0.02,
        )
    finally:
        pva_wrapper.close_subscription(sub1)
        pva_wrapper.close_subscription(sub2)


def test_two_subscriptions_fast_connection_callback_ends_connected(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    """
    Regression for: notify_disconnect=True + multiple subs + fast connection callback
    could leave final device state "disconnected" during startup.
    """
    pvname = pva_rig.name("Float")
    pvparam = "readpv.cache_key"  # same key, like devices do
    pv = pva_rig.pvs["Float"]

    ch1 = EventSink()
    ch2 = EventSink()

    conn_calls_lock = threading.Lock()
    conn_calls = []  # list of tuples: (ts, is_connected, kwargs)

    def fast_conn_cb(_pvname, _pvparam, is_connected, **kwargs):
        with conn_calls_lock:
            conn_calls.append((time.time(), is_connected, dict(kwargs)))

    def has_up():
        with conn_calls_lock:
            return any(call[1] is True for call in conn_calls)

    sub1 = pva_wrapper.subscribe(pvname, pvparam, ch1, fast_conn_cb)
    sub2 = pva_wrapper.subscribe(pvname, pvparam, ch2, fast_conn_cb)

    try:
        # Kick the PV so both monitors definitely get a non-exception update.
        pv.post(1.26, timestamp=time.time())
        pv.post(1.27, timestamp=time.time())

        # Each subscription should see at least one value callback.
        ch1.wait_calls(1, timeout=_TIMEOUT)
        ch2.wait_calls(1, timeout=_TIMEOUT)

        # We should have seen an "up" connection notification (aggregated at pvparam level).
        wait_for(
            has_up,
            timeout=_TIMEOUT,
            interval=0.02,
        )

        with conn_calls_lock:
            # After the first "up", there must be no "down" during this startup phase.
            first_up_idx = next(i for i, c in enumerate(conn_calls) if c[1] is True)
            assert not any(c[1] is False for c in conn_calls[first_up_idx + 1 :])

        # Group should end connected.
        wait_for(
            lambda: pva_wrapper._conn_refcnt.get((pvname, pvparam), 0) > 0,
            timeout=_TIMEOUT,
            interval=0.02,
        )
    finally:
        pva_wrapper.close_subscription(sub1)
        pva_wrapper.close_subscription(sub2)


def test_restart_two_subscriptions_finally_connected_even_with_slow_conn_cb(
    pva_rig: PvaRig, pva_wrapper: P4pWrapper
):
    pvname = pva_rig.name("Float")
    pv = pva_rig.pvs["Float"]

    conn = EventSink()
    ch1 = EventSink()
    ch2 = EventSink()

    def slow_conn_cb(name, param, is_connected, **kwargs):
        conn(name, param, is_connected, **kwargs)
        time.sleep(0.5)

    # Same pvparam for both subs (this is what NICOS devices do)
    sub1 = pva_wrapper.subscribe(pvname, "value", ch1, slow_conn_cb)
    sub2 = pva_wrapper.subscribe(pvname, "value", ch2, slow_conn_cb)

    # Force initial activity so both monitors definitely see something.
    pv.post(1.26, timestamp=time.time())
    ch1.wait_calls(1, timeout=_TIMEOUT)
    ch2.wait_calls(1, timeout=_TIMEOUT)

    # Both subs should be connected in wrapper bookkeeping
    wait_for(
        lambda: pva_wrapper._conn_refcnt.get((pvname, "value"), 0) == 2, timeout=_TIMEOUT
    )
    assert pva_wrapper._sub_connected[sub1._nicos_subkey] is True
    assert pva_wrapper._sub_connected[sub2._nicos_subkey] is True

    # Restart server (simulate IOC restart)
    pva_rig.server.restart()

    # After stop/start, p4p may deliver Cancelled or other Exception to monitors.
    # Your wrapper updates bookkeeping either way; rely on that.
    wait_for(
        lambda: pva_wrapper._conn_refcnt.get((pvname, "value"), 0) == 0, timeout=_TIMEOUT
    )
    assert pva_wrapper._sub_connected[sub1._nicos_subkey] is False
    assert pva_wrapper._sub_connected[sub2._nicos_subkey] is False

    # Now make the restarted server emit an update so monitors reconnect and deliver.
    pv.post(1.27, timestamp=time.time())

    wait_for(
        lambda: pva_wrapper._conn_refcnt.get((pvname, "value"), 0) == 2, timeout=_TIMEOUT
    )
    assert pva_wrapper._sub_connected[sub1._nicos_subkey] is True
    assert pva_wrapper._sub_connected[sub2._nicos_subkey] is True

    # Connection callback should end in connected state.
    # We *expect* at least two "up" events: one initial, one after restart.
    wait_for(lambda: sum(1 for c in conn.calls if c[0][2] is True) >= 2, timeout=_TIMEOUT)

    # no "down" after the last "up"
    last_up_idx = max(i for i, c in enumerate(conn.calls) if c[0][2] is True)
    assert not any(c[0][2] is False for c in conn.calls[last_up_idx + 1 :])

    pva_wrapper.close_subscription(sub1)
    pva_wrapper.close_subscription(sub2)

from __future__ import annotations

import numpy as np
import pytest

from nicos.core import CommunicationError, status
from nicos.devices.epics.pva.p4p import P4pWrapper, pvget, pvput
from nicos.devices.epics.status import SEVERITY_TO_STATUS

from test.test_epics.test_p4p.utils.p4p_doubles import (
    CallSpy,
    FakeContext,
    FakeEnumValue,
    FakeSubscription,
    FakeUpdate,
)


def _any_severity_key() -> int:
    return next(iter(SEVERITY_TO_STATUS))


@pytest.fixture()
def fake_context():
    return FakeContext()


def test_pvget_uses_global_context_and_returns_value(monkeypatch):
    fake_context = FakeContext()
    fake_context.set_get_result("PV:GLOBAL", {"value": 123})

    from nicos.devices.epics.pva import p4p as p4p_mod

    monkeypatch.setattr(p4p_mod, "_CONTEXT", fake_context)

    assert pvget("PV:GLOBAL", timeout=4.2) == 123
    assert fake_context.get_calls == [("PV:GLOBAL", 4.2)]


def test_pvput_uses_global_context_with_expected_flags(monkeypatch):
    fake_context = FakeContext()

    from nicos.devices.epics.pva import p4p as p4p_mod

    monkeypatch.setattr(p4p_mod, "_CONTEXT", fake_context)

    pvput("PV:GLOBAL:PUT", 11, wait=True, timeout=2.5)
    assert fake_context.put_calls == [("PV:GLOBAL:PUT", 11, 2.5, True, "true")]


def test_connect_pv_ok_calls_get_with_timeout(fake_context: FakeContext):
    fake_context.set_get_result("PV:OK", {"value": 1})
    pva_wrapper = P4pWrapper(timeout=1.23, context=fake_context)

    pva_wrapper.connect_pv("PV:OK")

    assert fake_context.get_calls == [("PV:OK", 1.23)]


def test_connect_pv_timeout_raises_communicationerror(fake_context: FakeContext):
    fake_context.set_get_result("PV:TIMEOUT", TimeoutError("nope"))
    pva_wrapper = P4pWrapper(timeout=0.5, context=fake_context)

    with pytest.raises(CommunicationError) as excinfo:
        pva_wrapper.connect_pv("PV:TIMEOUT")

    assert "could not connect to PV PV:TIMEOUT" in str(excinfo.value)


def test_get_pv_value_returns_scalar(fake_context: FakeContext):
    fake_context.set_get_result("PV:INT", {"value": 42})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_pv_value("PV:INT") == 42
    assert fake_context.get_calls == [("PV:INT", 1.0)]


def test_get_pv_value_as_string_converts_ndarray_to_string(fake_context: FakeContext):
    fake_context.set_get_result("PV:WFM", {"value": np.array([65, 66], dtype=np.uint8)})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_pv_value("PV:WFM", as_string=True) == "AB"


def test_get_pv_value_enum_as_int_and_string(fake_context: FakeContext):
    enum_val = FakeEnumValue(index=1, choices=["ZERO", "ONE", "TWO"])

    fake_context.set_get_result("PV:ENUM", {"value": enum_val})
    pva_wrapper = P4pWrapper(timeout=2.0, context=fake_context)

    # Raw enum returns index
    assert pva_wrapper.get_pv_value("PV:ENUM") == 1

    # as_string=True maps via choices (and populates the cache)
    assert pva_wrapper.get_pv_value("PV:ENUM", as_string=True) == "ONE"
    assert pva_wrapper._choices["PV:ENUM"] == ["ZERO", "ONE", "TWO"]


def test_put_pv_value_passes_process_true_timeout_and_wait(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.5, context=fake_context)

    pva_wrapper.put_pv_value("PV:W", 12.34, wait=False)
    assert fake_context.put_calls == [("PV:W", 12.34, 1.5, False, "true")]

    pva_wrapper.put_pv_value("PV:W2", 99, wait=True)
    assert fake_context.put_calls[-1] == ("PV:W2", 99, 1.5, True, "true")


def test_put_pv_value_blocking_uses_block_timeout_wait_true_process_true(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=0.1, context=fake_context)

    pva_wrapper.put_pv_value_blocking("PV:B", 7, block_timeout=60)
    assert fake_context.put_calls == [("PV:B", 7, 60, True, "true")]


def test_get_pv_type_enum_returns_int(fake_context: FakeContext):
    fake_context.set_get_result(
        "PV:ENUM", {"value": FakeEnumValue(index=0, choices=["A"])}
    )
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_pv_type("PV:ENUM") is int


def test_get_pv_type_scalar_returns_python_type(fake_context: FakeContext):
    fake_context.set_get_result("PV:FLOAT", {"value": 3.14})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_pv_type("PV:FLOAT") is float


def test_get_units_default_when_missing_display(fake_context: FakeContext):
    fake_context.set_get_result("PV:NODISPLAY", {"value": 1})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_units("PV:NODISPLAY", default="") == ""
    assert pva_wrapper.get_units("PV:NODISPLAY", default="mm") == "mm"


def test_get_units_from_display(fake_context: FakeContext):
    fake_context.set_get_result("PV:UNITS", {"value": 1, "display": {"units": "deg"}})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_units("PV:UNITS") == "deg"


def test_get_limits_default_when_missing_display(fake_context: FakeContext):
    fake_context.set_get_result("PV:NOLIM", {"value": 1})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_limits("PV:NOLIM") == (-1e308, 1e308)


def test_get_limits_from_display(fake_context: FakeContext):
    fake_context.set_get_result(
        "PV:LIM",
        {"value": 1, "display": {"limitLow": -5.0, "limitHigh": 5.0}},
    )
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_limits("PV:LIM") == (-5.0, 5.0)


def test_get_control_values_prefers_display(fake_context: FakeContext):
    fake_context.set_get_result(
        "PV:CTRL", {"display": {"foo": "bar"}, "control": {"x": 1}}
    )
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_control_values("PV:CTRL") == {"foo": "bar"}


def test_get_control_values_falls_back_to_control(fake_context: FakeContext):
    fake_context.set_get_result("PV:CTRL2", {"control": {"min": 1, "max": 2}})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_control_values("PV:CTRL2") == {"min": 1, "max": 2}


def test_get_control_values_empty_when_missing(fake_context: FakeContext):
    fake_context.set_get_result("PV:CTRL3", {"value": 1})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_control_values("PV:CTRL3") == {}


def test_get_value_choices_bool(fake_context: FakeContext):
    fake_context.set_get_result("PV:BOOL", {"value": True})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_value_choices("PV:BOOL") == [False, True]


def test_get_value_choices_non_iterable_returns_empty(fake_context: FakeContext):
    fake_context.set_get_result("PV:INT", {"value": 5})
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_value_choices("PV:INT") == []


def test_get_value_choices_enum_reads_and_caches(fake_context: FakeContext):
    fake_context.set_get_result(
        "PV:ENUM", {"value": FakeEnumValue(index=0, choices=["A", "B"])}
    )
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    assert pva_wrapper.get_value_choices("PV:ENUM") == ["A", "B"]
    assert pva_wrapper._choices["PV:ENUM"] == ["A", "B"]


def test_extract_alarm_info_maps_severity_and_filters_no_alarm(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)
    sev_key = _any_severity_key()
    mapped = SEVERITY_TO_STATUS[sev_key]

    severity, msg = pva_wrapper._extract_alarm_info(
        {"alarm": {"severity": sev_key, "message": "NO_ALARM"}}
    )
    assert severity == mapped
    assert msg == ""

    severity, msg = pva_wrapper._extract_alarm_info(
        {"alarm": {"severity": sev_key, "message": "something broke"}}
    )
    assert severity == mapped
    assert msg == "something broke"


def test_extract_alarm_info_missing_fields_returns_unknown(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)
    severity, msg = pva_wrapper._extract_alarm_info({})
    assert severity == status.UNKNOWN
    assert msg == "alarm information unavailable"


def test_extract_alarm_info_unknown_severity_returns_unknown(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)
    severity, msg = pva_wrapper._extract_alarm_info(
        {"alarm": {"severity": 99999, "message": "weird"}}
    )
    assert severity == status.UNKNOWN
    assert msg == "alarm information unavailable"


def test_get_alarm_status_uses_context_get_and_extracts_alarm(
    fake_context: FakeContext,
):
    sev_key = _any_severity_key()
    fake_context.set_get_result(
        "PV:ALARM", {"alarm": {"severity": sev_key, "message": "boom"}}
    )
    pva_wrapper = P4pWrapper(timeout=3.0, context=fake_context)

    severity, msg = pva_wrapper.get_alarm_status("PV:ALARM")

    assert fake_context.get_calls == [("PV:ALARM", 3.0)]
    assert severity == SEVERITY_TO_STATUS[sev_key]
    assert msg == "boom"


def test_subscribe_registers_monitor_and_starts_disconnected(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    change = CallSpy()
    sub = pva_wrapper.subscribe("PV:X", "value", change)

    sub_id = id(sub)

    assert fake_context.monitor_calls == [
        ("PV:X", "field(value,timeStamp,alarm,control,display)", True)
    ]
    assert sub_id in pva_wrapper._sub_to_key
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(sub_id)] is False


def test_multiple_subscriptions_refcount_connect_disconnect_order(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch1 = CallSpy()
    ch2 = CallSpy()

    sub1 = pva_wrapper.subscribe("PV:A", "status", ch1, conn)
    sub2 = pva_wrapper.subscribe("PV:A", "status", ch2, conn)

    # initial disconnect injection: should not produce a "down" signal
    sub1.emit(RuntimeError("Disconnected"))
    assert conn.calls == []

    # first connection event brings the group up once
    sub1.emit(FakeUpdate({"value": 1}, {"value"}))
    assert len(conn.calls) == 1
    assert conn.calls[0][0] == ("PV:A", "status", True)

    # second subscription connects: no duplicate "up"
    sub2.emit(FakeUpdate({"value": 2}, {"value"}))
    assert len(conn.calls) == 1

    # disconnect one subscription: still connected overall
    sub1.emit(RuntimeError("net hiccup"))
    assert len(conn.calls) == 1

    # disconnect last subscription: group goes down once
    exc = RuntimeError("net down")
    sub2.emit(exc)
    assert len(conn.calls) == 2
    args, kwargs = conn.calls[1]
    assert args == ("PV:A", "status", False)
    assert "reason" in kwargs
    assert "net down" in kwargs["reason"]

    assert ("PV:A", "status") not in pva_wrapper._conn_refcnt


def test_disconnect_twice_does_not_underflow_refcount(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:B", "value", ch, conn)

    sub.emit(FakeUpdate({"value": 1}, {"value"}))
    assert pva_wrapper._conn_refcnt[("PV:B", "value")] == 1

    sub.emit(RuntimeError("drop1"))
    assert ("PV:B", "value") not in pva_wrapper._conn_refcnt

    # duplicate disconnect should be ignored and not go negative
    sub.emit(RuntimeError("drop2"))
    assert ("PV:B", "value") not in pva_wrapper._conn_refcnt
    assert len(conn.calls) == 2  # up + down


def test_cancelled_disconnect_is_suppressed_but_state_is_updated(
    fake_context: FakeContext,
):
    # This test uses the Cancelled class imported by the module under test.
    # We avoid relying on its constructor signature.
    from nicos.devices.epics.pva import p4p as p4p_mod

    def make_cancelled():
        try:
            return p4p_mod.Cancelled()
        except Exception:
            return p4p_mod.Cancelled.__new__(p4p_mod.Cancelled)

    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:C", "value", ch, conn)

    sub.emit(FakeUpdate({"value": 1}, {"value"}))
    assert len(conn.calls) == 1  # up

    sub.emit(make_cancelled())
    # no "down" callback for Cancelled
    assert len(conn.calls) == 1
    assert ("PV:C", "value") not in pva_wrapper._conn_refcnt
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(id(sub))] is False


def test_subscribe_with_no_change_callback_still_tracks_connection_state(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    sub = pva_wrapper.subscribe("PV:NOCB", "value", None, conn)

    sub.emit(FakeUpdate({"value": 7}, {"value"}))
    assert len(conn.calls) == 1
    assert conn.calls[0][0] == ("PV:NOCB", "value", True)
    assert pva_wrapper._conn_refcnt[("PV:NOCB", "value")] == 1

    sub.emit(RuntimeError("drop"))
    assert len(conn.calls) == 2
    assert conn.calls[1][0] == ("PV:NOCB", "value", False)
    assert ("PV:NOCB", "value") not in pva_wrapper._conn_refcnt


def test_alarm_only_update_without_value_uses_cached_value(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:D", "value", ch)

    # initial value
    sub.emit(FakeUpdate({"value": 10}, {"value"}))
    assert len(ch.calls) == 1
    args, _ = ch.calls[-1]
    assert args[2] == 10

    # alarm delta without "value" field should still emit using cached value
    sev_key = _any_severity_key()
    sub.emit(
        FakeUpdate(
            {"alarm": {"severity": sev_key, "message": "BOOM"}},
            {"alarm.severity"},
        )
    )
    assert len(ch.calls) == 2
    args, _ = ch.calls[-1]
    assert args[2] == 10
    assert args[5] == SEVERITY_TO_STATUS[sev_key]
    assert args[6] == "BOOM"


def test_alarm_only_update_without_cached_value_emits_nothing(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:E", "value", ch)

    sev_key = _any_severity_key()
    sub.emit(
        FakeUpdate(
            {"alarm": {"severity": sev_key, "message": "BOOM"}},
            {"alarm.severity"},
        )
    )
    assert ch.calls == []


def test_close_subscription_cleans_bookkeeping_when_connected(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:F", "value", ch, conn)

    sub.emit(FakeUpdate({"value": 1}, {"value"}))
    assert ("PV:F", "value") in pva_wrapper._conn_refcnt
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(id(sub))] is True

    pva_wrapper.close_subscription(sub)

    assert sub.closed is True
    assert pva_wrapper._sub_to_key.get(id(sub)) not in pva_wrapper._sub_connected
    assert ("PV:F", "value") not in pva_wrapper._conn_refcnt


def test_close_one_of_two_connected_subscriptions_decrements_but_keeps_connection(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch1 = CallSpy()
    ch2 = CallSpy()
    sub1 = pva_wrapper.subscribe("PV:F2", "value", ch1, conn)
    sub2 = pva_wrapper.subscribe("PV:F2", "value", ch2, conn)

    sub1.emit(FakeUpdate({"value": 1}, {"value"}))
    sub2.emit(FakeUpdate({"value": 2}, {"value"}))
    assert pva_wrapper._conn_refcnt[("PV:F2", "value")] == 2

    pva_wrapper.close_subscription(sub1)
    assert sub1.closed is True
    assert pva_wrapper._conn_refcnt[("PV:F2", "value")] == 1
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(id(sub2))] is True


def test_close_subscription_when_never_connected_does_not_touch_refcount(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:G", "value", ch)

    assert ("PV:G", "value") not in pva_wrapper._conn_refcnt
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(id(sub))] is False

    pva_wrapper.close_subscription(sub)

    assert sub.closed is True
    assert pva_wrapper._sub_to_key.get(id(sub)) not in pva_wrapper._sub_connected
    assert ("PV:G", "value") not in pva_wrapper._conn_refcnt


def test_close_subscription_without_nicos_subkey_is_safe(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    sub = FakeSubscription("PV:H", lambda *_: None)
    pva_wrapper.close_subscription(sub)

    assert sub.closed is True


def test_units_only_monitor_update_emits_callback_with_cached_value_and_new_units(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:U", "value", ch)

    # initial value and some units
    sub.emit(
        FakeUpdate(
            {"value": 1.0, "display": {"units": "mm"}},
            {"value", "display.units"},
        )
    )
    assert len(ch.calls) == 1
    args, _ = ch.calls[-1]
    assert args[2] == 1.0
    assert args[3] == "mm"

    # units change only (no 'value' in changeSet) -> should still emit using cached value
    sub.emit(
        FakeUpdate(
            {"display": {"units": "deg"}},
            {"display.units"},
        )
    )
    assert len(ch.calls) == 2
    args, _ = ch.calls[-1]
    assert args[2] == 1.0
    assert args[3] == "deg"


def test_limits_only_monitor_update_emits_callback_with_cached_value_and_new_limits(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:L", "value", ch)

    sub.emit(
        FakeUpdate(
            {"value": 2.0, "display": {"limitLow": -1.0, "limitHigh": 5.0}},
            {"value", "display.limitLow"},
        )
    )
    assert len(ch.calls) == 1
    args, _ = ch.calls[-1]
    assert args[2] == 2.0
    assert args[4] == (-1.0, 5.0)

    # limits updated only -> still emits with cached value
    sub.emit(
        FakeUpdate(
            {"display": {"limitLow": -2.0, "limitHigh": 6.0}},
            {"display.limitLow"},
        )
    )
    assert len(ch.calls) == 2
    args, _ = ch.calls[-1]
    assert args[2] == 2.0
    assert args[4] == (-2.0, 6.0)


def test_enum_monitor_update_updates_value_and_choices_cache(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:ENUM", "value", ch, conn)

    # First monitor update: placeholder/default choices
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=0, choices=["Undefined"])},
            {"value.index"},
        )
    )

    # connected should come up once
    assert len(conn.calls) == 1
    assert conn.calls[0][0] == ("PV:ENUM", "value", True)

    # change callback gets enum index (not string)
    assert len(ch.calls) == 1
    args, _ = ch.calls[-1]
    assert args[2] == 0

    # choices cache updated from monitor
    assert pva_wrapper._choices["PV:ENUM"] == ["Undefined"]

    # Second monitor update: real choices arrive
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=1, choices=["Alpha", "Beta", "Gamma"])},
            {"value.index"},
        )
    )
    assert len(ch.calls) == 2
    args, _ = ch.calls[-1]
    assert args[2] == 1
    assert pva_wrapper._choices["PV:ENUM"] == ["Alpha", "Beta", "Gamma"]


def test_enum_choices_churn_across_disconnect_and_reconnect(fake_context: FakeContext):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:MBBO", "value", ch, conn)

    # "Before restart": real choices
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=2, choices=["A", "B", "C", "D"])},
            {"value.index"},
        )
    )
    assert pva_wrapper._choices["PV:MBBO"] == ["A", "B", "C", "D"]

    # disconnect (IOC restart)
    sub.emit(RuntimeError("Disconnected"))
    assert len(conn.calls) == 2
    assert conn.calls[1][0] == ("PV:MBBO", "value", False)
    assert pva_wrapper._sub_connected[pva_wrapper._sub_to_key.get(id(sub))] is False

    # reconnect: placeholder/default choices first
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=0, choices=["Undefined"])},
            {"value.index"},
        )
    )
    # up again
    assert len(conn.calls) == 3
    assert conn.calls[2][0] == ("PV:MBBO", "value", True)
    assert pva_wrapper._choices["PV:MBBO"] == ["Undefined"]

    # later: final real choices restored/changed
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=1, choices=["Alpha", "Beta", "Gamma"])},
            {"value.index"},
        )
    )
    assert pva_wrapper._choices["PV:MBBO"] == ["Alpha", "Beta", "Gamma"]
    assert pva_wrapper._values["PV:MBBO"] == 1


def test_get_enum_as_string_uses_latest_choices_from_monitor_cache(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    # The get-path will always do a get() first.
    fake_context.set_get_result(
        "PV:ENUM", {"value": FakeEnumValue(index=1, choices=["X", "Y"])}
    )

    conn = CallSpy()
    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:ENUM", "value", ch, conn)

    # Monitor update gives the *real* choices, different from get() payload.
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=1, choices=["Alpha", "Beta", "Gamma"])},
            {"value.index"},
        )
    )
    assert pva_wrapper._choices["PV:ENUM"] == ["Alpha", "Beta", "Gamma"]

    # get_pv_value(as_string=True) should map using the cached choices
    assert pva_wrapper.get_pv_value("PV:ENUM", as_string=True) == "Beta"


@pytest.mark.xfail(
    reason=(
        "Monitor updates can deliver 'value.index' together with a refreshed choices list "
        "(eg during reconnect). Wrapper currently converts using stale cached choices before "
        "updating the cache from the incoming value, producing wrong enum string."
    )
)
def test_enum_monitor_as_string_uses_new_choices_when_choices_and_index_change_together(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    # Simulate stale choices cache from a previous connection:
    # index=1 used to mean "Gamma" (['Beta','Gamma'] -> 1 == 'Gamma')
    pva_wrapper._choices["PV:ENUM"] = ["Beta", "Gamma"]
    pva_wrapper._values["PV:ENUM"] = 1

    ch = CallSpy()
    # Important: as_string=True means _convert_value() will map index->string.
    sub = pva_wrapper.subscribe("PV:ENUM", "value", ch, as_string=True)

    # Reconnect/update delivers a refreshed choices list and an index in the same delta:
    # new mapping: ['Alpha','Beta','Gamma'] -> index 1 == 'Beta'
    sub.emit(
        FakeUpdate(
            {"value": FakeEnumValue(index=1, choices=["Alpha", "Beta", "Gamma"])},
            {"value.index"},
        )
    )

    # Desired behavior: callback uses *new* choices from this update, not stale cache.
    assert len(ch.calls) == 1
    args, _ = ch.calls[0]
    assert args[0] == "PV:ENUM"
    assert args[1] == "value"
    assert args[2] == "Beta"

    # Cache should be updated to the new choices as well.
    assert pva_wrapper._choices["PV:ENUM"] == ["Alpha", "Beta", "Gamma"]


@pytest.mark.xfail(
    reason=(
        "Gets can deliver 'value.index' together with a refreshed choices list. "
        "Wrapper currently converts using stale cached choices before "
        "updating the cache from the incoming value, producing wrong enum string."
    )
)
def test_get_enum_as_string_uses_new_choices_when_choices_and_index_change_together(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    # Simulate stale choices cache from a previous connection:
    # index=1 used to mean "Gamma" (['Beta','Gamma'] -> 1 == 'Gamma')
    pva_wrapper._choices["PV:ENUM"] = ["Beta", "Gamma"]
    pva_wrapper._values["PV:ENUM"] = 1

    # Simulate get() returning an index with a refreshed choices list:
    # new mapping: ['Alpha','Beta','Gamma'] -> index 1 == 'Beta'
    fake_context.set_get_result(
        "PV:ENUM", {"value": FakeEnumValue(index=1, choices=["Alpha", "Beta", "Gamma"])}
    )

    assert pva_wrapper.get_pv_value("PV:ENUM", as_string=True) == "Beta"
    assert pva_wrapper._choices["PV:ENUM"] == ["Alpha", "Beta", "Gamma"]


@pytest.mark.xfail(
    reason="Wrapper only refreshes limits on 'display.limitLow' delta; should also handle 'display.limitHigh'."
)
def test_limits_high_only_monitor_update_emits_callback_with_cached_value_and_new_limits(
    fake_context: FakeContext,
):
    pva_wrapper = P4pWrapper(timeout=1.0, context=fake_context)

    ch = CallSpy()
    sub = pva_wrapper.subscribe("PV:LHI", "value", ch)

    # initial value + full limits (delta indicates limitLow changed)
    sub.emit(
        FakeUpdate(
            {"value": 2.0, "display": {"limitLow": -1.0, "limitHigh": 5.0}},
            {"value", "display.limitLow"},
        )
    )
    assert len(ch.calls) == 1
    args, _ = ch.calls[-1]
    assert args[2] == 2.0
    assert args[4] == (-1.0, 5.0)

    # Now only limitHigh changes; wrapper should refresh limits and still emit using cached value.
    sub.emit(
        FakeUpdate(
            {"display": {"limitHigh": 6.0}},
            {"display.limitHigh"},
        )
    )

    assert len(ch.calls) == 2
    args, _ = ch.calls[-1]
    assert args[2] == 2.0
    assert args[4] == (-1.0, 6.0)

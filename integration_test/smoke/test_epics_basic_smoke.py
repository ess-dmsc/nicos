"""Integration smoke tests for the minimal EPICS setup."""

from __future__ import annotations

import time


def _wait_for_device(smoke_client, device_name: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        exists = smoke_client.eval(f"{device_name!r} in session.devices", default=False)
        if exists:
            return
        time.sleep(0.1)
    raise AssertionError(
        f"device did not become available after setup reload: {device_name}"
    )


def _wait_for_moveable_readback(
    smoke_client, target: float, timeout: float = 15.0
) -> float:
    deadline = time.monotonic() + timeout
    value = float(smoke_client.eval("SmokeBasicMoveable.read(0)"))
    while time.monotonic() < deadline:
        value = float(smoke_client.eval("SmokeBasicMoveable.read(0)"))
        if abs(value - target) <= 0.05:
            return value
        time.sleep(0.1)
    pv_val = smoke_client.eval(
        "SmokeBasicMoveable._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.VAL')",
        default=None,
    )
    pv_rbv = smoke_client.eval(
        "SmokeBasicMoveable._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.RBV')",
        default=None,
    )
    raise AssertionError(
        "readback did not reach target in time: "
        f"final={value} target={target} pv_val={pv_val} pv_rbv={pv_rbv}"
    )


def test_epics_basic_setup_devices_support_read_and_status(smoke_client) -> None:
    """NewSetup, then verify setup devices can status/read without errors."""
    smoke_client.execute("NewSetup('epics_basic')", timeout=90)
    _wait_for_device(smoke_client, "SmokeBasicMoveable", timeout=30)
    _wait_for_device(smoke_client, "SmokeBasicReadable", timeout=30)

    setup_devices = smoke_client.eval(
        "sorted(session._setup_info['epics_basic']['devices'])"
    )
    assert setup_devices == ["SmokeBasicMoveable", "SmokeBasicReadable"]

    for devname in setup_devices:
        smoke_client.eval(f"session.getDevice({devname!r}).status(0)")
        smoke_client.eval(f"session.getDevice({devname!r}).read(0)")


def test_epics_basic_move_and_readback_change(smoke_client) -> None:
    """NewSetup, read start, move, then read final and assert it changed."""
    smoke_client.execute("NewSetup('epics_basic')", timeout=90)
    _wait_for_device(smoke_client, "SmokeBasicMoveable", timeout=30)

    start = float(smoke_client.eval("SmokeBasicMoveable.read(0)"))
    target = 6.0 if abs(start - 6.0) > 0.05 else 7.0

    smoke_client.execute(f"move('SmokeBasicMoveable', {target!r})", timeout=30)

    end = _wait_for_moveable_readback(smoke_client, target)
    assert abs(end - target) <= 0.05
    assert abs(end - start) > 0.05

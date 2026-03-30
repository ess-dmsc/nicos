"""Small reusable helpers for harness-based ESS device tests."""

import time


def wait_until_complete(device, timeout=2.0, poll_interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if device.isCompleted():
            return
        time.sleep(poll_interval)
    raise AssertionError(f"{device.name} did not complete within {timeout} seconds")


def wait_for(predicate, timeout=2.0, poll_interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(poll_interval)
    raise AssertionError("Condition not met within timeout")

"""Small helpers shared by command-level ESS tests.

These wrappers keep the command tests focused on `count()` and `scan()`
behaviour instead of repeating session boilerplate in every module.
"""

import time
from contextlib import contextmanager


@contextmanager
def loaded_setup(session, name):
    """Load a temporary setup for one test and always unload it afterwards."""
    session.loadSetup(name)
    try:
        yield
    finally:
        session.unloadSetup()


def set_detectors(session, *names):
    """Resolve detector names in the current setup and make them active."""
    session.experiment.setDetectors([session.getDevice(name) for name in names])


def wait_until(predicate, timeout=2.0):
    """Poll until *predicate* becomes true or the timeout expires.

    The short sleep keeps asynchronous tests deterministic without needing
    arbitrary long `sleep()` calls in the test bodies.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def scan_positions(dataset):
    """Extract the x-axis values from a NICOS scan dataset.

    Command tests use this to assert which scan points were actually recorded
    without caring about the rest of the dataset internals.
    """
    return [point[dataset.xindex] for point in dataset.devvaluelists]

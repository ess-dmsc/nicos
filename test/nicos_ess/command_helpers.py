import time
from contextlib import contextmanager


@contextmanager
def loaded_setup(session, name):
    session.loadSetup(name)
    try:
        yield
    finally:
        session.unloadSetup()


def set_detectors(session, *names):
    session.experiment.setDetectors([session.getDevice(name) for name in names])


def wait_until(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def scan_positions(dataset):
    return [point[dataset.xindex] for point in dataset.devvaluelists]

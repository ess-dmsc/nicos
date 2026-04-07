import time
from contextlib import contextmanager


class _DeliveredMessage:
    def partition(self):
        return 0

    def offset(self):
        return 0


class _KafkaRecord:
    def __init__(self, payload):
        self._payload = payload

    def value(self):
        return self._payload


class RecordingKafkaProducer:
    def __init__(self):
        self.messages = []

    def produce(self, topic, message, **kwargs):
        self.messages.append(
            {
                "topic": topic,
                "message": message,
                "key": kwargs.get("key"),
            }
        )
        callback = kwargs.get("on_delivery_callback")
        if callback:
            callback(None, _DeliveredMessage())


@contextmanager
def loaded_setup(session, name):
    session.loadSetup(name)
    try:
        yield
    finally:
        session.unloadSetup()


def _wait_until(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _set_detectors(session, *names):
    session.experiment.setDetectors([session.getDevice(name) for name in names])

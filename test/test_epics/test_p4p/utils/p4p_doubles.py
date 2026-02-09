from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional


class CallSpy:
    def __init__(self):
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeSubscription:
    def __init__(self, pvname: str, callback):
        self.pvname = pvname
        self._callback = callback
        self.closed = False

    def emit(self, result):
        self._callback(result)

    def close(self):
        self.closed = True


class FakeContext:
    def __init__(self):
        self._get_results: dict[str, object] = {}
        self.get_calls: list[tuple[str, Optional[float]]] = []
        self.put_calls = []  # list of (pvname, value, timeout, wait, process)
        self.monitor_calls: list[tuple[str, Optional[str], Optional[bool]]] = []
        self._subscriptions: list[FakeSubscription] = []

    def set_get_result(self, pvname: str, result: object):
        self._get_results[pvname] = result

    def get(self, pvname: str, timeout=None):
        self.get_calls.append((pvname, timeout))
        result = self._get_results.get(pvname, {})
        if isinstance(result, Exception):
            raise result
        return result

    def put(self, pvname: str, value, timeout=None, wait=None, process=None):
        self.put_calls.append((pvname, value, timeout, wait, process))

    def monitor(self, pvname: str, callback, request=None, notify_disconnect=None):
        self.monitor_calls.append((pvname, request, notify_disconnect))
        sub = FakeSubscription(pvname, callback)
        self._subscriptions.append(sub)
        return sub


class FakeEnumValue:
    def __init__(self, index: int, choices: list[str]):
        self._data = {"index": index, "choices": choices}

    def getID(self) -> str:
        return "enum_t"

    def __getitem__(self, key: str):
        return self._data[key]

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)


@dataclass(frozen=True)
class FakeUpdate:
    data: dict
    changed: set[str]

    def changedSet(self) -> set[str]:
        return set(self.changed)

    def __getitem__(self, key: str):
        return self.data[key]


class EventSink:
    def __init__(self):
        self._evt = threading.Event()
        self._lock = threading.Lock()
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs):
        with self._lock:
            self.calls.append((args, kwargs))
        self._evt.set()

    def wait_calls(self, n: int, *, timeout: float = 5.0) -> None:
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                if len(self.calls) >= n:
                    return
            self._evt.wait(timeout=0.1)
            self._evt.clear()
        raise AssertionError(f"timeout waiting for {n} calls, got {len(self.calls)}")

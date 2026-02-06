import queue
import threading
import time
from collections import deque
from threading import Lock

from streaming_data_types.alarm_al00 import Severity, serialise_al00
from streaming_data_types.logdata_f144 import serialise_f144

from nicos.core import Device, Override, Param, host, listof, status
from nicos.protocols.cache import OP_TELL, cache_load
from nicos.services.collector import ForwarderBase
from nicos.utils import createThread
from nicos_ess.devices.kafka.producer import KafkaProducer

nicos_status_to_al00 = {
    status.OK: Severity.OK,
    status.WARN: Severity.MINOR,
    status.ERROR: Severity.MAJOR,
    status.UNKNOWN: Severity.INVALID,
}


def convert_status(nicos_status):
    """Convert the NICOS status into the corresponding al00 schema severity.

    Policy decision: treat everything that is not WARN or ERROR as OK.

    :param nicos_status: the NICOS status
    :return: the al00 schema severity
    """
    severity, msg = cache_load(nicos_status)
    return nicos_status_to_al00.get(severity, Severity.OK), msg


def to_f144(dev_name, dev_value, timestamp_ns):
    """Convert the device information into an f144 FlatBuffer.

    :param dev_name: the device name
    :param dev_value: the device's value
    :param timestamp_ns: the associated timestamp in nanoseconds
    :return: FlatBuffer representation of data
    """
    return serialise_f144(dev_name, dev_value, timestamp_ns)


class CacheKafkaForwarder(ForwarderBase, Device):
    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "output_topic": Param(
            "The topic to send data to",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "dev_ignore": Param(
            "Devices to ignore; if empty, all devices are accepted",
            default=[],
            type=listof(str),
        ),
        "update_interval": Param(
            "Time interval (in secs.) to send regular updates",
            default=10.0,
            type=float,
            settable=False,
        ),
    }
    parameter_overrides = {
        # Key filters are irrelevant for this collector
        "keyfilters": Override(default=[], settable=False),
    }

    def doInit(self, mode):
        self._dev_to_value_cache = {}
        self._dev_to_status_cache = {}
        self._producer = None
        self._lock = Lock()

        self._per_dev_max = 100  #  per-device backlog cap

        self._buffers = {}  # (name, is_value) -> deque[(value, timestamp)]
        self._active = deque()  # round-robin of keys that currently have buffered items
        self._active_set = (
            set()
        )  # membership guard so we don't enqueue same key many times
        self._buf_lock = Lock()
        self._has_data = threading.Event()

        self._dropped_total = 0
        self._last_drop_log = 0.0

        self._initFilters()
        self._worker = createThread("cache_to_kafka", self._processQueue, start=False)
        self._regular_update_worker = createThread(
            "send_regular_updates", self._poll_updates, start=False
        )
        while not self._producer:
            try:
                self._producer = KafkaProducer.create(self.brokers)
            except Exception as error:
                self.log.error(
                    "Could not connect to Kafka - will try again soon: %s", error
                )
                time.sleep(5)
        self.log.info("Connected to Kafka brokers %s", self.brokers)

    def _startWorker(self):
        self._worker.start()
        self._regular_update_worker.start()

    def _poll_updates(self):
        while True:
            with self._lock:
                for name, (value, timestamp) in self._dev_to_value_cache.items():
                    self._push_to_queue(name, value, timestamp, True)
                for name, (value, timestamp) in self._dev_to_status_cache.items():
                    self._push_to_queue(name, value, timestamp, False)

            time.sleep(self.update_interval)

    def _checkKey(self, key):
        if key.endswith("/value") or key.endswith("/status"):
            return True
        return False

    def _checkDevice(self, name):
        if name not in self.dev_ignore:
            return True
        return False

    def _putChange(self, timestamp, ttl, key, op, value):
        if value is None or op != OP_TELL:
            return
        dev_name = key[0 : key.index("/")]
        if not self._checkKey(key) or not self._checkDevice(dev_name):
            return
        self.log.debug("_putChange %s %s %s", key, value, timestamp)

        with self._lock:
            timestamp_ns = int(float(timestamp) * 10**9)
            if key.endswith("value"):
                self._dev_to_value_cache[dev_name] = (value, timestamp_ns)
                self._push_to_queue(dev_name, value, timestamp_ns, True)
            else:
                self._dev_to_status_cache[dev_name] = (
                    convert_status(value),
                    timestamp_ns,
                )
                self._push_to_queue(
                    dev_name, *self._dev_to_status_cache[dev_name], False
                )

    def _push_to_queue(self, dev_name, value, timestamp, is_value):
        key = (dev_name, is_value)

        with self._buf_lock:
            dq = self._buffers.get(key)
            if dq is None:
                dq = deque(maxlen=self._per_dev_max)
                self._buffers[key] = dq

            # detect per-device drop (deque(maxlen) auto-drops from the left)
            if len(dq) == dq.maxlen:
                self._dropped_total += 1
                now = time.monotonic()
                if now - self._last_drop_log > 1.0:
                    # rate-limit log spam
                    self.log.error(
                        "Per-device backlog full; dropping oldest updates (total dropped so far=%d)",
                        self._dropped_total,
                    )
                    self._last_drop_log = now

            dq.append((value, timestamp))

            # schedule this device/type for draining (only once)
            if key not in self._active_set:
                self._active.append(key)
                self._active_set.add(key)

        self._has_data.set()

    def _processQueue(self):
        last_flush = time.monotonic()

        while True:
            # Wait until there is something to do (or wake periodically for flush)
            self._has_data.wait(timeout=0.1)

            # Pop one item fairly (round-robin across device/type)
            with self._buf_lock:
                if not self._active:
                    self._has_data.clear()
                    item = None
                else:
                    key = self._active.popleft()
                    dq = self._buffers.get(key)

                    if not dq:
                        # should be rare, but keep structures consistent
                        self._active_set.discard(key)
                        item = None
                    else:
                        value, timestamp = dq.popleft()
                        name, is_value = key

                        # If more pending for this key, re-append to end (fairness)
                        if dq:
                            self._active.append(key)
                        else:
                            self._active_set.discard(key)
                            # optional: free empty deque to avoid unbounded dict growth
                            del self._buffers[key]

                        item = (name, value, timestamp, is_value)

            if item is None:
                # still do periodic flush
                now = time.monotonic()
                if now - last_flush >= 1.0:
                    remaining = self._producer.flush(0.2)
                    if remaining:
                        self.log.warning(
                            "Kafka flush timeout; %d msgs still pending", remaining
                        )
                    last_flush = now
                continue

            name, value, timestamp, is_value = item

            try:
                if is_value:
                    value = cache_load(value)
                    if isinstance(value, bool):
                        value = int(value)
                    if not isinstance(value, str):
                        buffer = to_f144(name, value, timestamp)
                        self._send_to_kafka(buffer, name)
                else:
                    buffer = serialise_al00(name, timestamp, value[0], value[1])
                    self._send_to_kafka(buffer, name)
            except Exception as error:
                self.log.error("Could not forward data: %s", error)

            now = time.monotonic()
            if now - last_flush >= 1.0:
                remaining = self._producer.flush(0.2)
                if remaining:
                    self.log.warning(
                        "Kafka flush timeout; %d msgs still pending", remaining
                    )
                last_flush = now

    def _send_to_kafka(self, buffer, name):
        try:
            self._producer.produce(
                self.output_topic,
                buffer,
                key=name.encode("utf-8"),
                auto_flush=False,
            )
        except BufferError:
            # Internal librdkafka queue is full: we are overloaded or Kafka is slow/unavailable.
            # Since the policy is "latest wins", dropping here is acceptable and avoids wedging.
            self.log.warning("Kafka internal queue full; dropping message for %s", name)

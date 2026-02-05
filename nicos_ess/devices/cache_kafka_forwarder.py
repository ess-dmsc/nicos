import queue
import time
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
        "kafka_backoff_initial": Param(
            "Initial backoff (in secs.) when kafka delivery fails",
            default=1.0,
            type=float,
            settable=False,
        ),
        "max_kafka_backoff": Param(
            "Maximum backoff (in secs.) when kafka delivery keeps failing",
            default=60.0,
            type=float,
            settable=False,
        ),
        "kafka_log_throttle": Param(
            "Minimum time (in secs.) between repeated kafka/queue error logs",
            default=60.0,
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
        self._producer_lock = Lock()

        now = time.monotonic()
        self._last_delivered_ts = now
        self._kafka_down_until = 0.0
        self._kafka_backoff = self.kafka_backoff_initial

        self._queue_full_dropped = 0
        self._queue_full_next_log = 0.0
        self._kafka_err_next_log = 0.0

        self._initFilters()
        self._queue = queue.Queue(1000)
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

    def _maybe_log_queue_full(self, now):
        if now < self._queue_full_next_log:
            return
        if self._queue_full_dropped:
            self.log.warning(
                "Kafka queue full; dropped %d message(s) in the last %.0f seconds",
                self._queue_full_dropped,
                self.kafka_log_throttle,
            )
            self._queue_full_dropped = 0
        self._queue_full_next_log = now + self.kafka_log_throttle

    def _set_kafka_down(self, now, error):
        if now >= self._kafka_err_next_log:
            self.log.error(
                "Kafka send failed; dropping for %.1fs (backoff). Last error: %s",
                self._kafka_backoff,
                error,
            )
            self._kafka_err_next_log = now + self.kafka_log_throttle

        self._kafka_down_until = now + self._kafka_backoff
        self._kafka_backoff = min(self._kafka_backoff * 2.0, self.max_kafka_backoff)

    def _kafka_is_down(self, now):
        return now < self._kafka_down_until

    def _push_to_queue(self, dev_name, value, timestamp, is_value):
        now = time.monotonic()
        if self._kafka_is_down(now):
            # Kafka is unhealthy; don't enqueue. Caches keep latest values.
            return

        try:
            self._queue.put_nowait((dev_name, value, timestamp, is_value))
            return
        except queue.Full:
            pass

        if not self._worker.is_alive():
            self.log.error("Kafka forwarding worker thread has stopped!")
            return

        # Drop oldest and attempt once more (non-blocking, readable, race-safe enough).
        try:
            self._queue.get_nowait()
        except queue.Empty:
            self._queue_full_dropped += 1
            self._maybe_log_queue_full(now)
            return
        else:
            self._queue.task_done()

        try:
            self._queue.put_nowait((dev_name, value, timestamp, is_value))
        except queue.Full:
            # Still full: drop this update too.
            self._queue_full_dropped += 2
        else:
            self._queue_full_dropped += 1

        self._maybe_log_queue_full(now)

    def _processQueue(self):
        while True:
            name, value, timestamp, is_value = self._queue.get()
            try:
                now = time.monotonic()
                if self._kafka_is_down(now):
                    # Discard backlog while Kafka is down to prevent permanent queue-full.
                    continue

                if is_value:
                    # Convert value from string representation to correct type
                    value = cache_load(value)
                    if isinstance(value, bool):
                        # Convert to 1 or 0
                        value = int(value)
                    if not isinstance(value, str):
                        # Policy decision: don't send strings via f144
                        buffer = to_f144(name, value, timestamp)
                        self._send_to_kafka(buffer, name)
                else:
                    buffer = serialise_al00(name, timestamp, value[0], value[1])
                    self._send_to_kafka(buffer, name)

            except Exception as error:
                self._set_kafka_down(time.monotonic(), error)
            finally:
                self._queue.task_done()

    def _send_to_kafka(self, buffer, name):
        def on_delivery(err, msg):
            now = time.monotonic()
            if err:
                if now >= self._kafka_err_next_log:
                    self.log.error("Failed to deliver message for %s: %s", name, err)
                    self._kafka_err_next_log = now + self.kafka_log_throttle
            else:
                self._last_delivered_ts = now
                self._kafka_backoff = self.kafka_backoff_initial
                self._kafka_down_until = 0.0

        with self._producer_lock:
            producer = self._producer

        producer.produce(
            self.output_topic,
            buffer,
            key=name.encode("utf-8"),
            on_delivery_callback=on_delivery,
        )

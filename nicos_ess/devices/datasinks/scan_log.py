"""Publish scan and point boundaries to Kafka for the NeXus file."""

import threading
from time import time as currenttime

from streaming_data_types.logdata_f144 import serialise_f144

from nicos import session
from nicos.core import POLLER, Override, Param, floatrange, host, listof
from nicos.core.constants import POINT, SCAN, SIMULATION
from nicos.core.data import DataSink, DataSinkHandler
from nicos.utils import createThread
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.utilities.json_utils import generate_nxlog_json


class ScanLogSinkHandler(DataSinkHandler):
    def prepare(self):
        self.manager.assignCounter(self.dataset)
        self._started = False

    def begin(self):
        if self.dataset.settype == SCAN:
            self._start(self.dataset.started)

    def putMetainfo(self, metainfo):
        # NICOS collects the metainfo right before it starts the detectors.
        if self.dataset.settype == POINT:
            self._start(currenttime())

    def end(self):
        # A point that never counted is logged when it ends.
        self._start(self.dataset.started)
        self.sink._set(self.dataset.settype, 0, self.dataset.finished)

    def _start(self, timestamp):
        if not self._started:
            self._started = True
            self.sink._set(self.dataset.settype, self.dataset.counter, timestamp)


class ScanLogSink(DataSink):
    """Log the scan and point numbers as f144 step functions.

    The NeXus file gets ``/entry/scan_log`` with the NXlogs ``scan`` and
    ``point``. Each holds the global NICOS counter (as in the counters file)
    while the scan runs or the point counts, and 0 otherwise. A point outside
    a scan, such as from ``count()``, is logged with the scan at 0.

    A scan is logged when it begins and ends; a point when its detectors
    start and when it ends. Like the forwarder, the sink repeats the current
    numbers every ``update_interval`` seconds, so that a file started in the
    middle of a scan has them from its start.

    Reading the file: a value holds from its time until the next row. Point
    ``n`` counted from the first row with ``n`` to the first later row with
    another value (``0``); repeated rows of the same value change nothing.
    The scan of a point is the scan log's value at the point's start.
    """

    parameters = {
        "brokers": Param(
            "List of Kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "topic": Param(
            "Kafka topic to publish the scan and point numbers to",
            type=str,
            mandatory=True,
            userparam=False,
        ),
        "update_interval": Param(
            "Seconds between repeats of the current numbers (0: none)",
            type=floatrange(0),
            default=10.0,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "settypes": Override(default=[SCAN, POINT]),
    }

    handlerclass = ScanLogSinkHandler

    def doInit(self, mode):
        self._producer = None
        self._lock = threading.Lock()
        self._values = {SCAN: 0, POINT: 0}
        self._prev_values = {}
        self._last_ns = {SCAN: 0, POINT: 0}
        self._stopping = threading.Event()
        self._thread = None
        self._failing = False
        # Pollers create the sinks of the system setup too.
        if mode != SIMULATION and session.sessiontype != POLLER:
            self._producer = KafkaProducer.create(self.brokers)
            self._publish_current()
            if self.update_interval:
                self._thread = createThread(f"{self.name} repeater", self._repeat)

    def doShutdown(self):
        self._stopping.set()
        if self._thread:
            self._thread.join(2)
        if self._producer:
            self._producer.flush(5)

    def createHandlers(self, dataset):
        # One handler per dataset, not one per detector.
        return [self.handlerclass(self, dataset, None)]

    def _source_name(self, settype):
        return f"{self.name.lower()}/{settype}"

    def _set(self, settype, number, timestamp):
        with self._lock:
            self._values[settype] = number
            self._publish(settype, number, timestamp)

    def _repeat(self):
        while not self._stopping.wait(self.update_interval):
            self._publish_current()

    def _publish_current(self):
        with self._lock:
            now = currenttime()
            for settype, number in self._values.items():
                self._publish(settype, number, now)

    def _publish(self, settype, number, timestamp):
        """Send one value; its time never goes back from the last one sent."""
        if self._producer is None:
            return
        if number == self._prev_values.get(settype):
            return
        self._prev_values[settype] = number

        source = self._source_name(settype)
        timestamp_ns = max(int(timestamp * 1e9), self._last_ns[settype])
        self._last_ns[settype] = timestamp_ns
        try:
            self._producer.produce(
                self.topic,
                serialise_f144(source, number, timestamp_ns),
                on_delivery_callback=self._on_delivery,
                auto_flush=False,
            )
        except Exception as err:
            self._failed(err)

    def _on_delivery(self, err, message):
        if err:
            self._failed(err)
        elif self._failing:
            self._failing = False
            self.log.info("publishing to %s again", self.topic)

    def _failed(self, err):
        """Warn once until a message gets through again."""
        if not self._failing:
            self._failing = True
            self.log.warning("could not publish to %s: %s", self.topic, err)
        else:
            self.log.debug("could not publish to %s: %s", self.topic, err)

    def nexus_logs(self):
        """Return the NXlog nodes of the scan and point numbers."""
        return [
            generate_nxlog_json(
                settype, "f144", self._source_name(settype), self.topic, "", "int64"
            )
            for settype in (SCAN, POINT)
        ]

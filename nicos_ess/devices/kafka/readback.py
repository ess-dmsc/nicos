from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from functools import partial
from time import time as currenttime
from typing import Any, Callable, Dict, List, Optional, Tuple

from streaming_data_types import DESERIALISERS
from streaming_data_types.alarm_al00 import Severity
from streaming_data_types.epics_connection_ep01 import ConnectionInfo
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    Device,
    Override,
    Param,
    Readable,
    host,
    nonemptylistof,
    nonemptystring,
    status,
)
from nicos.core.errors import CommunicationError, ConfigurationError
from nicos_ess.devices.kafka.consumer import KafkaSubscriber

KafkaKey = Tuple[str, str]


@dataclass
class KafkaReadbackState:
    topic: str
    source_name: str
    has_value: bool = False
    value: Any = None
    value_timestamp_ns: int = 0
    alarm: Optional[Severity] = None
    alarm_message: str = ""
    alarm_timestamp_ns: int = 0
    connection: Optional[ConnectionInfo] = None
    connection_service: str = ""
    connection_timestamp_ns: int = 0


class KafkaReadbackConsumer(Device):
    """Shared Kafka input device for scalar NICOS readbacks.

    The device owns Kafka I/O and keeps the latest decoded state in memory. It
    deliberately does not publish readback values or statuses; those belong to
    the attached ``KafkaReadable`` devices.
    """

    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=nonemptylistof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "topics": Param(
            "Kafka topics to consume",
            type=nonemptylistof(nonemptystring),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
    }

    _schema_handlers: Dict[str, Callable[[KafkaReadbackState, Any], None]] = {}

    def doPreinit(self, mode):
        self._kafka_subscribers = {}
        self._latest: Dict[KafkaKey, KafkaReadbackState] = {}
        self._callbacks: Dict[KafkaKey, List[Callable[[KafkaReadbackState], None]]] = {}
        self._lock = threading.RLock()

        if mode == SIMULATION or session.sessiontype == POLLER:
            return

        for topic in self.topics:
            self._start_topic_subscriber(topic)

    def register(self, topic, source_name, callback):
        topic = str(topic)
        source_name = str(source_name)
        if topic not in self.topics:
            raise ConfigurationError(
                self,
                "topic %r is not configured on %s" % (topic, self.name),
            )

        key = (topic, source_name)
        with self._lock:
            callbacks = self._callbacks.setdefault(key, [])
            if callback not in callbacks:
                callbacks.append(callback)
            snapshot = self._snapshot_locked(key)

        if snapshot is not None:
            callback(snapshot)

    def unregister(self, topic, source_name, callback):
        key = (str(topic), str(source_name))
        with self._lock:
            callbacks = self._callbacks.get(key)
            if not callbacks:
                return
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks:
                del self._callbacks[key]

    def latest(self, topic, source_name):
        with self._lock:
            return self._snapshot_locked((str(topic), str(source_name)))

    def _start_topic_subscriber(self, topic):
        subscriber = KafkaSubscriber(self.brokers)
        subscriber.subscribe([topic], partial(self._messages_callback, topic))
        self._kafka_subscribers[topic] = subscriber

    def _messages_callback(self, topic, messages):
        for _timestamp, raw in messages:
            self._handle_kafka_payload(topic, raw)

    def _handle_kafka_payload(self, topic, raw):
        try:
            schema = get_schema(raw)
            decoder = DESERIALISERS.get(schema)
            handler = self._schema_handlers.get(schema)
            if decoder is None or handler is None:
                return
            decoded = decoder(raw)
            source_name = self._source_name(schema, decoded)
            if not source_name:
                return
        except Exception as err:
            self.log.warning("Could not decode Kafka readback message: %s", err)
            return

        key = (topic, source_name)
        with self._lock:
            state = self._latest.get(key)
            if state is None:
                state = KafkaReadbackState(topic=topic, source_name=source_name)
                self._latest[key] = state
            handler(state, decoded)
            snapshot = self._snapshot_from_state(state)
            callbacks = list(self._callbacks.get(key, ()))

        for callback in callbacks:
            try:
                callback(snapshot)
            except Exception:
                self.log.warning(
                    "Kafka readback callback failed for %s/%s",
                    topic,
                    source_name,
                    exc=True,
                )

    def _snapshot_locked(self, key):
        state = self._latest.get(key)
        if state is None:
            return None
        return self._snapshot_from_state(state)

    @staticmethod
    def _snapshot_from_state(state):
        return replace(state)

    @staticmethod
    def _source_name(schema, decoded):
        if schema == "al00":
            return decoded.source
        return getattr(decoded, "source_name", "")

    @staticmethod
    def _handle_f144(state, decoded):
        state.has_value = True
        state.value = decoded.value
        state.value_timestamp_ns = int(decoded.timestamp_unix_ns or 0)

    @staticmethod
    def _handle_al00(state, decoded):
        state.alarm = decoded.severity
        state.alarm_message = decoded.message
        state.alarm_timestamp_ns = int(decoded.timestamp_ns or 0)

    @staticmethod
    def _handle_ep01(state, decoded):
        state.connection = decoded.status
        state.connection_service = decoded.service_id or ""
        state.connection_timestamp_ns = int(decoded.timestamp or 0)

    def doShutdown(self):
        for subscriber in self._kafka_subscribers.values():
            subscriber.close()


KafkaReadbackConsumer._schema_handlers = {
    "f144": KafkaReadbackConsumer._handle_f144,
    "al00": KafkaReadbackConsumer._handle_al00,
    "ep01": KafkaReadbackConsumer._handle_ep01,
}


class KafkaReadable(Readable):
    """NICOS readback backed by a shared ``KafkaReadbackConsumer``."""

    attached_devices = {
        "kafka": Attach("Shared Kafka readback consumer", KafkaReadbackConsumer),
    }

    parameters = {
        "topic": Param(
            "Kafka topic for this readback source",
            type=nonemptystring,
            mandatory=True,
            preinit=True,
            settable=False,
            userparam=False,
        ),
        "source_name": Param(
            "Kafka source name for this readback",
            type=nonemptystring,
            mandatory=True,
            preinit=True,
            settable=False,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, default=""),
        "maxage": Override(default=None, userparam=False),
        "pollinterval": Override(default=None, settable=False, userparam=False),
    }

    hardware_access = False

    def doPreinit(self, mode):
        self._registered = False

    def doInit(self, mode):
        if mode == SIMULATION or session.sessiontype == POLLER:
            return
        self._attached_kafka.register(
            self.topic, self.source_name, self._receive_kafka_update
        )
        self._registered = True

    def doShutdown(self):
        if self._registered:
            self._attached_kafka.unregister(
                self.topic, self.source_name, self._receive_kafka_update
            )
            self._registered = False

    def doRead(self, maxage=None):
        snapshot = self._attached_kafka.latest(self.topic, self.source_name)
        if snapshot is None or not snapshot.has_value:
            raise CommunicationError(
                self,
                "Could not read value from Kafka source %r/%r"
                % (self.topic, self.source_name),
            )
        return snapshot.value

    def doStatus(self, maxage=None):
        snapshot = self._attached_kafka.latest(self.topic, self.source_name)
        current_status = self._status_from_snapshot(snapshot) if snapshot else None
        if current_status is None:
            return status.UNKNOWN, "No status information"
        return current_status

    def _receive_kafka_update(self, snapshot):
        if snapshot.has_value:
            self._cache.put(
                self,
                "value",
                snapshot.value,
                self._cache_timestamp(snapshot.value_timestamp_ns),
            )

        current_status = self._status_from_snapshot(snapshot)
        if current_status is not None:
            self._cache.put(
                self,
                "status",
                current_status,
                self._cache_timestamp(
                    self._status_timestamp_ns_from_snapshot(snapshot)
                ),
            )

    def _status_from_snapshot(self, snapshot):
        parts = []
        if snapshot.alarm is not None:
            parts.append(self._alarm_status(snapshot.alarm, snapshot.alarm_message))
        if snapshot.connection is not None:
            parts.append(
                self._connection_status(
                    snapshot.connection, snapshot.connection_service
                )
            )
        if not parts:
            return None
        return max(parts, key=lambda item: item[0])

    @staticmethod
    def _status_timestamp_ns_from_snapshot(snapshot):
        return max(snapshot.alarm_timestamp_ns, snapshot.connection_timestamp_ns)

    @staticmethod
    def _cache_timestamp(timestamp_ns):
        if timestamp_ns:
            return timestamp_ns / 1_000_000_000
        return currenttime()

    @staticmethod
    def _alarm_status(severity, message):
        if severity == Severity.OK:
            return status.OK, message or ""
        if severity == Severity.MINOR:
            return status.WARN, message or "Kafka alarm severity MINOR"
        if severity in (Severity.MAJOR, Severity.INVALID):
            return status.ERROR, message or f"Kafka alarm severity {severity.name}"
        return status.UNKNOWN, message or f"Kafka alarm severity {severity}"

    @staticmethod
    def _connection_status(connection, service):
        suffix = f" ({service})" if service else ""
        if connection == ConnectionInfo.CONNECTED:
            return status.OK, ""
        if connection in (ConnectionInfo.UNKNOWN, ConnectionInfo.NEVER_CONNECTED):
            return status.UNKNOWN, f"Kafka source {connection.name.lower()}{suffix}"
        return status.ERROR, f"Kafka source {connection.name.lower()}{suffix}"

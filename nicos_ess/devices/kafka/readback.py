from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from enum import Enum
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
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber

KafkaKey = Tuple[str, str]


class KafkaReadbackError(Enum):
    """Kafka subscriber error categories surfaced to readables."""

    BROKERS_DOWN = "brokers_down"
    OFFSET_OUT_OF_RANGE = "offset_out_of_range"
    UNKNOWN_TOPIC = "unknown_topic"
    OTHER = "other"


@dataclass
class KafkaReadbackState:
    """Latest cached readback state for one Kafka topic/source pair.

    Schema handlers only update the fields they own. That lets us mix value,
    alarm, connection, and future schema-specific updates in one shared record.
    """

    has_value: bool = False
    value: Any = None
    value_timestamp_ns: int = 0
    alarm: Optional[Severity] = None
    alarm_message: str = ""
    alarm_timestamp_ns: int = 0
    connection: Optional[ConnectionInfo] = None
    connection_service: str = ""
    connection_timestamp_ns: int = 0
    kafka_error: Optional[KafkaReadbackError] = None
    kafka_error_message: str = ""
    kafka_error_timestamp_ns: int = 0

    def snapshot(self):
        return replace(self)


@dataclass(frozen=True)
class KafkaReadbackSchemaSpec:
    """How one schema contributes to the shared readback state."""

    get_source_name: Callable[[Any], str]
    apply_update: Callable[[KafkaReadbackState, Any], None]


class KafkaReadbackRouter(Device):
    """Shared Kafka router device for scalar NICOS readbacks.

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

    _schema_specs: Dict[str, KafkaReadbackSchemaSpec] = {}

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
        key = self._key(topic, source_name)
        self._require_configured_topic(key[0])
        with self._lock:
            callbacks = self._callbacks.setdefault(key, [])
            if callback not in callbacks:
                callbacks.append(callback)
            state = self._latest.get(key)
            snapshot = state.snapshot() if state is not None else None

        if snapshot is not None:
            callback(snapshot)

    def unregister(self, topic, source_name, callback):
        key = self._key(topic, source_name)
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
            state = self._latest.get(self._key(topic, source_name))
            return state.snapshot() if state is not None else None

    def _start_topic_subscriber(self, topic):
        subscriber = KafkaSubscriber(self.brokers)
        subscriber.subscribe(
            [topic],
            messages_callback=partial(self._messages_callback, topic),
            error_callback=partial(self._error_callback, topic),
        )
        self._kafka_subscribers[topic] = subscriber

    def _messages_callback(self, topic, messages):
        for _timestamp, raw in messages:
            self._handle_kafka_payload(topic, raw)

    def _error_callback(self, topic, err):
        category, message = self._categorize_kafka_error(err)
        timestamp_ns = int(currenttime() * 1_000_000_000)
        notifications = []
        with self._lock:
            for key in list(self._callbacks):
                if key[0] != topic:
                    continue
                state = self._latest.setdefault(key, KafkaReadbackState())
                state.kafka_error = category
                state.kafka_error_message = message
                state.kafka_error_timestamp_ns = timestamp_ns
                notifications.append(
                    (key, state.snapshot(), list(self._callbacks.get(key, ())))
                )
        for (topic_, source_name), snapshot, callbacks in notifications:
            self._notify_callbacks(topic_, source_name, snapshot, callbacks)

    @staticmethod
    def _categorize_kafka_error(err):
        try:
            name = str(err.name() or "")
        except Exception:
            name = ""
        try:
            detail = err.str()
        except Exception:
            detail = repr(err)
        if KafkaConsumer.is_all_brokers_down(err):
            return KafkaReadbackError.BROKERS_DOWN, detail or "All Kafka brokers down"
        if KafkaConsumer.is_offset_out_of_range(err):
            return (
                KafkaReadbackError.OFFSET_OUT_OF_RANGE,
                detail or "Kafka offset out of range",
            )
        if KafkaConsumer.is_unknown_topic_or_partition(err):
            return (
                KafkaReadbackError.UNKNOWN_TOPIC,
                detail or "Kafka topic or partition missing",
            )
        return KafkaReadbackError.OTHER, detail or (name or "Kafka error")

    def _handle_kafka_payload(self, topic, raw):
        decoded_payload = self._decode_payload(raw)
        if decoded_payload is None:
            return

        source_name, apply_update, decoded = decoded_payload
        snapshot, callbacks = self._update_state(
            topic, source_name, apply_update, decoded
        )
        self._notify_callbacks(topic, source_name, snapshot, callbacks)

    def _decode_payload(self, raw):
        try:
            schema = get_schema(raw)
            spec = self._schema_specs.get(schema)
            decoder = DESERIALISERS.get(schema)
            if decoder is None or spec is None:
                return
            decoded = decoder(raw)
            source_name = spec.get_source_name(decoded)
            if not source_name:
                return
        except Exception as err:
            self.log.warning("Could not decode Kafka readback message: %s", err)
            return
        return source_name, spec.apply_update, decoded

    def _update_state(self, topic, source_name, apply_update, decoded):
        key = self._key(topic, source_name)
        with self._lock:
            state = self._latest.setdefault(key, KafkaReadbackState())
            apply_update(state, decoded)
            state.kafka_error = None
            state.kafka_error_message = ""
            state.kafka_error_timestamp_ns = 0
            snapshot = state.snapshot()
            callbacks = list(self._callbacks.get(key, ()))
        return snapshot, callbacks

    def _notify_callbacks(self, topic, source_name, snapshot, callbacks):
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

    @staticmethod
    def _source_name_from_source(decoded):
        return getattr(decoded, "source", "")

    @staticmethod
    def _source_name_from_source_name(decoded):
        return getattr(decoded, "source_name", "")

    @staticmethod
    def _apply_f144(state, decoded):
        state.has_value = True
        state.value = decoded.value
        state.value_timestamp_ns = int(decoded.timestamp_unix_ns or 0)

    @staticmethod
    def _apply_al00(state, decoded):
        state.alarm = decoded.severity
        state.alarm_message = decoded.message
        state.alarm_timestamp_ns = int(decoded.timestamp_ns or 0)

    @staticmethod
    def _apply_ep01(state, decoded):
        state.connection = decoded.status
        state.connection_service = decoded.service_id or ""
        state.connection_timestamp_ns = int(decoded.timestamp or 0)

    def _require_configured_topic(self, topic):
        if topic not in self.topics:
            raise ConfigurationError(
                self,
                "topic %r is not configured on %s" % (topic, self.name),
            )

    @staticmethod
    def _key(topic, source_name):
        return str(topic), str(source_name)

    def doShutdown(self):
        for subscriber in self._kafka_subscribers.values():
            subscriber.close()


KafkaReadbackRouter._schema_specs = {
    "f144": KafkaReadbackSchemaSpec(
        get_source_name=KafkaReadbackRouter._source_name_from_source_name,
        apply_update=KafkaReadbackRouter._apply_f144,
    ),
    "al00": KafkaReadbackSchemaSpec(
        get_source_name=KafkaReadbackRouter._source_name_from_source,
        apply_update=KafkaReadbackRouter._apply_al00,
    ),
    "ep01": KafkaReadbackSchemaSpec(
        get_source_name=KafkaReadbackRouter._source_name_from_source_name,
        apply_update=KafkaReadbackRouter._apply_ep01,
    ),
}


class KafkaReadable(Readable):
    """NICOS readback backed by a shared ``KafkaReadbackRouter``."""

    attached_devices = {
        "kafka": Attach("Shared Kafka readback router", KafkaReadbackRouter),
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
        current_status = self._status_from_snapshot(snapshot)
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
                    max(
                        snapshot.alarm_timestamp_ns,
                        snapshot.connection_timestamp_ns,
                        snapshot.kafka_error_timestamp_ns,
                    )
                ),
            )

    def _status_from_snapshot(self, snapshot):
        if snapshot is None:
            return None

        parts = []
        if snapshot.alarm is not None:
            parts.append(self._alarm_status(snapshot.alarm, snapshot.alarm_message))
        if snapshot.connection is not None:
            parts.append(
                self._connection_status(
                    snapshot.connection, snapshot.connection_service
                )
            )
        if snapshot.kafka_error is not None:
            parts.append(
                (
                    status.ERROR,
                    snapshot.kafka_error_message
                    or f"Kafka subscriber error: {snapshot.kafka_error.value}",
                )
            )
        if not parts:
            return None
        return max(parts, key=lambda item: item[0])

    @staticmethod
    def _cache_timestamp(timestamp_ns):
        if timestamp_ns:
            return timestamp_ns / 1_000_000_000
        return currenttime()

    @staticmethod
    def _alarm_status(severity, message):
        if severity == Severity.OK:
            return status.OK, ""
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

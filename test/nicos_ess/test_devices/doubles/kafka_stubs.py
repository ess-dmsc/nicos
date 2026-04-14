# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Kafka test doubles for fast harness-based device tests.

The doubles are intentionally tiny:

- producers only record what was sent
- consumers return queued records or records synthesised by a hook
- subscribers record subscriptions and can be driven explicitly by tests

That keeps the tests explicit about when data appears, instead of hiding a
background Kafka simulation inside the fixtures.
"""


class StubKafkaSubscriber:
    """Subscriber stub that records subscriptions and exposes callbacks."""

    def __init__(self, brokers=None, consumer=None, **kwargs):
        self.brokers = brokers
        self.consumer = consumer
        self.options = kwargs
        self.subscribed = []
        self.messages_callback = None
        self.no_messages_callback = None
        self.closed = False
        self.stop_called = False

    def subscribe(self, topics, messages_callback=None, no_messages_callback=None):
        self.subscribed.append(list(topics))
        self.messages_callback = messages_callback
        self.no_messages_callback = no_messages_callback

    def emit_messages(self, messages):
        if self.messages_callback:
            self.messages_callback(messages)

    def emit_idle(self):
        if self.no_messages_callback:
            self.no_messages_callback()

    def stop_consuming(self):
        self.stop_called = True

    def close(self):
        self.closed = True
        if self.consumer is not None:
            self.consumer.close()


class StubKafkaConsumer:
    """Queue-based consumer with an optional dynamic poll hook.

    `poll_hook` lets a test derive the next consumed record from external
    state, for example by returning an ACK after a producer recorded a config
    command.
    """

    def __init__(self, brokers=None, options=None, records=None, poll_hook=None):
        self.brokers = list(brokers) if brokers is not None else None
        self.options = dict(options or {})
        self.records = [self._coerce_record(record) for record in records or ()]
        self.poll_hook = poll_hook
        self.subscriptions = []
        self.closed = False

    def subscribe(self, *args, **kwargs):
        self.subscriptions.append((args, kwargs))

    def poll(self, *args, **kwargs):
        if self.poll_hook is not None:
            # The hook can synthesise a record from the current producer state.
            record = self.poll_hook(self, *args, **kwargs)
            if record is not None:
                return self._coerce_record(record)
        if self.records:
            return self.records.pop(0)
        return None

    def seek(self, *args, **kwargs):
        del args, kwargs

    def queue_record(self, payload):
        self.records.append(self._coerce_record(payload))

    def _coerce_record(self, record):
        if hasattr(record, "value"):
            return record
        return StubKafkaMessage(record)

    def close(self):
        self.closed = True


class _DeliveredMessage:
    """Minimal object matching the producer callback interface we rely on."""

    def partition(self):
        return 0

    def offset(self):
        return 0


class StubKafkaMessage:
    """Small Kafka message object for tests that need topic/error metadata."""

    def __init__(
        self,
        payload,
        *,
        topic="",
        key=None,
        error=None,
        timestamp=(0, 0),
        partition=0,
        offset=0,
    ):
        self._payload = payload
        self._topic = topic
        self._key = key
        self._error = error
        self._timestamp = timestamp
        self._partition = partition
        self._offset = offset

    def value(self):
        return self._payload

    def topic(self):
        return self._topic

    def key(self):
        return self._key

    def error(self):
        return self._error

    def timestamp(self):
        return self._timestamp

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset


class StubKafkaProducer:
    """Producer that records every message and immediately reports delivery."""

    def __init__(self):
        self.messages = []

    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaProducer()

    def produce(self, topic, message, **kwargs):
        self.messages.append(
            {
                "topic": topic,
                "message": message,
                "key": kwargs.get("key"),
            }
        )
        # Tests are usually interested in what was sent, not in delivery
        # retries, so we report success immediately.
        callback = kwargs.get("on_delivery_callback")
        if callback:
            callback(None, _DeliveredMessage())

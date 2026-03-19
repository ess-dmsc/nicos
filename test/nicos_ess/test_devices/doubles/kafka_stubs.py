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

"""Kafka test doubles for fast harness-based device tests."""

from collections import deque


class StubKafkaSubscriber:
    def __init__(self, *args, **kwargs):
        del args, kwargs

    def subscribe(self, *args, **kwargs):
        del args, kwargs

    def stop_consuming(self):
        pass

    def close(self):
        pass


class StubKafkaConsumer:
    def __init__(self, messages=None):
        self._messages = deque()
        self._consumer = self
        for message in messages or ():
            self.push_message(message)

    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaConsumer()

    def subscribe(self, *args, **kwargs):
        del args, kwargs

    def poll(self, *args, **kwargs):
        del args, kwargs
        if self._messages:
            return self._messages.popleft()
        return None

    def push_message(self, message):
        if hasattr(message, "value"):
            self._messages.append(message)
        else:
            self._messages.append(_StubKafkaMessage(message))

    def seek(self, *args, **kwargs):
        del args, kwargs

    def commit(self, *args, **kwargs):
        del args, kwargs

    def close(self):
        pass


class _StubKafkaMessage:
    def __init__(self, value, key=None):
        self._value = value
        self._key = key

    def value(self):
        return self._value

    def key(self):
        return self._key


class _DeliveredMessage:
    def partition(self):
        return 0

    def offset(self):
        return 0


class StubKafkaProducer:
    def __init__(self):
        self.messages = []

    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaProducer()

    def produce(
        self,
        topic_name,
        message=None,
        partition=-1,
        key=None,
        on_delivery_callback=None,
        *,
        auto_flush=True,
        flush_timeout=None,
        poll_before_produce=True,
    ):
        del partition, auto_flush, flush_timeout, poll_before_produce
        self.messages.append({"topic": topic_name, "message": message, "key": key})
        if on_delivery_callback:
            on_delivery_callback(None, _DeliveredMessage())

    def flush(self, timeout=None):
        del timeout
        return 0

    def poll(self, timeout=0.0):
        del timeout
        return 0


def patch_kafka_stubs(
    monkeypatch,
    module,
    *,
    producer=None,
    consumer_factory=StubKafkaConsumer,
    consumer_messages=None,
    subscriber=StubKafkaSubscriber,
    status_module=None,
):
    """Patch a module to use the shared Kafka harness doubles."""

    if producer is None:
        producer = StubKafkaProducer()

    def create_consumer(*args, **kwargs):
        del args, kwargs
        if consumer_messages is not None and consumer_factory is StubKafkaConsumer:
            return StubKafkaConsumer(messages=consumer_messages)
        return consumer_factory()

    def create_producer(*args, **kwargs):
        del args, kwargs
        return producer

    if hasattr(module, "KafkaSubscriber"):
        monkeypatch.setattr(module, "KafkaSubscriber", subscriber)
    if hasattr(module, "KafkaConsumer"):
        monkeypatch.setattr(module.KafkaConsumer, "create", create_consumer)
    if hasattr(module, "KafkaProducer"):
        monkeypatch.setattr(module.KafkaProducer, "create", create_producer)
    if status_module is not None:
        monkeypatch.setattr(status_module, "KafkaSubscriber", subscriber)
    return producer

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
- subscribers are no-ops because tests drive callbacks directly

That keeps the tests explicit about when data appears, instead of hiding a
background Kafka simulation inside the fixtures.
"""


class StubKafkaSubscriber:
    """No-op subscriber used when a test triggers callbacks directly."""

    def __init__(self, *args, **kwargs):
        del args, kwargs

    def subscribe(self, *args, **kwargs):
        del args, kwargs

    def stop_consuming(self):
        pass

    def close(self):
        pass


class StubKafkaConsumer:
    """Queue-based consumer with an optional dynamic poll hook.

    `poll_hook` lets a test derive the next consumed record from external
    state, for example by returning an ACK after a producer recorded a config
    command.
    """

    def __init__(self, records=None, poll_hook=None):
        self.records = [self._coerce_record(record) for record in records or ()]
        self.poll_hook = poll_hook
        self.subscriptions = []
        self.closed = False

    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaConsumer()

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
        return _StubKafkaRecord(record)

    def close(self):
        self.closed = True


class _DeliveredMessage:
    """Minimal object matching the producer callback interface we rely on."""

    def partition(self):
        return 0

    def offset(self):
        return 0


class _StubKafkaRecord:
    """Small wrapper exposing the `value()` method used by the code under test."""

    def __init__(self, payload):
        self._payload = payload

    def value(self):
        return self._payload


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

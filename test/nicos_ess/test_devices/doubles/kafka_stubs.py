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
    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaConsumer()

    def subscribe(self, *args, **kwargs):
        del args, kwargs

    def poll(self, *args, **kwargs):
        del args, kwargs
        return None

    def seek(self, *args, **kwargs):
        del args, kwargs

    def close(self):
        pass


class _DeliveredMessage:
    def partition(self):
        return 0

    def offset(self):
        return 0


class StubKafkaProducer:
    @staticmethod
    def create(*args, **kwargs):
        del args, kwargs
        return StubKafkaProducer()

    def produce(self, *args, **kwargs):
        del args
        callback = kwargs.get("on_delivery_callback")
        if callback:
            callback(None, _DeliveredMessage())

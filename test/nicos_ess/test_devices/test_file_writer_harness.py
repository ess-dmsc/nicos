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

import pytest

from nicos_ess.devices.datasinks import file_writer
from nicos_ess.devices.datasinks.nexus_structure import NexusStructureProvider
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)


ROLES = ("daemon", "poller")


class HarnessNexusStructureProvider(NexusStructureProvider):
    def get_structure(self, metainfo, counter):
        del metainfo, counter
        return "{}"


@pytest.fixture
def kafka_stubs(monkeypatch):
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        file_writer.KafkaConsumer, "create", lambda *args, **kwargs: StubKafkaConsumer()
    )
    monkeypatch.setattr(
        file_writer.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )


@pytest.fixture
def attached_file_writer_devices(device_harness, kafka_stubs):
    del kafka_stubs
    for role in ROLES:
        device_harness.create_master(
            role,
            file_writer.FileWriterStatus,
            name="file_writer_status_dev",
            brokers=["localhost:9092"],
            statustopic=["file_writer_status"],
        )
        device_harness.create_master(
            role,
            HarnessNexusStructureProvider,
            name="nexus_structure_dev",
        )


@pytest.mark.parametrize("role", ROLES)
def test_file_writer_status_initializes(
    role,
    device_harness,
    kafka_stubs,
):
    del kafka_stubs
    dev = device_harness.create_master(
        role,
        file_writer.FileWriterStatus,
        name=f"file_writer_status_{role}",
        brokers=["localhost:9092"],
        statustopic=["file_writer_status"],
    )
    assert dev is not None


@pytest.mark.parametrize("role", ROLES)
def test_file_writer_control_sink_initializes(
    role,
    device_harness,
    kafka_stubs,
    attached_file_writer_devices,
):
    del kafka_stubs, attached_file_writer_devices
    dev = device_harness.create_master(
        role,
        file_writer.FileWriterControlSink,
        name=f"file_writer_control_sink_{role}",
        brokers=["localhost:9092"],
        pool_topic="file_writer_pool",
        instrument_topic="file_writer_instrument",
        status="file_writer_status_dev",
        nexus="nexus_structure_dev",
    )
    assert dev is not None

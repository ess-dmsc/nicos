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
    patch_kafka_stubs,
)


class HarnessNexusStructureProvider(NexusStructureProvider):
    def get_structure(self, metainfo, counter):
        del metainfo, counter
        return "{}"


@pytest.fixture
def kafka_stubs(monkeypatch):
    patch_kafka_stubs(monkeypatch, file_writer, status_module=status_handler)


@pytest.fixture
def attached_file_writer_devices(device_harness, kafka_stubs):
    del kafka_stubs
    device_harness.create_pair(
        file_writer.FileWriterStatus,
        name="file_writer_status_dev",
        shared={
            "brokers": ["localhost:9092"],
            "statustopic": ["file_writer_status"],
        },
    )
    device_harness.create_pair(
        HarnessNexusStructureProvider,
        name="nexus_structure_dev",
    )


class TestFileWriterStatusHarness:
    def test_initializes(self, device_harness, kafka_stubs):
        del kafka_stubs
        daemon_device, poller_device = device_harness.create_pair(
            file_writer.FileWriterStatus,
            name="file_writer_status",
            shared={
                "brokers": ["localhost:9092"],
                "statustopic": ["file_writer_status"],
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestFileWriterControlSinkHarness:
    def test_initializes(self, device_harness, kafka_stubs, attached_file_writer_devices):
        del kafka_stubs, attached_file_writer_devices
        daemon_device, poller_device = device_harness.create_pair(
            file_writer.FileWriterControlSink,
            name="file_writer_control_sink",
            shared={
                "brokers": ["localhost:9092"],
                "pool_topic": "file_writer_pool",
                "instrument_topic": "file_writer_instrument",
                "status": "file_writer_status_dev",
                "nexus": "nexus_structure_dev",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

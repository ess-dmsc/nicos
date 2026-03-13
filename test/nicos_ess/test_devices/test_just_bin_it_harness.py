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

from nicos_ess.devices.datasources import just_bin_it
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)


@pytest.fixture
def kafka_stubs(monkeypatch):
    monkeypatch.setattr(just_bin_it, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        just_bin_it.KafkaConsumer, "create", lambda *args, **kwargs: StubKafkaConsumer()
    )
    monkeypatch.setattr(
        just_bin_it.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)


class TestJustBinItImageHarness:
    def test_initializes(self, device_harness, kafka_stubs):
        del kafka_stubs
        daemon_device, poller_device = device_harness.create_pair(
            just_bin_it.JustBinItImage,
            name="just_bin_it_image",
            shared={
                "brokers": ["localhost:9092"],
                "hist_topic": "jbi_hist",
                "data_topic": "jbi_data",
            },
        )

        assert daemon_device is not None
        assert poller_device is not None


class TestJustBinItDetectorHarness:
    def test_initializes(self, device_harness, kafka_stubs):
        del kafka_stubs
        daemon_device, poller_device = device_harness.create_pair(
            just_bin_it.JustBinItDetector,
            name="just_bin_it_detector",
            shared={
                "brokers": ["localhost:9092"],
                "command_topic": "jbi_command",
                "response_topic": "jbi_response",
                "statustopic": [],
            },
        )

        assert daemon_device is not None
        assert poller_device is not None

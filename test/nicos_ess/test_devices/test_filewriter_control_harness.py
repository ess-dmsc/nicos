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
from datetime import datetime
from unittest import mock
from unittest.mock import Mock

import pytest

from nicos_ess.devices.datasinks import file_writer
from nicos_ess.devices.datasinks.file_writer import (
    AlreadyWritingException,
    JobRecord,
)
from nicos_ess.devices.datasinks.nexus_structure import (
    NexusStructureJsonFile,
)
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)
from test.nicos_ess.test_devices.doubles.serialised_messages import (
    create_status_message,
)


class HarnessNexusStructureProvider(NexusStructureJsonFile):
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
def filewriter_control_sink_devices(device_harness, kafka_stubs):
    # kafka stubs not used directly but needed to create filewriter devices
    del kafka_stubs
    # attached filewriter status device
    device_harness.create_pair(
        file_writer.FileWriterStatus,
        name="filewriter_status_device",
        shared={
            "brokers": ["localhost:9092"],
            "statustopic": ["filewriter_status"],
        },
    )
    # attached nexus structure device
    device_harness.create_pair(
        HarnessNexusStructureProvider,
        name="NexusStructure",
        shared={
            "instrument_name": "ymir",
        },
    )
    return device_harness.create_pair(
        file_writer.FileWriterControlSink,
        name="file_writer_control_sink",
        shared={
            "brokers": ["localhost:9092"],
            "pool_topic": "filewriter_pool",
            "instrument_topic": "filewriter_instrument",
            "status": "filewriter_status_device",
            "nexus": "NexusStructure",
        },
    )


class TestFileWriterControlSinkHarness:
    def test_initializes(self, filewriter_control_sink_devices):
        daemon_device, poller_device = filewriter_control_sink_devices

        assert daemon_device is not None
        assert poller_device is not None

    def test_cannot_start_job_if_job_in_progress(
        self,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device._attached_status.add_job(job)
        messages = [(123, create_status_message(job_id_1))]
        daemon_device._attached_status.new_messages_callback(messages)

        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            with pytest.raises(AlreadyWritingException):
                daemon_device.start_job()

    def test_can_start_job_if_no_job_in_progress(
        self,
        monkeypatch,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
        monkeypatch.setattr(
            file_writer.FileWriterController,
            "_generate_uuid",
            lambda self, file_num: job_id_1,
        )
        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            daemon_device.start_job()

        assert job_id_1 in daemon_device._attached_status.jobs_in_progress

    def test_can_start_job_if_existing_job_is_stopped(
        self,
        monkeypatch,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices

        stopping_job_id = "job id 1"
        job = JobRecord(stopping_job_id, 42, 0, 0)
        daemon_device._attached_status.add_job(job)
        daemon_device._attached_status.mark_for_stop(
            stopping_job_id, stop_time=12345678
        )
        assert stopping_job_id not in daemon_device.get_active_jobs()

        new_job_id = "job id 2"
        monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
        monkeypatch.setattr(
            file_writer.FileWriterController,
            "_generate_uuid",
            lambda self, file_num: new_job_id,
        )
        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            daemon_device.start_job()
        assert new_job_id in daemon_device._attached_status.jobs_in_progress

    def test_list_jobs_limits_output_to_most_recent_jobs(
        self,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        daemon_device._attached_status._jobs_in_order = {}
        for idx, job_id in enumerate(["job id 1", "job id 2", "job id 3"], start=1):
            job = JobRecord(job_id, idx, datetime.fromtimestamp(0), 0)
            daemon_device._attached_status._jobs_in_order[job_id] = job

        with (
            device_harness.activate("daemon"),
            mock.patch(
                "nicos_ess.devices.datasinks.file_writer.printTable"
            ) as print_table,
        ):
            daemon_device.list_jobs(2)

        _, items, _ = print_table.call_args.args
        assert len(items) == 2
        assert [item[0] for item in items] == ["2", "3"]

    def test_stop_job_ignored_if_no_job_in_progress(
        self,
        monkeypatch,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        daemon_device.stop_job()

        request_stop.assert_not_called()

    def test_can_stop_running_job(
        self,
        monkeypatch,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
        monkeypatch.setattr(
            file_writer.FileWriterController,
            "_generate_uuid",
            lambda self, file_num: job_id_1,
        )
        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            daemon_device.start_job()
            assert job_id_1 in daemon_device.get_active_jobs()
            daemon_device.stop_job()
        request_stop.assert_called_once()

        assert job_id_1 not in daemon_device.get_active_jobs()
        assert job_id_1 in daemon_device._attached_status.marked_for_stop

    def test_stop_job_ignored_if_existing_job_is_already_stopping(
        self,
        monkeypatch,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
        monkeypatch.setattr(
            file_writer.FileWriterController,
            "_generate_uuid",
            lambda self, file_num: job_id_1,
        )
        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            daemon_device.start_job()
            daemon_device.stop_job()
            daemon_device.stop_job()

        request_stop.assert_called_once()

    def test_stop_job_ignored_if_job_id_does_not_match(
        self,
        monkeypatch,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        job_number = 42
        job = JobRecord(job_id_1, job_number, 0, 0)
        daemon_device._attached_status.add_job(job)
        status_message = [(123, create_status_message(job_id_1))]
        daemon_device._attached_status.new_messages_callback(status_message)
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        daemon_device.stop_job(job_number="does not match")

        request_stop.assert_not_called()

    def test_can_stop_job_if_job_id_matches(
        self,
        monkeypatch,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        job_number = 42
        job = JobRecord(job_id_1, job_number, 0, 0)
        daemon_device._attached_status.add_job(job)
        status_message = [(123, create_status_message(job_id_1))]
        daemon_device._attached_status.new_messages_callback(status_message)
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        daemon_device.stop_job(job_number=job_number)

        request_stop.assert_called_once()

    def test_with_multiple_jobs_no_jobs_stopped_if_job_id_not_supplied(
        self,
        monkeypatch,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        job_id_2 = "job id 2"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device._attached_status.add_job(job)
        job = JobRecord(job_id_2, 42, 0, 0)
        daemon_device._attached_status.add_job(job)
        status_messages = [
            (123, create_status_message(job_id_1)),
            (234, create_status_message(job_id_2)),
        ]
        daemon_device._attached_status.new_messages_callback(status_messages)
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        daemon_device.stop_job()

        request_stop.assert_not_called()

    def test_with_multiple_jobs_specified_job_is_stopped(
        self,
        monkeypatch,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        job_id_1 = "job id 1"
        job_number_1 = 42
        job_id_2 = "job id 2"
        job_number_2 = 43
        job = JobRecord(job_id_1, job_number_1, 0, 0)
        daemon_device._attached_status.add_job(job)
        job = JobRecord(job_id_2, job_number_2, 0, 0)
        daemon_device._attached_status.add_job(job)
        status_messages = [
            (123, create_status_message(job_id_1)),
            (234, create_status_message(job_id_2)),
        ]
        daemon_device._attached_status.new_messages_callback(status_messages)
        request_stop = Mock()
        monkeypatch.setattr(
            file_writer.FileWriterController, "request_stop", request_stop
        )
        daemon_device.stop_job(job_number=job_number_1)

        request_stop.assert_called_once()
        assert job_id_1 in daemon_device._attached_status.marked_for_stop
        assert job_id_2 in daemon_device.get_active_jobs()

    def test_lost_job_still_considered_in_progress(
        self,
        monkeypatch,
        device_harness,
        filewriter_control_sink_devices,
    ):
        daemon_device, poller_device = filewriter_control_sink_devices
        # Simulate a file-writer crash by forcing the job to time out.
        job_id_1 = "job id 1"
        monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
        monkeypatch.setattr(
            file_writer.FileWriterController,
            "_generate_uuid",
            lambda self, file_num: job_id_1,
        )
        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = "123456"
            daemon_device.start_job()
        status_message = [(123, create_status_message(job_id_1))]
        daemon_device._attached_status.new_messages_callback(status_message)
        daemon_device._attached_status.timeoutinterval = -10
        daemon_device._attached_status.no_messages_callback()

        assert job_id_1 in daemon_device.get_active_jobs()

    # def test_can_stop_writing_even_if_job_lost(
    #     self,
    #     monkeypatch,
    #     device_harness,
    #     filewriter_control_sink_devices,
    # ):
    #     daemon_device, poller_device = filewriter_control_sink_devices
    #     # Simulate a file-writer crash by forcing the job to time out.
    #     job_id_1 = "job id 1"
    #     monkeypatch.setattr(file_writer, "incrementFileCounter", lambda: 42)
    #     monkeypatch.setattr(
    #         file_writer.FileWriterController,
    #         "_generate_uuid",
    #         lambda self, file_num: job_id_1,
    #     )
    #     with device_harness.activate("daemon") as daemon_session:
    #         daemon_session.experiment.propinfo["proposal"] = "123456"
    #         daemon_device.start_job()
    #     status_message = [(123, create_status_message(job_id_1))]
    #     daemon_device._attached_status.new_messages_callback(status_message)
    #     daemon_device._attached_status.timeoutinterval = -10
    #     daemon_device._attached_status.no_messages_callback()
    #
    #     #with self.log.allow_errors():
    #     daemon_device.stop_job()

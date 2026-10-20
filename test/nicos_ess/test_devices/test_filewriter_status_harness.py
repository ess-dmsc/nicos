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
from nicos_ess.devices.datasinks.file_writer import JobRecord, JobState
from nicos_ess.devices.datasinks.nexus_structure import NexusStructureProvider
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)
from test.nicos_ess.test_devices.doubles.serialised_messages import (
    create_start_request_message,
    create_status_message,
    create_stop_confirmed_message,
    create_stop_request_message,
)


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
def filewriter_status_devices(device_harness, kafka_stubs):
    # kafka stubs not used directly but needed to create filewriter status devices
    del kafka_stubs
    return device_harness.create_pair(
        file_writer.FileWriterStatus,
        name="file_writer_status",
        shared={
            "brokers": ["localhost:9092"],
            "statustopic": ["file_writer_status"],
        },
    )


class TestFileWriterStatusHarness:
    def test_initializes(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices

        assert daemon_device is not None
        assert poller_device is not None

    def test_after_startup_no_jobs_in_progress(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices

        assert not daemon_device.jobs_in_progress

    def test_adding_new_job_puts_it_in_progress(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.NOT_STARTED

    def test_status_message_received_changes_next_update_time(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        status_message = [(123, create_status_message(job_id_1))]
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        old_time = daemon_device._jobs[job_id_1].next_update
        daemon_device.new_messages_callback(status_message)

        assert daemon_device._jobs[job_id_1].next_update != old_time

    def test_on_start_job_success(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        start_request = [(456, create_start_request_message(job_id_1, success=True))]
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        daemon_device.new_messages_callback(start_request)

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.STARTED

    def test_job_stopped_before_filewriting_picks_it_up_successfully_completes(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)

        assert job_id_1 in daemon_device.marked_for_stop
        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.NOT_STARTED

        start_request = [(456, create_start_request_message(job_id_1, success=True))]
        daemon_device.new_messages_callback(start_request)

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.STARTED

        stop_confirm = [(567, create_stop_confirmed_message(job_id_1))]
        daemon_device.new_messages_callback(stop_confirm)

        assert job_id_1 not in daemon_device.jobs_in_progress

    def test_queued_job_starts_after_a_delay(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)

        # Force timeouts in the status reporting
        daemon_device.timeoutinterval = -10
        daemon_device.no_messages_callback()

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.NOT_STARTED

        start_request = [(456, create_start_request_message(job_id_1, success=True))]
        daemon_device.new_messages_callback(start_request)

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.STARTED

    def test_on_failed_start_job_is_rejected_and_removed_from_jobs_in_progress(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)

        start_request = [(456, create_start_request_message(job_id_1, success=False))]
        daemon_device.new_messages_callback(start_request)

        assert job_id_1 not in daemon_device.jobs_in_progress
        assert daemon_device._jobs_in_order[job_id_1].state == JobState.REJECTED

    def test_if_not_yet_started_then_can_mark_for_stop_but_still_in_progress(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)

        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)

        assert job_id_1 in daemon_device.marked_for_stop
        assert job_id_1 in daemon_device.jobs_in_progress

    def test_if_started_then_can_mark_for_stop_but_still_in_progress(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        start_request = [(456, create_start_request_message(job_id_1, success=True))]
        daemon_device.new_messages_callback(start_request)

        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)

        assert job_id_1 in daemon_device.marked_for_stop
        assert job_id_1 in daemon_device.jobs_in_progress

    def test_if_start_failed_then_is_removed_immediately_when_marked_for_stop(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        start_request = [(456, create_start_request_message(job_id_1, success=False))]
        daemon_device.new_messages_callback(start_request)

        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)

        assert job_id_1 not in daemon_device.marked_for_stop
        assert job_id_1 not in daemon_device.jobs_in_progress

    def test_answer_to_stop_message_does_not_modify_job_state(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)
        messages = [
            (123, create_status_message(job_id_1)),
            (125, create_stop_request_message(job_id_1)),
        ]
        daemon_device.new_messages_callback(messages)

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.STARTED

    def test_on_stop_confirmed_job_is_not_in_progress(self, filewriter_status_devices):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        daemon_device.mark_for_stop(job_id_1, stop_time=12345678)
        stop_confirm = [(456, create_stop_confirmed_message(job_id_1))]
        daemon_device.new_messages_callback(stop_confirm)

        assert job_id_1 not in daemon_device.jobs_in_progress

    def test_status_message_after_job_stopped_is_ignored(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        # There is no guarantee that messages from Kafka are in the order sent
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        messages = [
            (123, create_status_message(job_id_1)),
            (125, create_stop_request_message(job_id_1)),
            (126, create_stop_confirmed_message(job_id_1)),
        ]
        daemon_device.new_messages_callback(messages)
        delayed_status = [(124, create_status_message(job_id_1))]
        daemon_device.new_messages_callback(delayed_status)

        assert job_id_1 not in daemon_device.jobs_in_progress
        assert job_id_1 not in daemon_device.marked_for_stop

    def test_job_marked_as_failed_when_no_status_messages_for_a_while(
        self, filewriter_status_devices
    ):
        daemon_device, poller_device = filewriter_status_devices
        job_id_1 = "job id 1"
        job = JobRecord(job_id_1, 42, 0, 0)
        daemon_device.add_job(job)
        status_message = [(123, create_status_message(job_id_1))]
        daemon_device.new_messages_callback(status_message)
        # Hack it so it times out immediately
        daemon_device.timeoutinterval = -10
        daemon_device.no_messages_callback()

        assert job_id_1 in daemon_device.jobs_in_progress
        assert daemon_device._jobs[job_id_1].state == JobState.FAILED

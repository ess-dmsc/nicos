import json
from datetime import datetime

from streaming_data_types import serialise_answ, serialise_wrdn, serialise_x5f2
from streaming_data_types.fbschemas.action_response_answ.ActionOutcome import (
    ActionOutcome,
)
from streaming_data_types.fbschemas.action_response_answ.ActionType import ActionType


def create_status_message(job_id, start_time=1, stop_time=9999, update_interval=1000):
    status = {
        "file_being_written": "filename",
        "job_id": job_id,
        "start_time": start_time,
        "state": "writing",
        "stop_time": stop_time,
    }
    return serialise_x5f2(
        "nicos_tests",
        "version",
        "service_id",
        "hostname",
        12345,
        update_interval,
        json.dumps(status),
    )


def create_start_request_message(job_id, start_time=None, success=True):
    start = start_time if start_time else datetime.now()
    outcome = ActionOutcome.Success if success else ActionOutcome.Failure
    return serialise_answ(
        "service_id",
        job_id,
        "command_id",
        ActionType.StartJob,
        outcome,
        "message",
        0,
        start,
    )


def create_stop_request_message(job_id, stop_time=None, success=True):
    stop = stop_time if stop_time else datetime.now()
    outcome = ActionOutcome.Success if success else ActionOutcome.Failure
    return serialise_answ(
        "service_id",
        job_id,
        "command_id",
        ActionType.SetStopTime,
        outcome,
        "message",
        0,
        stop,
    )


def create_stop_confirmed_message(job_id):
    metadata = json.dumps({"stop_time": 123456})
    return serialise_wrdn("service_id", job_id, False, "filename", metadata)


def create_stop_message_with_error(job_id):
    metadata = json.dumps({"stop_time": 123456})
    return serialise_wrdn(
        "service_id", job_id, True, "filename", metadata, "some error"
    )

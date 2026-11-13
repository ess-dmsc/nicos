"""Helpers for the NICOS smoke stack test."""

from __future__ import annotations

import json
import math
import time
from textwrap import dedent

from confluent_kafka import OFFSET_BEGINNING, Consumer, TopicPartition
from streaming_data_types import deserialise_f144, deserialise_pl72


def read_counters(smoke_client) -> dict[str, int]:
    counters_file = smoke_client.runtime_root / "data" / "counters"
    counters: dict[str, int] = {}
    if not counters_file.exists():
        return counters
    for line in counters_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        counters[key] = int(value)
    return counters


def wait_for_counter_increment(
    smoke_client, scan_before: int, file_before: int, timeout: float = 10.0
) -> dict[str, int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        counters = read_counters(smoke_client)
        if (
            counters.get("scan", 0) >= scan_before + 1
            and counters.get("file", 0) >= file_before + 1
        ):
            return counters
        time.sleep(0.1)
    raise TimeoutError(
        "counter increments not observed in time: "
        f"before(scan={scan_before}, file={file_before}) "
        f"after={read_counters(smoke_client)}"
    )


def wait_for_moveable_readback(
    smoke_client, moveable, target: float, timeout: float = 15.0
) -> float:
    deadline = time.monotonic() + timeout
    value = float(smoke_client.read(moveable, 0))
    while time.monotonic() < deadline:
        value = float(smoke_client.read(moveable, 0))
        if math.isclose(value, target, abs_tol=0.05):
            return value
        time.sleep(0.1)
    move_name = moveable.name
    pv_val = smoke_client.eval(
        f"{move_name}._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.VAL')",
        default=None,
    )
    pv_rbv = smoke_client.eval(
        f"{move_name}._epics_wrapper.get_pv_value('TEST:SMOKE:MOVE.RBV')",
        default=None,
    )
    raise TimeoutError(
        "readback did not reach target in time: "
        f"final={value} target={target} pv_val={pv_val} pv_rbv={pv_rbv}"
    )


def filewriter_jobs(smoke_client):
    return smoke_client.eval(
        "["
        "(job.job_id, job.job_number, job.get_state_string(), "
        "job.stop_requested, job.error_msg, job.service_id) "
        "for job in FileWriterStatus._jobs_in_order.values()"
        "]",
        default=[],
    )


def wait_for_filewriter_job_state(
    smoke_client, job_id: str, expected_state: str, timeout: float = 20.0
):
    deadline = time.monotonic() + timeout
    jobs = []
    while time.monotonic() < deadline:
        jobs = filewriter_jobs(smoke_client)
        for job in jobs:
            if job[0] == job_id and job[2] == expected_state:
                return job
        time.sleep(0.1)
    raise TimeoutError(
        "filewriter job state not observed in time: "
        f"job_id={job_id!r} expected={expected_state!r} jobs={jobs!r}"
    )


def run_scan_with_filewriter_context(
    smoke_client, *, title: str, timeout: float = 180.0
):
    smoke_client.execute(
        dedent(
            f"""
            __smoke_filewriter_jobs_before = [
                (job.job_id, job.job_number, job.get_state_string())
                for job in FileWriterStatus._jobs_in_order.values()
            ]
            __smoke_jobs_before = FileWriterControl.get_active_jobs()
            with nexusfile_open({title!r}):
                __smoke_jobs_during = FileWriterControl.get_active_jobs()
                __smoke_filewriter_state_during = ""
                __smoke_filewriter_service_during = ""
                import time as __smoke_time
                __smoke_deadline = __smoke_time.monotonic() + 20
                while __smoke_time.monotonic() < __smoke_deadline:
                    __smoke_filewriter_jobs_during = [
                        (
                            job.job_id,
                            job.job_number,
                            job.get_state_string(),
                            job.service_id,
                        )
                        for job in FileWriterStatus._jobs_in_order.values()
                    ]
                    if __smoke_filewriter_jobs_during:
                        __smoke_latest_filewriter = (
                            __smoke_filewriter_jobs_during[-1]
                        )
                        __smoke_filewriter_state_during = (
                            __smoke_latest_filewriter[2]
                        )
                        __smoke_filewriter_service_during = (
                            __smoke_latest_filewriter[3]
                        )
                    if __smoke_filewriter_state_during == "STARTED":
                        break
                    __smoke_time.sleep(0.1)
                scan(SmokeBasicMoveable, [0, 5, 10], timer=2.0)
            __smoke_jobs_after = FileWriterControl.get_active_jobs()
            __smoke_filewriter_jobs_after = [
                (
                    job.job_id,
                    job.job_number,
                    job.get_state_string(),
                    job.stop_requested,
                    job.error_msg,
                    job.service_id,
                )
                for job in FileWriterStatus._jobs_in_order.values()
            ]
            """
        ),
        timeout=timeout,
    )
    return {
        "jobs_before": smoke_client.eval("__smoke_jobs_before", default=[]),
        "jobs_during": smoke_client.eval("__smoke_jobs_during", default=[]),
        "jobs_after": smoke_client.eval("__smoke_jobs_after", default=[]),
        "filewriter_jobs_before": smoke_client.eval(
            "__smoke_filewriter_jobs_before", default=[]
        ),
        "filewriter_state_during": smoke_client.eval(
            "__smoke_filewriter_state_during", default=""
        ),
        "filewriter_service_during": smoke_client.eval(
            "__smoke_filewriter_service_during", default=""
        ),
        "filewriter_jobs_after": smoke_client.eval(
            "__smoke_filewriter_jobs_after", default=[]
        ),
    }


def read_topic(smoke_client, topic: str, timeout: float = 20.0) -> list[bytes]:
    """Return every message on the single-partition *topic*, oldest first."""
    consumer = Consumer(
        {
            "bootstrap.servers": smoke_client.kafka_bootstrap,
            "group.id": f"nicos-smoke-reader-{time.monotonic_ns()}",
            "enable.auto.commit": False,
        }
    )
    try:
        _, high = consumer.get_watermark_offsets(
            TopicPartition(topic, 0), timeout=timeout
        )
        consumer.assign([TopicPartition(topic, 0, OFFSET_BEGINNING)])
        values = []
        deadline = time.monotonic() + timeout
        offset = -1
        while offset < high - 1:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"read {len(values)} of {high} messages from {topic}"
                )
            msg = consumer.poll(0.5)
            if msg is None or msg.error():
                continue
            offset = msg.offset()
            values.append(msg.value())
        return values
    finally:
        consumer.close()


def scan_log_messages(smoke_client, topic: str) -> dict[str, list[tuple[int, int]]]:
    """Return {source: [(value, timestamp_ns), ...]} of the scan log sink.

    Only changes are kept: the sink repeats its current values.
    """
    result = {"scanlog/scan": [], "scanlog/point": []}
    for value in read_topic(smoke_client, topic):
        if value[4:8] != b"f144":
            continue
        log = deserialise_f144(value)
        changes = result.get(log.source_name)
        if changes is not None and (not changes or changes[-1][0] != log.value):
            changes.append((int(log.value), log.timestamp_unix_ns))
    return result


def last_start_structure(smoke_client, pool_topic: str) -> dict:
    starts = [v for v in read_topic(smoke_client, pool_topic) if v[4:8] == b"pl72"]
    return json.loads(deserialise_pl72(starts[-1]).nexus_structure)

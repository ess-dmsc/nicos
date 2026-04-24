from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event

from confluent_kafka import Consumer, KafkaError, Producer
from streaming_data_types import (
    deserialise_6s4t,
    deserialise_pl72,
    serialise_answ,
    serialise_wrdn,
    serialise_x5f2,
)
from streaming_data_types.fbschemas.action_response_answ.ActionOutcome import (
    ActionOutcome,
)
from streaming_data_types.fbschemas.action_response_answ.ActionType import ActionType

DEFAULT_BOOTSTRAP = "localhost:19092"
DEFAULT_POOL_TOPIC = "test_smoke_filewriter_pool"
DEFAULT_STATUS_TOPIC = "test_smoke_filewriter_status"
DEFAULT_STATUS_INTERVAL_MS = 1000
DEFAULT_STOP_LEEWAY_S = 3.0
MAX_MESSAGE_SIZE = 209_715_200


@dataclass
class Job:
    job_id: str
    filename: str
    start_time_ms: int
    stop_time_ms: int
    control_topic: str
    metadata: str
    stop_deadline: float | None = None


class FileWriterDouble:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        pool_topic: str,
        status_topic: str,
        service_id: str,
        status_interval_ms: int,
        stop_leeway_s: float,
    ):
        self.pool_topic = pool_topic
        self.status_topic = status_topic
        self.service_id = service_id
        self.status_interval_ms = status_interval_ms
        self.stop_leeway_s = stop_leeway_s
        self.job: Job | None = None
        self._next_status = 0.0
        self._current_topic = ""
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "message.max.bytes": MAX_MESSAGE_SIZE,
            }
        )
        self._consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": f"nicos-smoke-filewriter-double-{os.getpid()}",
                "auto.offset.reset": "latest",
                "enable.auto.commit": False,
                "allow.auto.create.topics": False,
            }
        )

    def run(self, stop_event: Event) -> None:
        self._subscribe(self.pool_topic)
        self._publish_status()
        while not stop_event.is_set():
            self._finish_job_after_leeway()
            self._publish_status_if_due()
            msg = self._consumer.poll(0.1)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"[filewriter-double] kafka error: {msg.error()}", flush=True)
                continue
            self._handle_message(msg)
        self.close()

    def close(self) -> None:
        self._producer.flush(5)
        self._consumer.close()

    def _subscribe(self, topic: str) -> None:
        if topic == self._current_topic:
            return
        self._consumer.subscribe([topic])
        self._current_topic = topic
        print(f"[filewriter-double] consuming {topic}", flush=True)

    def _handle_message(self, msg) -> None:
        value = msg.value()
        self._commit(msg)
        if self.job is None and self._is_schema(value, b"pl72"):
            self._handle_start(value)
        elif self.job is not None and self._is_schema(value, b"6s4t"):
            self._handle_stop(value)

    def _commit(self, msg) -> None:
        try:
            self._consumer.commit(message=msg, asynchronous=False)
        except Exception as exc:
            print(f"[filewriter-double] commit failed: {exc}", flush=True)

    def _handle_start(self, value: bytes) -> None:
        start = deserialise_pl72(value)
        if not start.control_topic:
            self._publish_answer(
                topic=self.status_topic,
                job_id=start.job_id,
                command_id=start.job_id,
                action=ActionType.StartJob,
                outcome=ActionOutcome.Failure,
                status_code=400,
                message="Rejected start job as control topic was empty.",
                stop_time_ms=start.stop_time,
            )
            return

        self.job = Job(
            job_id=start.job_id,
            filename=start.filename,
            start_time_ms=start.start_time,
            stop_time_ms=start.stop_time,
            control_topic=start.control_topic,
            metadata=start.metadata,
        )
        self._subscribe(start.control_topic)
        self._publish(start.control_topic, value)
        self._publish_answer(
            topic=start.control_topic,
            job_id=start.job_id,
            command_id=start.job_id,
            action=ActionType.StartJob,
            outcome=ActionOutcome.Success,
            status_code=201,
            message="Started write job.",
            stop_time_ms=start.stop_time,
        )
        self._publish_status()

    def _handle_stop(self, value: bytes) -> None:
        assert self.job is not None
        stop = deserialise_6s4t(value)
        if stop.job_id != self.job.job_id:
            self._publish_answer(
                topic=self.job.control_topic,
                job_id=stop.job_id,
                command_id=stop.command_id,
                action=ActionType.SetStopTime,
                outcome=ActionOutcome.Failure,
                status_code=400,
                message="Rejected stop command as the job ID did not match.",
                stop_time_ms=stop.stop_time,
            )
            return

        stop_time_ms = stop.stop_time or _now_ms()
        self.job.stop_time_ms = stop_time_ms
        self.job.stop_deadline = time.monotonic() + self.stop_leeway_s
        self._publish_answer(
            topic=self.job.control_topic,
            job_id=stop.job_id,
            command_id=stop.command_id,
            action=ActionType.SetStopTime,
            outcome=ActionOutcome.Success,
            status_code=201,
            message="Attempting to stop writing job now.",
            stop_time_ms=stop_time_ms,
        )
        self._publish_status()

    def _finish_job_after_leeway(self) -> None:
        if self.job is None or self.job.stop_deadline is None:
            return
        if time.monotonic() < self.job.stop_deadline:
            return
        job = self.job
        self._publish(
            job.control_topic,
            serialise_wrdn(
                self.service_id,
                job.job_id,
                False,
                job.filename,
                job.metadata,
            ),
        )
        self.job = None
        self._subscribe(self.pool_topic)
        self._publish_status()

    def _publish_answer(
        self,
        *,
        topic: str,
        job_id: str,
        command_id: str,
        action: ActionType,
        outcome: ActionOutcome,
        status_code: int,
        message: str,
        stop_time_ms: int,
    ) -> None:
        self._publish(
            topic,
            serialise_answ(
                self.service_id,
                job_id,
                command_id,
                action,
                outcome,
                message,
                status_code,
                _datetime_from_ms(stop_time_ms),
            ),
        )

    def _publish_status_if_due(self) -> None:
        if time.monotonic() >= self._next_status:
            self._publish_status()

    def _publish_status(self) -> None:
        topic = self.job.control_topic if self.job else self.status_topic
        self._publish(topic, self._status_message())
        self._next_status = time.monotonic() + self.status_interval_ms / 1000

    def _status_message(self) -> bytes:
        if self.job is None:
            status = {
                "state": "idle",
                "job_id": "",
                "file_being_written": "",
                "start_time": 0,
                "stop_time": 0,
            }
        else:
            status = {
                "state": "writing",
                "job_id": self.job.job_id,
                "file_being_written": self.job.filename,
                "start_time": self.job.start_time_ms,
                "stop_time": self.job.stop_time_ms,
            }
        return serialise_x5f2(
            "nicos-smoke-filewriter-double",
            "0.0.0",
            self.service_id,
            socket.gethostname(),
            os.getpid(),
            self.status_interval_ms,
            json.dumps(status),
        )

    def _publish(self, topic: str, payload: bytes) -> None:
        self._producer.poll(0)
        self._producer.produce(topic, payload)
        self._producer.flush(10)

    @staticmethod
    def _is_schema(value: bytes, schema: bytes) -> bool:
        return len(value) >= 8 and value[4:8] == schema


def _now_ms() -> int:
    return int(time.time() * 1000)


def _datetime_from_ms(timestamp_ms: int) -> datetime:
    if timestamp_ms <= 0:
        return datetime.now()
    return datetime.fromtimestamp(timestamp_ms / 1000)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap",
        default=os.environ.get("NICOS_SMOKE_KAFKA_BOOTSTRAP", DEFAULT_BOOTSTRAP),
    )
    parser.add_argument(
        "--pool-topic",
        default=os.environ.get("NICOS_SMOKE_FILEWRITER_POOL_TOPIC", DEFAULT_POOL_TOPIC),
    )
    parser.add_argument(
        "--status-topic",
        default=os.environ.get(
            "NICOS_SMOKE_FILEWRITER_STATUS_TOPIC", DEFAULT_STATUS_TOPIC
        ),
    )
    parser.add_argument(
        "--service-id",
        default=os.environ.get(
            "NICOS_SMOKE_FILEWRITER_SERVICE_ID", "nicos-smoke-filewriter-double"
        ),
    )
    parser.add_argument(
        "--status-interval-ms",
        type=int,
        default=int(
            os.environ.get(
                "NICOS_SMOKE_FILEWRITER_STATUS_INTERVAL_MS",
                str(DEFAULT_STATUS_INTERVAL_MS),
            )
        ),
    )
    parser.add_argument(
        "--stop-leeway",
        type=float,
        default=float(
            os.environ.get(
                "NICOS_SMOKE_FILEWRITER_STOP_LEEWAY_S",
                str(DEFAULT_STOP_LEEWAY_S),
            )
        ),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    stop_event = Event()

    def _stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    FileWriterDouble(
        bootstrap_servers=args.bootstrap,
        pool_topic=args.pool_topic,
        status_topic=args.status_topic,
        service_id=args.service_id,
        status_interval_ms=args.status_interval_ms,
        stop_leeway_s=args.stop_leeway,
    ).run(stop_event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

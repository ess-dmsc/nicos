import json
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from os import path

from streaming_data_types import (
    deserialise_answ,
    deserialise_pl72,
    deserialise_wrdn,
    deserialise_x5f2,
    serialise_6s4t,
    serialise_pl72,
)
from streaming_data_types.fbschemas.action_response_answ.ActionOutcome import (
    ActionOutcome,
)
from streaming_data_types.fbschemas.action_response_answ.ActionType import ActionType

from nicos import session
from nicos.core import (
    ADMIN,
    POLLER,
    Attach,
    ConfigurationError,
    Moveable,
    Override,
    Param,
    host,
    listof,
    none_or,
    status,
)
from nicos.core.constants import SIMULATION, MASTER
from nicos.core.params import anytype, tupleof
from nicos.utils import printTable, readFileCounter, updateFileCounter, createThread

from nicos_ess.devices.datasinks.nexus_structure import NexusStructureProvider
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer


class AlreadyWritingException(Exception):
    pass


class StartWritingRejectedException(Exception):
    pass


class JobState(Enum):
    STARTED = (0,)
    NOT_STARTED = (1,)
    WRITTEN = (2,)
    REJECTED = (3,)
    FAILED = 4


class JobRecord:
    """Class for storing job information."""

    def __init__(self, job_id, job_number, start_time, kafka_offset):
        """Constructor.

        :param job_id:
        :param job_number:
        :param start_time:
        :param kafka_offset:
        """
        self.job_id = job_id
        self.job_number = job_number
        self.start_time = start_time
        self.stop_time = None
        self.error_msg = ""
        self.state = JobState.NOT_STARTED
        self.kafka_offset = kafka_offset
        self.replay_of = None

    @classmethod
    def from_dict(cls, job_dict):
        result = JobRecord("", 0, 0, 0)
        for k, v in job_dict.items():
            if k in result.__dict__:
                result.__dict__[k] = v
        return result

    def as_dict(self):
        return self.__dict__


def incrementFileCounter():
    exp = session.experiment
    if not path.isfile(path.join(exp.dataroot, exp.counterfile)):
        session.log.warning(
            "creating new empty file counter file at %s",
            path.join(exp.dataroot, exp.counterfile),
        )
    counterpath = path.normpath(path.join(exp.dataroot, exp.counterfile))
    nextnum = readFileCounter(counterpath, "file") + 1
    updateFileCounter(counterpath, "file", nextnum)
    return nextnum


def generateMetainfo():
    devices = [
        dev
        for (_, dev) in sorted(
            session.devices.items(), key=lambda name_dev: name_dev[0].lower()
        )
    ]
    metainfo = {}
    for device in devices:
        if "metadata" not in device.visibility:
            continue
        for key, value, strvalue, unit, category in device.info():
            metainfo[device.name, key] = (value, strvalue, unit, category)
    return metainfo


def generate_filepath(file_num):
    proposal = session.experiment.propinfo.get("proposal")
    proposal_path = session.experiment.proposalpath_of(proposal)
    filename = f"{proposal}_{file_num:0>8}.hdf"
    return path.join(proposal_path, filename)


class FileWriterController:
    """Helper class for handling commands being sent to Kafka."""

    def __init__(self, brokers, pool_topic, status_topic, timeout_interval):
        self.brokers = brokers
        self.pool_topic = pool_topic
        self.instrument_topic = status_topic
        self.timeout_interval = timeout_interval * 2
        self.command_channel = None

    def request_start(self, filename, structure, job_id, start_time, stop_time=None):
        if not stop_time:
            stop_time = start_time + timedelta(days=365.25 * 10)

        message = serialise_pl72(
            job_id,
            filename,
            start_time,
            stop_time,
            nexus_structure=structure,
            broker="",
            instrument_name="",
            run_name="",
            control_topic=self.instrument_topic,
        )

        delivered = False
        delivery_info = None

        def on_delivery(err, message):
            nonlocal delivered, delivery_info
            delivered = True
            delivery_info = (message.partition(), message.offset())

        producer = KafkaProducer.create(self.brokers)
        producer.produce(self.pool_topic, message, on_delivery_callback=on_delivery)

        while not delivered:
            time.sleep(0.1)

        return job_id, delivery_info

    def _get_instrument_name(self):
        device = self._check_for_device("NexusStructure")
        if device:
            return device.instrument_name
        self.log.warning("Could not locate instrument name from NexusStructure device")
        return ""

    def _check_for_device(self, name):
        try:
            return session.getDevice(name)
        except ConfigurationError:
            return None

    def request_stop(self, job_id, stop_time):
        message = serialise_6s4t(
            job_id=job_id,
            command_id=str(uuid.uuid1()),
            stop_time=stop_time,
            run_name="",
        )

        delivered = False

        def on_delivery(err, message):
            nonlocal delivered
            delivered = True

        producer = KafkaProducer.create(self.brokers)
        producer.produce(
            self.instrument_topic, message, on_delivery_callback=on_delivery
        )

        while not delivered:
            time.sleep(0.1)


class Filewriter(Moveable):
    parameters = {
        "brokers": Param(
            "List of kafka hosts to be connected",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "pool_topic": Param(
            "The job pool topic for the filewriters",
            type=str,
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "statustopic": Param(
            "Kafka topic(s) where status messages are written",
            type=listof(str),
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "instrument_topic": Param(
            "The instrument specific topic for filewriting",
            type=str,
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "timeoutinterval": Param(
            "Time to wait (secs) before communication is considered failed",
            type=int,
            default=5,
            settable=True,
            userparam=False,
        ),
        "stoptimeout": Param(
            "Time to wait (secs) before stopping writing is considered failed",
            type=int,
            default=10,
            settable=True,
            userparam=False,
        ),
        "job_history": Param(
            description="stores the most recent jobs in the cache",
            type=listof(anytype),
            internal=True,
            settable=True,
        ),
        "job_history_limit": Param(
            description="maximum number of jobs to store in the cache",
            type=int,
            default=10,
            internal=True,
            settable=True,
        ),
        "stored_job": Param(
            description="stores the current job in the cache so it "
            "can be retrieved if NICOS restarts",
            type=none_or(anytype),
            internal=True,
            settable=True,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }

    attached_devices = {
        "nexus": Attach("Supplies the NeXus file structure", NexusStructureProvider),
    }

    _consumer = None
    _message_subscriber = None
    _current_job = None
    _current_job_messages = {}
    _immediate_stop = threading.Event()
    _is_blocking = threading.Event()

    def doPreinit(self, mode):
        if session.sessiontype == POLLER or mode == SIMULATION:
            return
        self._active_sim_job = False
        self._consumer = None
        self._controller = FileWriterController(
            self.brokers,
            self.pool_topic,
            self.instrument_topic,
            self.timeoutinterval,
        )
        self._consumer = KafkaConsumer.create(self.brokers)
        self._consumer.subscribe([self.pool_topic])
        self._message_subscriber = KafkaSubscriber(self.brokers)
        self._message_subscriber.subscribe(
            self.statustopic,
            self._new_messages_callback,
            self._no_messages_callback,
        )

        if self._mode == MASTER:
            self._setROParam("curstatus", (status.WARN, "Trying to connect..."))

    def doInit(self, mode):
        if session.sessiontype == POLLER or mode == SIMULATION:
            return
        self._immediate_stop.clear()
        self._is_blocking.clear()
        self._retrieve_last_job()

    def doRead(self, maxage=0):
        return ""

    def doShutdown(self):
        if self._consumer:
            self._consumer.close()
        if self._message_subscriber:
            self._message_subscriber.close()

    def doStart(self, value):
        pass

    def doIsCompleted(self):
        if self._is_blocking.is_set():
            return False
        return True

    def get_active_job(self):
        return self._current_job

    def doStatus(self, maxage=0):
        return self.curstatus

    def doStop(self):
        self.log.warn("Dostop: immediate stop triggered")
        self._cleanup()

    def _cleanup(self):
        self.log.info("Cleanup: initiating immediate stop cleanup.")

        self._immediate_stop.set()

        if self._current_job is not None:
            try:
                now = datetime.now()
                self.log.info(
                    "Cleanup: sending stop message for job %s", self._current_job.job_id
                )
                self._controller.request_stop(self._current_job.job_id, now)
            except Exception as e:
                self.log.error("Cleanup: error sending stop message: %s", e)

        wait_seconds = 0
        max_wait = self.stoptimeout
        while self._is_blocking.is_set() and wait_seconds < max_wait:
            time.sleep(0.1)
            wait_seconds += 0.1

        if self._current_job is not None:
            self._update_cached_jobs()

        self._is_blocking.clear()
        self._current_job = None
        self.stored_job = None
        self._current_job_messages.clear()

        self.log.info("Cleanup: immediate stop cleanup complete.")

    def start_job(self):
        if self._mode == SIMULATION:
            return

        if self._current_job:
            self.log.warn("file writing already in progress - ignoring start command")
            return

        self._immediate_stop.clear()
        self._check_okay_to_start()

        file_num = incrementFileCounter()
        file_path = generate_filepath(file_num)
        job_id = str(uuid.uuid1())
        metainfo = generateMetainfo()
        metainfo[("Exp", "job_id")] = job_id
        start_time = datetime.now()
        start_time_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(start_time.timestamp())
        )
        metainfo[("dataset", "starttime")] = (
            start_time_str,
            start_time_str,
            "",
            "general",
        )
        structure = self._attached_nexus.get_structure(metainfo, file_num)

        self._is_blocking.set()
        createThread(
            "file_writer_start_job",
            target=self._start_job,
            args=(file_path, file_num, structure),
            kwargs={"start_time": start_time, "job_id": job_id},
            daemon=True,
            start=True,
        )

    def stop_job(self):
        if self._mode == SIMULATION:
            return

        if not self._current_job:
            self.log.warn("no file writing in progress - ignoring stop command")
            return

        self._is_blocking.set()
        createThread(
            "file_writer_stop_job",
            target=self._stop_job,
            daemon=True,
            start=True,
        )

    def list_jobs(self):
        def _state_to_str(job_state):
            return str(job_state).split(".")[1]

        dt_format = "%Y-%m-%d %H:%M:%S"
        headers = ["job", "status", "start time", "stop time", "replay of", "error"]
        funcs = [
            lambda job: str(job["job_number"]),
            lambda job: _state_to_str(job["state"]),
            lambda job: job["start_time"].strftime(dt_format),
            lambda job: job["stop_time"].strftime(dt_format)
            if job["stop_time"]
            else "",
            lambda job: str(job["replay_of"]) if job["replay_of"] else "",
            lambda job: job["error_msg"] if job["error_msg"] else "",
        ]
        if session.daemon_device.current_script().user.level == ADMIN:
            headers.insert(1, "job  GUID")
            funcs.insert(1, lambda job: job["job_id"])
        items = []
        for job in self.job_history:
            items.append([func(job) for func in funcs])
        printTable(headers, items, session.log.info)

    def replay_job(self, job_number):
        if self._mode == SIMULATION:
            return
        if self._current_job:
            self.log.warn("file writing in progress - ignoring replay command")
        self._check_okay_to_start()

        job_to_replay = None
        for job in self.job_history:
            if job["job_number"] == job_number:
                job_to_replay = JobRecord.from_dict(job)
                break

        if not job_to_replay:
            raise RuntimeError(
                "Could not replay job as that job number was " "not found"
            )
        if not job_to_replay.stop_time:
            raise RuntimeError(
                "Could not replay job as no stop time defined " "for that job"
            )

        self.log.warn(f"replaying job {job_number}")
        self._immediate_stop.clear()
        partition, offset = job_to_replay.kafka_offset
        self._consumer.seek(self.pool_topic, partition=partition, offset=offset)
        poll_start = time.monotonic()
        time_out_s = 5
        self.log.warn("seeked to offset")
        while True:
            if self._immediate_stop.is_set():
                return

            self.log.warn("polling")
            data = self._consumer.poll(timeout_ms=5)
            self.log.warn("polled")
            # Because there are multiple partitions, we might not get the message
            # we want immediately. So, we need to check whether the message is the
            # one we are looking for.
            if data and data.partition() == partition and data.offset() == offset:
                break
            if not data and time.monotonic() > poll_start + time_out_s:
                raise RuntimeError(
                    "Could not replay job as could not retrieve job "
                    "information from Kafka"
                )

        self.log.warn("retrieved job information from Kafka")

        message = deserialise_pl72(data.value())

        file_num = incrementFileCounter()
        file_path = generate_filepath(file_num)

        self._is_blocking.set()
        createThread(
            "file_writer_start_job",
            target=self._start_job,
            args=(file_path, file_num, message.nexus_structure),
            kwargs={
                "start_time": job_to_replay.start_time,
                "stop_time": job_to_replay.stop_time,
                "replay_of": job_number,
            },
            daemon=True,
            start=True,
        )

    def _start_job(
        self,
        filename,
        counter,
        structure,
        start_time=None,
        stop_time=None,
        replay_of=None,
        job_id=None,
    ):
        start_time = start_time if start_time else datetime.now()
        job_id = job_id if job_id else str(uuid.uuid1())
        job = JobRecord(job_id, counter, start_time, (-1, -1))
        job.replay_of = replay_of
        job.stop_time = stop_time

        self._current_job = job
        self._current_job_messages = {}

        job_id, kafka_offset = self._controller.request_start(
            filename, structure, job_id, start_time, stop_time
        )
        self._current_job.kafka_offset = kafka_offset
        self.stored_job = self._current_job.as_dict()

        while "start" not in self._current_job_messages:
            if self._immediate_stop.is_set():
                self._is_blocking.clear()
                return
            time.sleep(0.1)

        started, error_msg = self._current_job_messages["start"]

        if started:
            self.log.info("file writing started")
            self._is_blocking.clear()
        else:
            self._is_blocking.clear()
            raise StartWritingRejectedException(error_msg)

    def _stop_job(self):
        job_id = self._current_job.job_id
        stop_time = datetime.now()
        self._current_job.stop_time = stop_time
        self._controller.request_stop(job_id, stop_time)

        timeout = time.monotonic() + self.stoptimeout
        while "stop" not in self._current_job_messages:
            if self._immediate_stop.is_set():
                self.log.warn("immediate stop, returning out of stop loop")
                self._is_blocking.clear()
                return
            if time.monotonic() > timeout:
                self._current_job_messages["stop"] = (
                    False,
                    "timed out waiting for stop to be acknowledged",
                )
                self._is_blocking.clear()
                break
            time.sleep(0.2)

        stopped, error_msg = self._current_job_messages["stop"]

        if stopped:
            self.log.info("file writing stopped")
            self._current_job.state = JobState.WRITTEN
        else:
            self.log.error(
                f"there was an issue with stopping file writing: {error_msg}"
            )
            self._current_job.state = JobState.FAILED
            self._current_job.error_msg = error_msg

        self._update_cached_jobs()
        self._current_job = None
        self.stored_job = None
        self._current_job_messages = {}
        self._is_blocking.clear()

    def _new_messages_callback(self, messages):
        self._setROParam("curstatus", self._get_curstatus())

        for _, msg in sorted(messages, key=lambda x: x[0]):
            self.log.error(msg[4:8])
            schema = msg[4:8]
            if schema == b"wrdn":
                self._on_writing_finished(msg)

        if not self._current_job:
            return

        for _, msg in sorted(messages, key=lambda x: x[0]):
            self.log.error(msg[4:8])
            schema = msg[4:8]
            if schema == b"x5f2":
                self._on_status_message(msg)
            elif schema == b"answ":
                self._on_response_message(msg)

    def _no_messages_callback(self):
        pass

    def _get_curstatus(self):
        if not self._current_job:
            return status.OK, ""

        if (
            "start" in self._current_job_messages
            and "stop" not in self._current_job_messages
        ):
            started, error_msg = self._current_job_messages["start"]
            if not started:
                return status.ERROR, error_msg
            return status.BUSY, "writing..."
        elif "stop" in self._current_job_messages:
            stopped, error_msg = self._current_job_messages["stop"]
            if not stopped:
                return status.ERROR, error_msg
            return status.BUSY, "finishing up..."

        return status.UNKNOWN, "Unknown status"

    def _on_status_message(self, message):
        msg = deserialise_x5f2(message)
        status_info = json.loads(msg.status_json)
        if status_info["job_id"] == self._current_job.job_id:
            self._current_job_messages["status"] = status_info

    def _on_response_message(self, message):
        self.log.warn("on_response")
        result = deserialise_answ(message)
        self.log.warn(f"{result.job_id}")
        self.log.warn(result)
        if result.job_id != self._current_job.job_id:
            return

        if result.action == ActionType.StartJob:
            self.log.warn(f"on_start_response {result}")
            self._on_start_response(result)
        elif result.action == ActionType.SetStopTime:
            self.log.warn(f"on_stopt_response {result}")
            self._on_stop_response(result)

    def _on_start_response(self, result):
        if result.outcome == ActionOutcome.Success:
            self._current_job_messages["start"] = (True, "")
            self._current_job.state = JobState.STARTED
        else:
            self._current_job_messages["start"] = (False, result.message)
            self._current_job.state = JobState.REJECTED
            self._update_cached_jobs()

    def _on_stop_response(self, result):
        if not self._current_job.stop_time:
            self._current_job_messages["stop"] = (
                False,
                "file writing was stopped by a third-party (i.e. not NICOS)",
            )
            return

        if result.outcome == ActionOutcome.Success:
            self._current_job_messages["stop"] = (True, "")
        else:
            self._current_job_messages["stop"] = (False, result.message)

    def _on_writing_finished(self, message):
        result = deserialise_wrdn(message)

        if not self._current_job:
            self._update_historical_jobs(result)
            return

        self.log.warn(result)
        if result.error_encountered:
            self._current_job_messages["written"] = (False, result.message)
        else:
            self._current_job_messages["written"] = (True, "")

        stopped, error_msg = self._current_job_messages.get("stop", (False, ""))

        if stopped:
            self.log.info("file writing stopped")
            self._current_job.state = JobState.WRITTEN
        else:
            written, written_error_msg = self._current_job_messages.get(
                "written", (False, "")
            )
            if written:
                self.log.info("file writing finished")
                self._current_job.state = JobState.WRITTEN
            else:
                self.log.error(
                    f"there was an issue with stopping file writing: {error_msg}"
                )
                self._current_job.state = JobState.FAILED
                self._current_job.error_msg = error_msg

        self._update_cached_jobs()
        self._current_job = None
        self.stored_job = None
        self._current_job_messages = {}
        self._is_blocking.clear()

    def _update_historical_jobs(self, finished_job):
        job_id = finished_job.job_id
        for job in self.job_history:
            if job["state"] == JobState.WRITTEN:
                continue

            if job["job_id"] == job_id:
                job["state"] = JobState.WRITTEN
                job["stop_time"] = datetime.now()
                job["error_msg"] = finished_job.message
                break

    def _check_okay_to_start(self):
        if not session.experiment.propinfo.get("proposal"):
            raise RuntimeError("cannot start writing as proposal number not set")

    def _retrieve_last_job(self):
        if self.stored_job:
            self._current_job = JobRecord.from_dict(self.stored_job)

    def _update_cached_jobs(self):
        temp = [x for x in self.job_history]
        temp.append(self._current_job.as_dict())
        while len(temp) > self.job_history_limit:
            temp.pop(0)
        self.job_history = temp

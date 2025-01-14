import copy
import json
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta
from enum import Enum
from os import path
from time import time as currenttime

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
    MASTER,
    Attach,
    Param,
    host,
    listof,
    status,
    ConfigurationError,
)
from nicos.core.constants import SIMULATION
from nicos.core.device import Device
from nicos.core.params import anytype
from nicos.utils import printTable, readFileCounter, updateFileCounter

from nicos_ess.devices.datasinks.nexus_structure import NexusStructureProvider
from nicos_ess.devices.kafka.consumer import KafkaConsumer
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler


class AlreadyWritingException(Exception):
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
        self.update_interval = 0
        self.next_update = 0
        self.start_time = start_time
        self.stop_time = None
        self.error_msg = ""
        self.state = JobState.NOT_STARTED
        self.kafka_offset = kafka_offset
        self.service_id = ""
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

    def on_writing(self, update_interval):
        self.set_next_update(update_interval)
        self.state = JobState.STARTED
        self.error_msg = ""

    def set_next_update(self, update_interval):
        self.update_interval = update_interval // 1000
        self.next_update = currenttime() + self.update_interval

    def set_error_msg(self, error_msg):
        # Only record the first error message as the rest will be related
        if not self.error_msg:
            self.error_msg = error_msg

    def start_rejected(self, error_msg):
        self.state = JobState.REJECTED
        self.set_error_msg(error_msg)

    def on_stop(self):
        self.state = JobState.WRITTEN

    def on_lost(self, error_msg):
        self.state = JobState.FAILED
        self.set_error_msg(error_msg)

    def is_overdue(self, leeway):
        return (
            self.state == JobState.STARTED and currenttime() > self.next_update + leeway
        )

    def stop_request(self, stop_time):
        self.stop_time = stop_time

    @property
    def stop_requested(self):
        return self.stop_time is not None

    def get_state_string(self):
        return str(self.state).split(".")[1]


class FileWriterStatus(KafkaStatusHandler):
    """Monitors Kafka for the status of any file-writing jobs."""

    parameters = {
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
    }

    def doPreinit(self, mode):
        KafkaStatusHandler.doPreinit(self, mode)
        self._lock = threading.RLock()
        self._jobs = {}
        self._jobs_in_order = OrderedDict()
        self._update_status()
        self._type_to_handler = {
            b"x5f2": self._on_status_message,
            b"answ": self._on_response_message,
            b"wrdn": self._on_stopped_message,
        }

    def doInit(self, mode):
        self._retrieve_cache_jobs()

    def _retrieve_cache_jobs(self):
        for v in self.job_history:
            job = JobRecord.from_dict(v)
            self._jobs_in_order[job.job_id] = job
            self.log.warn(f"job id {job.job_id}, job state {job.state}")
            if not job.stop_requested and job.state != JobState.REJECTED:
                # Assume it is still in progress.
                # Update the timeout so it doesn't time out immediately
                job.set_next_update(job.update_interval)
                self._jobs[job.job_id] = job

    def _update_cached_jobs(self):
        self.job_history = [
            self._jobs_in_order[k].as_dict()
            for k in list(self._jobs_in_order.keys())[-self.job_history_limit :]
        ]

    def new_messages_callback(self, messages):
        for _, msg in sorted(messages, key=lambda x: x[0]):
            if msg[4:8] in self._type_to_handler:
                with self._lock:
                    self._type_to_handler[msg[4:8]](msg)

    def _on_status_message(self, message):
        result = deserialise_x5f2(message)
        status_info = json.loads(result.status_json)
        job_id = status_info["job_id"]
        if job_id not in self._jobs:
            return
        self._jobs[job_id].on_writing(result.update_interval)
        self._update_status()

    def _job_stopped(self, job_id):
        if self._jobs[job_id].error_msg:
            session.log.error(
                "Job #%s failed to write successfully, "
                "run `list_filewriting_jobs` for more details",
                self._jobs[job_id].job_number,
            )
        del self._jobs[job_id]

    def _on_stopped_message(self, message):
        result = deserialise_wrdn(message)
        if result.job_id not in self._jobs:
            return
        session.log.warn(f"stop message={result}")

        if result.error_encountered:
            self._jobs[result.job_id].on_lost(result.message)
            if self._jobs[result.job_id].stop_requested:
                # User requested a stop and something went wrong
                self._job_stopped(result.job_id)
        else:
            self._jobs[result.job_id].on_stop()
            self._job_stopped(result.job_id)
        self._update_cached_jobs()
        self._update_status()

    def _on_response_message(self, message):
        result = deserialise_answ(message)
        if result.job_id not in self._jobs:
            return

        if result.action == ActionType.StartJob:
            self._on_start_response(result)
        elif result.action == ActionType.SetStopTime:
            self._on_stop_response(result)

    def _on_start_response(self, result):
        if result.outcome == ActionOutcome.Success:
            self.log.warn(
                "request to start writing succeeded for job %s", result.job_id
            )
            self._jobs[result.job_id].on_writing(self.statusinterval)
            self._jobs[result.job_id].service_id = result.service_id
        else:
            self.log.warn("request to start writing failed for job %s", result.job_id)
            self._jobs[result.job_id].start_rejected(result.message)

    def _on_stop_response(self, result):
        if not self._jobs[result.job_id].stop_requested:
            self.log.warning("stop requested from external agent for %s", result.job_id)

        if result.outcome == ActionOutcome.Success:
            self.log.debug(
                "request to stop writing succeeded for job %s", result.job_id
            )
        else:
            self.log.debug("request to stop writing failed for job %s", result.job_id)
            self._jobs[result.job_id].set_error_msg(result.message)
        session.log.warn(f"on stop message={result}")

    def no_messages_callback(self):
        with self._lock:
            self._check_for_lost_jobs()
            self._update_status()

    def _check_for_lost_jobs(self):
        overdue_jobs = [
            k for k, v in self._jobs.items() if v.is_overdue(self.timeoutinterval)
        ]
        for overdue in overdue_jobs:
            self._jobs[overdue].on_lost("lost connection to job")
            if self._jobs[overdue].stop_time:
                # Sent stop command before lost
                self._job_stopped(overdue)
        if overdue_jobs:
            self._update_cached_jobs()

    def doInfo(self):
        result = [(f"{self.name}", "", "", "", "general")]
        for i, job in enumerate(self._jobs):
            result.append((f"job {i + 1}", f"{job}", f"{job}", "", "general"))
        return result

    def _update_status(self):
        new_status = (status.OK, "")
        if len(self._jobs) > 0:
            new_status = (status.BUSY, "recording data")
        if new_status != self.curstatus:
            self._set_status(new_status)

    def _set_status(self, new_status):
        if self._mode == MASTER:
            self._setROParam("curstatus", new_status)
            if self._cache:
                self._cache.put(self._name, "status", new_status, currenttime())

    @property
    def jobs_in_progress(self):
        with self._lock:
            return set(self._jobs.keys())

    @property
    def marked_for_stop(self):
        with self._lock:
            return {k for k, v in self._jobs.items() if v.stop_requested}

    def mark_for_stop(self, job_id, stop_time):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].stop_request(stop_time)
                if self._jobs[job_id].state not in (
                    JobState.NOT_STARTED,
                    JobState.STARTED,
                ):
                    self._job_stopped(job_id)
                self._update_cached_jobs()

    def add_job(self, job):
        with self._lock:
            job.set_next_update(self.statusinterval)
            self._jobs[job.job_id] = job
            self._jobs_in_order[job.job_id] = job
            self._update_cached_jobs()

    @property
    def jobs(self):
        return copy.deepcopy(self._jobs)


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


class FileWriterController:
    """Helper class for handling commands being sent to Kafka."""

    def __init__(self, brokers, pool_topic, status_topic, timeout_interval):
        self.brokers = brokers
        self.pool_topic = pool_topic
        self.instrument_topic = status_topic
        self.timeout_interval = timeout_interval * 2
        self.command_channel = None

    def request_start(
        self, filename, structure, start_time, stop_time=None, job_id=None
    ):
        if not job_id:
            job_id = str(uuid.uuid1())

        if not stop_time:
            stop_time = start_time + timedelta(days=365.25 * 10)

        message = serialise_pl72(
            job_id,
            filename,
            start_time,
            stop_time,
            nexus_structure=structure,
            broker="",
            instrument_name=self._get_instrument_name(),
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

    def request_stop(self, job_id, stop_time, service_id):
        message = serialise_6s4t(
            job_id=job_id,
            command_id=str(uuid.uuid1()),
            service_id=service_id,
            stop_time=stop_time,
            run_name="",
        )

        producer = KafkaProducer.create(self.brokers)
        producer.produce(self.instrument_topic, message)


class FileWriterControlSink(Device):
    """Sink for the NeXus file-writer"""

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
    }

    attached_devices = {
        "status": Attach("The file-writer status device", FileWriterStatus),
        "nexus": Attach("Supplies the NeXus file structure", NexusStructureProvider),
    }

    def doInit(self, mode):
        self._active_sim_job = False
        self._consumer = None
        self._controller = FileWriterController(
            self.brokers,
            self.pool_topic,
            self.instrument_topic,
            self.timeoutinterval,
        )
        if mode != SIMULATION:
            self._consumer = KafkaConsumer.create(self.brokers)
            self._consumer.subscribe([self.pool_topic])

    def start_job(self):
        """Start a new file-writing job."""
        self.check_okay_to_start()
        if self._mode == SIMULATION:
            self._active_sim_job = True
        else:
            file_num = incrementFileCounter()
            file_path = self._generate_filepath(file_num)
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
            self._start_job(
                file_path, file_num, structure, start_time=start_time, job_id=job_id
            )
        self.log.info("Filewriting started")

    def _generate_filepath(self, file_num):
        proposal = session.experiment.propinfo.get("proposal")
        proposal_path = session.experiment.proposalpath_of(proposal)
        filename = f"{proposal}_{file_num:0>8}.hdf"
        return path.join(proposal_path, filename)

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
        job_id, commit_info = self._controller.request_start(
            filename, structure, start_time, stop_time, job_id
        )
        job = JobRecord(job_id, counter, start_time, commit_info)
        job.replay_of = replay_of
        job.stop_time = stop_time
        self._attached_status.add_job(job)

        while self._attached_status.jobs[job_id].state == JobState.NOT_STARTED:
            time.sleep(0.5)
        if self._attached_status.jobs[job_id].state == JobState.STARTED:
            self.log.error("job started")
        elif self._attached_status.jobs[job_id].state == JobState.REJECTED:
            self.log.error(self._attached_status.jobs[job_id].error_msg)
            self._attached_status._job_stopped(job_id)
        elif self._attached_status.jobs[job_id].state == JobState.FAILED:
            self.log.error("job failed")

    def stop_job(self, job_number=None):
        """Stop a file-writing job.

        :param job_number: the particular job to stop. Only required if there
            is more than one job running.
        """
        if self._mode == SIMULATION:
            self._active_sim_job = False
        else:
            self._stop_job(job_number)
        self.log.info("Filewriting stopped")

    def _stop_job(self, job_number=None):
        job_id = ""
        if job_number:
            for job in self._attached_status.jobs.values():
                if job.job_number == job_number:
                    job_id = job.job_id
                    break
            if not job_id:
                self.log.error(
                    "supplied job number is not recognised. "
                    "Already stopped or perhaps a typo?"
                )
                return

        if job_id and job_id in self._attached_status.marked_for_stop:
            # Already stopping so ignore
            return

        active_jobs = self.get_active_jobs()
        if not active_jobs:
            return

        if len(active_jobs) == 1:
            job_id = list(active_jobs)[0]
        elif len(active_jobs) > 1 and not job_id:
            self.log.error(
                "more than one job being written, rerun the command "
                "with the job ID specified in quotes"
            )
            return

        stop_time = datetime.now()
        job = self._attached_status.jobs[job_id]
        self._controller.request_stop(job.job_id, stop_time, job.service_id)
        self._attached_status.mark_for_stop(job_id, stop_time)

    def check_okay_to_start(self):
        if not session.experiment.propinfo.get("proposal"):
            if self._mode == SIMULATION:
                self.log.warning(
                    "no proposal number has been set. "
                    "When performing the real run a proposal "
                    "number is required to start writing."
                )
            else:
                raise RuntimeError("cannot start writing as proposal number not " "set")
        active_jobs = self.get_active_jobs()
        if active_jobs:
            raise AlreadyWritingException(
                "cannot start writing as writing " "already in progress"
            )

    def get_active_jobs(self):
        if self._mode == SIMULATION:
            if self._active_sim_job:
                return ["abcd1234-abcd-1234-abcd-abcdef123456"]
            return []
        jobs = self._attached_status.jobs_in_progress
        active_jobs = self._attached_status.marked_for_stop.symmetric_difference(jobs)
        return active_jobs

    def list_jobs(self):
        dt_format = "%Y-%m-%d %H:%M:%S"
        headers = ["job", "status", "start time", "stop time", "replay of", "error"]
        funcs = [
            lambda job: str(job.job_number),
            lambda job: job.get_state_string(),
            lambda job: job.start_time.strftime(dt_format),
            lambda job: job.stop_time.strftime(dt_format) if job.stop_time else "",
            lambda job: str(job.replay_of) if job.replay_of else "",
            lambda job: job.error_msg if job.error_msg else "",
        ]
        if session.daemon_device.current_script().user.level == ADMIN:
            headers.insert(1, "job  GUID")
            funcs.insert(1, lambda job: job.job_id)
        items = []
        for job in self._attached_status._jobs_in_order.values():
            items.append([func(job) for func in funcs])
        printTable(headers, items, session.log.info)

    def replay_job(self, job_number):
        if self._mode == SIMULATION:
            return
        self.check_okay_to_start()

        job_to_replay = None
        for job in self._attached_status._jobs_in_order.values():
            if job.job_number == job_number:
                job_to_replay = job
                break
        if not job_to_replay:
            raise RuntimeError(
                "Could not replay job as that job number was " "not found"
            )
        if not job_to_replay:
            raise RuntimeError(
                "Could not replay job as no stop time defined " "for that job"
            )

        partition, offset = job_to_replay.kafka_offset
        self._consumer.seek(self.pool_topic, partition=partition, offset=offset)
        poll_start = time.monotonic()
        data = self._consumer.poll(timeout_ms=5)
        time_out_s = 5
        while not data:
            data = self._consumer.poll(timeout_ms=5)
            if not data and time.monotonic() > poll_start + time_out_s:
                raise RuntimeError(
                    "Could not replay job as could not retrieve job "
                    "information from Kafka"
                )

        message = deserialise_pl72(data.value())

        file_num = incrementFileCounter()
        file_path = self._generate_filepath(file_num)
        self._start_job(
            file_path,
            file_num,
            message.nexus_structure,
            job_to_replay.start_time,
            job_to_replay.stop_time,
            job_number,
        )

    def doShutdown(self):
        if self._consumer:
            self._consumer.close()

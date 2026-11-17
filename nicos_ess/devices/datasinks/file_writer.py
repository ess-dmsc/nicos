"""Device that controls and monitors the external file writers through Kafka."""

import json
import threading
import time
import uuid
from datetime import datetime
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
    MASTER,
    POLLER,
    SIMULATION,
    Attach,
    ConfigurationError,
    Override,
    Param,
    listof,
    status,
)
from nicos.utils import printTable, readFileCounter, updateFileCounter
from nicos_ess.devices.datasinks.nexus_structure import NexusStructureProvider
from nicos_ess.devices.kafka.consumer import KafkaConsumer
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.devices.kafka.status_handler import KafkaStatusHandler

# When stoptime is not defined use an easily recognisable timestamp
# far far in the future.
LATE_OCT_2191 = datetime.fromtimestamp(7_000_000_000)
HISTORY_LENGTH = 10
DELIVERY_TIMEOUT = 10
STOP_ANSWER_TIMEOUT = 10
NOT_STARTED, STARTED, WRITTEN = "NOT_STARTED", "STARTED", "WRITTEN"
REJECTED, FAILED, LOST = "REJECTED", "FAILED", "LOST"


class AlreadyWritingException(Exception):
    """Raised when a new job is requested while another job is active."""


class FileWriterStartError(Exception):
    pass


def incrementFileCounter():
    exp = session.experiment
    counterpath = path.normpath(path.join(exp.dataroot, exp.counterfile))
    if not path.isfile(counterpath):
        session.log.warning("creating new empty file counter file at %s", counterpath)
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
        try:
            info = device.info()
        except Exception as err:
            device.log.warning("could not collect metadata, skipping", exc=err)
            continue
        for key, parinfo in info:
            metainfo[device.name, key] = parinfo
    return metainfo


def _daemon_controller():
    return getattr(getattr(session, "daemon_device", None), "_controller", None)


def _for_each_filewriter(method, *args):
    for dev in list(session.devices.values()):
        if isinstance(dev, FileWriter) and dev._mode != SIMULATION:
            getattr(dev, method)(*args)


def _hook_into_daemon(controller):
    """Stop files on an immediate stop and when their script fails."""
    if getattr(controller.eventfunc, "file_writer_hook", False):
        return False
    controller.add_estop_function(_for_each_filewriter, ("stop_jobs", "immediate stop"))
    emit = controller.eventfunc

    def eventfunc(event, data):
        emit(event, data)
        if event != "done":
            return
        try:
            if data.get("success"):
                _for_each_filewriter("release_jobs", data.get("reqid"))
            else:
                reason = "the script did not finish"
                _for_each_filewriter("stop_jobs", reason, data.get("reqid"))
        except Exception:
            session.log.exception("file writer: handling the end of a script failed")

    eventfunc.file_writer_hook = True
    controller.eventfunc = eventfunc
    return True


def _command_id(job_id):
    # the format main always sent: a deployed file writer rejected uuid4 ids
    digits = job_id.replace("-", "")[:12] + "5" + "0" * 11 + uuid.uuid1().hex[:8]
    return str(uuid.UUID(digits[:16] + "8" + digits[17:]))


def _stop_message(job, stop_time):
    return serialise_6s4t(
        job_id=job["id"],
        command_id=_command_id(job["id"]),
        service_id=job["service"],
        stop_time=stop_time,
        run_name="",
    )


def _stoppable(job):
    return job["stop"] is None and job["state"] in (NOT_STARTED, STARTED, LOST)


class FileWriter(KafkaStatusHandler):
    """Start and stop file writing jobs and follow them on the status topics."""

    parameters = {
        "pool_topic": Param(
            "The job pool topic for the filewriters",
            type=str,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "instrument_topic": Param(
            "The instrument specific topic for filewriting",
            type=str,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "starttimeout": Param(
            "Time (secs) a file writer has to take a new job",
            type=int,
            default=60,
            settable=True,
            userparam=False,
        ),
        "jobs": Param(
            "The most recent jobs, kept in the cache",
            type=listof(dict),
            internal=True,
            settable=True,
        ),
    }

    parameter_overrides = {
        "curstatus": Override(default=(status.OK, "")),
    }

    attached_devices = {
        "nexus": Attach("Supplies the NeXus file structure", NexusStructureProvider),
    }

    def doPreinit(self, mode):
        self._lock = threading.RLock()
        self._jobs = {}
        self._sim_job = False
        KafkaStatusHandler.doPreinit(self, mode)

    def doInit(self, mode):
        if self.instrument_topic not in self.statustopic:
            raise ConfigurationError(self, "statustopic must contain instrument_topic")
        with self._lock:
            for job in self.jobs:
                job = dict(job)
                if "id" not in job or job["id"] in self._jobs:
                    continue
                if job["state"] in (NOT_STARTED, STARTED):
                    job["state"] = LOST
                self._jobs[job["id"]] = job
        if mode == SIMULATION or session.sessiontype == POLLER:
            return
        self._producer = KafkaProducer.create(
            self.brokers, **{"message.timeout.ms": DELIVERY_TIMEOUT * 1000}
        )
        controller = _daemon_controller()
        if controller is not None and _hook_into_daemon(controller):
            alive = (None, controller.reqid_work)
            for job in self._copy_jobs():
                if _stoppable(job) and job["script"] not in alive:
                    self._stop_safely(job, "the daemon restarted during its script")

    def new_messages_callback(self, messages):
        with self._lock:
            for _, message in messages:
                try:
                    self._on_message(message)
                except Exception as err:
                    self.log.warning("could not handle a status message: %s", err)
            self.no_messages_callback()

    def no_messages_callback(self):
        with self._lock:
            now = time.time()
            for job in self._jobs.values():
                if job["state"] == NOT_STARTED and now > job["deadline"]:
                    self._end(job, LOST, "no file writer took the job")
                elif job["state"] == STARTED and now > job["deadline"]:
                    self._end(job, LOST, "no status from the file writer")
            writing = any(
                job["state"] in (NOT_STARTED, STARTED) for job in self._jobs.values()
            )
            new_status = (status.BUSY, "recording data") if writing else (status.OK, "")
            if self._mode == MASTER and new_status != self.curstatus:
                self._setROParam("curstatus", new_status)
                if self._cache:
                    self._cache.put(self._name, "status", new_status, time.time())

    def _on_message(self, message):
        kind = message[4:8]
        if kind == b"x5f2":
            result = deserialise_x5f2(message)
            try:
                job_id = json.loads(result.status_json).get("job_id")
            except (ValueError, AttributeError):
                return
            self._writing(job_id, result.update_interval / 1000)
        elif kind == b"answ":
            result = deserialise_answ(message)
            job = self._jobs.get(result.job_id)
            if job is None:
                return
            start = result.action == ActionType.StartJob
            if result.outcome == ActionOutcome.Success and start:
                job["service"] = result.service_id
                self._writing(job["id"], self.statusinterval)
            elif result.outcome == ActionOutcome.Success:
                job.update(stop_confirmed=True, stop_wanted=False)
            elif start:
                self._end(job, REJECTED, result.message)
            elif job["state"] in (NOT_STARTED, STARTED):
                self.log.error("job #%s: %s", job["number"], result.message)
        elif kind == b"wrdn":
            result = deserialise_wrdn(message)
            job = self._jobs.get(result.job_id)
            if job is not None and job["state"] in (NOT_STARTED, STARTED, LOST):
                if result.error_encountered:
                    self._end(job, FAILED, result.message)
                else:
                    job["error"] = ""
                    self._end(job, WRITTEN)

    def _writing(self, job_id, interval):
        job = self._jobs.get(job_id)
        if job is None or job["state"] not in (NOT_STARTED, STARTED, LOST):
            return
        if job["state"] == LOST and job["error"]:
            self.log.warning("a file writer reports on job #%s again", job["number"])
        job["deadline"] = time.time() + interval + self.timeoutinterval
        if job.get("stop_wanted") and self._mode == MASTER:
            self._send_stop_again(job)
        if job["state"] != STARTED:
            job.update(state=STARTED, error="")
            self._save()

    def _send_stop_again(self, job):
        if time.time() < job.get("resent", 0) + STOP_ANSWER_TIMEOUT:
            return
        stop_time = datetime.now()
        job.update(stop=stop_time.timestamp(), resent=time.time())
        message = _stop_message(job, stop_time)
        # do not block the thread that reads the answer
        self._producer.produce(self.instrument_topic, message, auto_flush=False)
        self.log.warning("job #%s: sent the stop again", job["number"])
        self._save()

    def _end(self, job, state, error=""):
        job["state"] = state
        if error:
            job["error"] = error
            self.log.error("job #%s: %s", job["number"], error)
        self._save()

    def _save(self):
        if self._mode == MASTER:
            jobs = list(self._jobs.values())[-HISTORY_LENGTH:]
            self.jobs = [dict(job) for job in jobs]

    def _copy_jobs(self):
        with self._lock:
            return [dict(job) for job in self._jobs.values()]

    def _update(self, job_id, **values):
        with self._lock:
            self._jobs[job_id].update(values)
            self._save()
            self.no_messages_callback()

    def start_job(self):
        """Start a new file-writing job."""
        self.check_okay_to_start()
        if self._mode == SIMULATION:
            self._sim_job = True
        else:
            file_num = incrementFileCounter()
            job_id = self._generate_uuid(file_num)
            metainfo = generateMetainfo()
            metainfo[("Exp", "job_id")] = job_id
            start_time = datetime.now()
            start = start_time.strftime("%Y-%m-%d %H:%M:%S")
            metainfo[("dataset", "starttime")] = (start, start, "", "general")
            structure = self._attached_nexus.get_structure(metainfo, file_num)
            self._start_job(file_num, job_id, structure, start_time)
        self.log.info("Filewriting started")

    def _start_job(
        self, counter, job_id, structure, start_time, stop_time=None, replay_of=None
    ):
        message = serialise_pl72(
            job_id,
            self._generate_filepath(counter),
            start_time,
            stop_time or LATE_OCT_2191,
            nexus_structure=structure,
            broker="",
            instrument_name=self._get_instrument_name(),
            run_name="",
            control_topic=self.instrument_topic,
        )
        job = {
            "id": job_id,
            "number": counter,
            "state": NOT_STARTED,
            "start": start_time.timestamp(),
            "stop": stop_time.timestamp() if stop_time else None,
            "error": "",
            "service": "",
            "offset": None,
            "replay_of": replay_of,
            "script": getattr(_daemon_controller(), "reqid_work", None),
            "deadline": time.time() + self.starttimeout + self.timeoutinterval,
        }
        with self._lock:  # the answer can arrive before _send returns
            self._jobs[job_id] = job
        try:
            self._update(job_id, offset=self._send(self.pool_topic, message))
            if not self._wait(
                job_id, lambda job: job["state"] != NOT_STARTED, self.starttimeout
            ):
                raise FileWriterStartError(
                    f"no file writer took job #{counter} within "
                    f"{self.starttimeout} s: is a file writer running?"
                )
        except BaseException as err:
            # a paused broker can deliver the request later
            self._update(job_id, state=LOST, error=str(err) or "start failed")
            self._stop_safely(self._job(job_id), "start failed")
            raise
        job = self._job(job_id)
        if job["state"] in (REJECTED, FAILED, LOST):
            raise FileWriterStartError(f"job #{counter} {job['state']}: {job['error']}")

    def _job(self, job_id):
        with self._lock:
            return dict(self._jobs[job_id])

    def _wait(self, job_id, until, timeout):
        deadline = time.monotonic() + timeout
        while not until(self._job(job_id)):
            if time.monotonic() > deadline:
                return False
            session.delay(0.1)
        return True

    def _generate_filepath(self, file_num):
        proposal = session.experiment.propinfo.get("proposal")
        proposal_path = session.experiment.proposalpath_of(proposal)
        instr_name = ""
        device_name = self._get_instrument_name().lower()
        if device_name:
            if device_name != session.instrument.instrument.lower():
                instr_name = f"{session.instrument.instrument.lower()}_"
            instr_name += f"{device_name}_"
        filename = f"{instr_name}{proposal}_{file_num:0>8}.hdf"
        return path.join(proposal_path, filename)

    def _get_instrument_name(self):
        return getattr(self._attached_nexus, "instrument_name", "")

    def _generate_uuid(self, file_num=""):
        proposal_str = f"{session.experiment.propinfo.get('proposal'):0>6}"[-6:]
        file_num_str = f"{file_num:0>6}"[-6:]
        # set version to name-based SHA1 hash (constructed)
        prefix = f"{proposal_str}{file_num_str}5"
        random_uuid = uuid.uuid1().hex
        generated_str = prefix + random_uuid[: len(random_uuid) - len(prefix)]
        # set specific variant accepted as RFC 4122 for k2n verification
        return str(uuid.UUID(generated_str[:16] + "8" + generated_str[17:]))

    def _send(self, topic, message):
        delivered = []
        self._producer.produce(
            topic,
            message,
            on_delivery_callback=lambda err, msg: delivered.append((err, msg)),
            flush_timeout=DELIVERY_TIMEOUT + 5,
        )
        if not delivered or delivered[0][0]:
            reason = delivered[0][0] if delivered else "no answer"
            raise RuntimeError(f"could not send to Kafka topic {topic}: {reason}")
        msg = delivered[0][1]
        return [msg.partition(), msg.offset()]

    def _stop(self, job):
        stop_time = datetime.now()
        message = _stop_message(job, stop_time)
        # the answer can arrive before _send returns
        self._update(
            job["id"],
            stop=stop_time.timestamp(),
            stop_confirmed=False,
            stop_wanted=False,
        )
        try:
            self._send(self.instrument_topic, message)
        except Exception:
            self._update(job["id"], stop=job["stop"], stop_wanted=True)
            raise

    def _stop_safely(self, job, reason):
        try:
            self._stop(job)
        except Exception as err:
            number = job["number"]
            self.log.error(
                f"{reason}: could not stop file job #{number} ({err}), "
                f"stop it with stop_filewriting({number})"
            )
        else:
            self.log.warning("%s: stopped file job #%s", reason, job["number"])

    def stop_job(self, job_number=None):
        """Stop a file-writing job.

        :param job_number: the particular job to stop. Only required if there
            is more than one job running.
        """
        if self._mode == SIMULATION:
            self._sim_job = False
            self.log.info("Filewriting stopped")
            return
        jobs = [
            job
            for job in self._copy_jobs()
            if _stoppable(job) or (job_number is not None and job["state"] == STARTED)
        ]
        if job_number is not None:
            jobs = [job for job in jobs if str(job["number"]) == str(job_number)]
            if not jobs:
                self.log.error("job %s is not being written", job_number)
                return
        jobs = [job for job in jobs if job["state"] == STARTED] or jobs
        if len(jobs) > 1:
            numbers = [job["number"] for job in jobs]
            self.log.error(
                f"more than one job being written {numbers}, rerun the "
                f"command with the job number, e.g. stop_filewriting({numbers[-1]})"
            )
            return
        if not jobs:
            return
        self._stop(jobs[0])

        def confirmed(job):
            return job.get("stop_confirmed") or job["state"] in (WRITTEN, FAILED)

        if self._wait(jobs[0]["id"], confirmed, STOP_ANSWER_TIMEOUT):
            self.log.info("Filewriting stopped")
        else:
            self.log.warning("stop sent, but no file writer confirmed it")

    def stop_jobs(self, reason, script=None):
        for job in self._copy_jobs():
            if _stoppable(job) and script in (None, job["script"]):
                self._stop_safely(job, reason)

    def release_jobs(self, script):
        with self._lock:
            for job in self._jobs.values():
                if job["script"] == script:
                    job["script"] = None
            self._save()

    def check_okay_to_start(self):
        if not session.experiment.propinfo.get("proposal"):
            if self._mode == SIMULATION:
                self.log.warning("no proposal number has been set")
            else:
                raise RuntimeError("cannot start writing as proposal number not set")
        if self.get_active_jobs():
            raise AlreadyWritingException(
                "cannot start writing as writing already in progress"
            )

    def get_active_jobs(self):
        if self._mode == SIMULATION:
            return ["abcd1234-abcd-1234-abcd-abcdef123456"] if self._sim_job else []
        return [
            job["id"]
            for job in self._copy_jobs()
            if job["state"] == STARTED and job["stop"] is None
        ]

    def list_jobs(self, n=None):
        def fmt(timestamp):
            if not timestamp:
                return ""
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

        admin = session.daemon_device.current_script().user.level == ADMIN
        headers = ["job", "job  GUID"][: 1 + admin]
        headers += ["status", "start time", "stop time", "replay of", "error"]
        rows = [
            [str(job["number"])]
            + [job["id"]] * admin
            + [job["state"], fmt(job["start"]), fmt(job["stop"])]
            + [str(job["replay_of"] or ""), job["error"]]
            for job in self._copy_jobs()[-max(int(n or 0), 0) :]
        ]
        printTable(headers, rows, self.log.info)

    def replay_job(self, job_number):
        if self._mode == SIMULATION:
            return
        self.check_okay_to_start()
        job = next(
            (j for j in self._copy_jobs() if str(j["number"]) == str(job_number)), None
        )
        if not job:
            raise RuntimeError("Could not replay job as that job number was not found")
        if not job["stop"] or not job["offset"]:
            raise RuntimeError("Could not replay job as it was not finished")

        partition, offset = job["offset"]
        consumer = KafkaConsumer.create(self.brokers)
        try:
            consumer.subscribe([self.pool_topic])
            consumer.seek(self.pool_topic, partition=partition, offset=offset)
            deadline = time.monotonic() + 5
            while True:
                # there are several partitions
                data = consumer.poll(timeout_ms=5)
                if data and data.partition() == partition and data.offset() == offset:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        "Could not replay job as could not retrieve job "
                        "information from Kafka"
                    )
        finally:
            consumer.close()

        file_num = incrementFileCounter()
        self._start_job(
            file_num,
            self._generate_uuid(file_num),
            deserialise_pl72(data.value()).nexus_structure,
            datetime.fromtimestamp(job["start"]),
            stop_time=datetime.fromtimestamp(job["stop"]),
            replay_of=job["number"],
        )
        self.log.info("Replay of job #%s started", job["number"])

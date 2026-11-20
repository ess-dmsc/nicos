import itertools
import time

import pytest
from streaming_data_types import deserialise_6s4t, deserialise_pl72, serialise_x5f2

from nicos.core import MAIN, MASTER, SLAVE, ConfigurationError, status
from nicos_ess.devices.datasinks import file_writer
from nicos_ess.devices.datasinks.file_writer import (
    FAILED,
    LOST,
    REJECTED,
    STARTED,
    WRITTEN,
    AlreadyWritingException,
    FileWriterStartError,
)
from nicos_ess.devices.datasinks.nexus_structure import NexusStructureJsonFile
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import StubKafkaSubscriber
from test.nicos_ess.test_devices.doubles.serialised_messages import (
    create_start_request_message,
    create_status_message,
    create_stop_confirmed_message,
    create_stop_message_with_error,
    create_stop_request_message,
)

CONFIG = {
    "brokers": ["localhost:9092"],
    "statustopic": ["commands", "fw_status"],
    "pool_topic": "pool",
    "instrument_topic": "commands",
    "nexus": "NexusStructure",
}


class HarnessNexusStructureProvider(NexusStructureJsonFile):
    def get_structure(self, metainfo, counter):
        return f'{{"counter": {counter}}}'


class Record:
    def __init__(self, offset, value=None):
        self._offset = offset
        self._value = value

    def partition(self):
        return 0

    def offset(self):
        return self._offset

    def value(self):
        return self._value


class FakePoolReader:
    def __init__(self, writer):
        self.writer = writer
        self.position = None

    def subscribe(self, topics):
        pass

    def seek(self, topic, partition, offset):
        self.position = offset

    def poll(self, timeout_ms):
        return Record(self.position, self.writer.pool[self.position])

    def close(self):
        pass


class FakeWriter:
    """Kafka producer with a file writer behind it."""

    def __init__(self):
        self.device = None
        self.answer = "accept"  # "reject", or None for no writer
        self.error = None
        self.stopped = []
        self.pool = []

    def produce(self, topic, message, on_delivery_callback=None, **options):
        report = on_delivery_callback or (lambda err, msg: None)
        if self.error:
            report(self.error, None)
            return
        if topic == "pool":
            self.pool.append(message)
        report(None, Record(len(self.pool) - 1))
        if topic == "pool" and self.answer:
            job_id = deserialise_pl72(message).job_id
            ok = self.answer == "accept"
            self.send(create_start_request_message(job_id, success=ok))
        elif topic == "commands":
            job_id = deserialise_6s4t(message).job_id
            self.stopped.append(job_id)
            if self.answer:
                self.send(create_stop_request_message(job_id))

    def send(self, *messages, to=None):
        (to or self.device).new_messages_callback(list(enumerate(messages)))


@pytest.fixture
def writer(device_harness, monkeypatch):
    fake = FakeWriter()
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(file_writer.KafkaProducer, "create", lambda *a, **kw: fake)
    monkeypatch.setattr(
        file_writer.KafkaConsumer, "create", lambda *args: FakePoolReader(fake)
    )
    monkeypatch.setattr(
        file_writer, "incrementFileCounter", itertools.count(42).__next__
    )
    monkeypatch.setattr(file_writer, "STOP_ANSWER_TIMEOUT", 0.2)
    with device_harness.activate("daemon") as daemon_session:
        daemon_session.experiment.propinfo["proposal"] = "123456"
    device_harness.create_pair(
        HarnessNexusStructureProvider,
        name="NexusStructure",
        shared={"instrument_name": "ymir"},
    )
    return fake


@pytest.fixture
def fw(writer, device_harness):
    writer.device = device_harness.create_daemon(
        file_writer.FileWriter, name="FileWriter", **CONFIG
    )
    return writer.device


@pytest.fixture
def other(device_harness):
    """Another daemon on the same cache: a restarted or a slave one."""

    def create(mode):
        return device_harness.create(
            "poller",
            file_writer.FileWriter,
            name="FileWriter",
            mode=mode,
            sessiontype=MAIN,
            **CONFIG,
        )

    return create


@pytest.fixture
def daemon(device_harness):
    return lambda: device_harness.activate("daemon")


@pytest.fixture
def start(fw, daemon):
    def start():
        with daemon():
            fw.start_job()
        return fw.jobs[-1]["id"]

    return start


@pytest.fixture
def stop(fw, daemon):
    def stop(number=None):
        with daemon():
            fw.stop_job(number)

    return stop


def job(fw, job_id=None):
    return next(j for j in reversed(fw.jobs) if job_id in (None, j["id"]))


def lose_contact(fw):
    later = time.time() + 3600
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(file_writer.time, "time", lambda: later)
        fw.no_messages_callback()


@pytest.fixture
def two_running_jobs(start, fw, writer):
    first = start()
    lose_contact(fw)
    second = start()
    writer.send(create_status_message(first))
    return first, second


def test_start_waits_for_a_writer_to_take_the_job(start, fw):
    job_id = start()

    assert job(fw)["state"] == STARTED
    assert job_id.startswith("12345600")
    assert fw.status(0) == (status.BUSY, "recording data")


def test_cannot_start_while_writing(start, fw, daemon):
    start()
    with daemon(), pytest.raises(AlreadyWritingException):
        fw.start_job()


def test_cannot_start_without_proposal(fw, device_harness):
    with device_harness.activate("daemon") as daemon_session:
        daemon_session.experiment.propinfo["proposal"] = None
        with pytest.raises(RuntimeError, match="proposal"):
            fw.start_job()


def test_rejected_start_raises(start, writer, fw):
    writer.answer = "reject"
    with pytest.raises(FileWriterStartError, match="REJECTED"):
        start()

    assert job(fw)["state"] == REJECTED
    assert not fw.get_active_jobs()


def test_start_no_writer_takes_raises_and_is_stopped(start, writer, fw):
    writer.answer = None
    fw.starttimeout = 0
    with pytest.raises(FileWriterStartError, match="no file writer took job"):
        start()

    job_id = job(fw)["id"]
    assert writer.stopped == [job_id]
    writer.send(create_start_request_message(job_id))
    assert job(fw)["state"] == STARTED
    assert not fw.get_active_jobs()


def test_immediate_stop_during_the_start_stops_the_job(
    writer, fw, device_harness, monkeypatch
):
    writer.answer = None

    def immediate_stop(secs):
        raise RuntimeError("emergency stop")

    with device_harness.activate("daemon") as daemon_session:
        monkeypatch.setattr(daemon_session, "delay", immediate_stop)
        with pytest.raises(RuntimeError, match="emergency stop"):
            fw.start_job()

    assert len(writer.stopped) == 1
    assert not fw.get_active_jobs()


def test_stop_during_the_start_is_not_hidden_by_a_kafka_error(
    writer, fw, device_harness, monkeypatch
):
    writer.answer = None

    def immediate_stop(secs):
        writer.error = "broker down"
        raise RuntimeError("emergency stop")

    with device_harness.activate("daemon") as daemon_session:
        monkeypatch.setattr(daemon_session, "delay", immediate_stop)
        with pytest.raises(RuntimeError, match="emergency stop"):
            fw.start_job()


def test_kafka_refusing_the_start_raises(writer, fw, start):
    writer.error = "broker down"
    with pytest.raises(RuntimeError, match="pool"):
        start()

    assert not fw.get_active_jobs()
    writer.error = None
    start()
    assert len(fw.get_active_jobs()) == 1


def test_a_start_kafka_timed_out_is_stopped_when_a_writer_takes_it(writer, fw, start):
    writer.error = "timed out"
    with pytest.raises(RuntimeError, match="pool"):
        start()
    writer.error = None
    job_id = job(fw)["id"]
    writer.send(create_start_request_message(job_id))

    assert writer.stopped == [job_id]
    assert not fw.get_active_jobs()


def test_stop_without_jobs_does_nothing(fw, writer, stop, caplog):
    stop()

    assert not writer.stopped
    assert "Filewriting stopped" not in caplog.text


@pytest.mark.parametrize("number", [None, 42, "42"])
def test_stop_running_job(start, stop, fw, writer, number, caplog):
    job_id = start()
    stop(number)

    assert writer.stopped == [job_id]
    assert not fw.get_active_jobs()
    assert "Filewriting stopped" in caplog.text


def test_unconfirmed_stop_is_reported(start, stop, writer, caplog):
    start()
    writer.answer = None
    stop()

    assert "no file writer confirmed" in caplog.text
    assert "Filewriting stopped" not in caplog.text


def test_a_stop_kafka_could_not_send_is_sent_when_the_writer_is_back(
    start, stop, fw, writer
):
    job_id = start()
    writer.error = "broker down"
    with pytest.raises(RuntimeError):
        stop()
    assert fw.get_active_jobs() == [job_id]

    writer.error = None
    writer.answer = None
    writer.send(create_status_message(job_id))
    writer.send(create_status_message(job_id))

    assert writer.stopped == [job_id]
    assert not fw.get_active_jobs()


def test_a_stop_by_hand_is_not_sent_twice(start, stop, writer):
    job_id = start()
    writer.error = "broker down"
    with pytest.raises(RuntimeError):
        stop()
    writer.error = None
    writer.answer = None
    stop(42)
    writer.send(create_status_message(job_id))

    assert writer.stopped == [job_id]


def test_a_slave_does_not_send_stops(start, stop, writer, other):
    job_id = start()
    writer.error = "broker down"
    with pytest.raises(RuntimeError):
        stop()
    writer.error = None
    writer.send(create_status_message(job_id), to=other(SLAVE))

    assert not writer.stopped


def test_stop_unknown_job_number(start, stop, writer, caplog):
    start()
    stop(7)

    assert not writer.stopped
    assert "job 7 is not being written" in caplog.text


def test_stop_with_several_jobs_needs_a_number(
    two_running_jobs, stop, fw, writer, caplog
):
    first, second = two_running_jobs
    stop()

    assert not writer.stopped
    assert "[42, 43]" in caplog.text
    stop(42)
    assert writer.stopped == [first]
    assert fw.get_active_jobs() == [second]


def test_lost_job_does_not_block_and_can_still_be_stopped(start, stop, fw, writer):
    job_id = start()
    lose_contact(fw)

    assert job(fw)["state"] == LOST
    assert not fw.get_active_jobs()
    stop()
    assert writer.stopped == [job_id]


def test_lost_stop_can_be_repeated_with_the_job_number(start, stop, writer):
    job_id = start()
    stop()
    writer.send(create_status_message(job_id))
    stop(42)

    assert writer.stopped == [job_id, job_id]


def test_job_without_heartbeat_is_lost_and_comes_back(start, fw, writer, caplog):
    job_id = start()
    lose_contact(fw)

    assert job(fw)["error"] == "no status from the file writer"
    assert fw.status(0) == (status.OK, "")
    writer.send(create_status_message(job_id))
    assert job(fw)["state"] == STARTED
    assert "reports on job #42 again" in caplog.text


@pytest.mark.parametrize(
    "done, state",
    [
        (create_stop_confirmed_message, WRITTEN),
        (create_stop_message_with_error, FAILED),
    ],
)
def test_done_message_ends_the_job(start, fw, writer, done, state):
    job_id = start()
    writer.send(done(job_id), create_status_message(job_id))

    assert job(fw)["state"] == state
    assert fw.status(0) == (status.OK, "")


@pytest.mark.parametrize("status_json", ["", '"idle"', "not json", "[1]"])
def test_messages_of_other_services_are_ignored(start, fw, writer, status_json):
    job_id = start()
    strange = serialise_x5f2("other", "1", "id", "host", 1, 1000, status_json)
    writer.send(strange, create_stop_confirmed_message(job_id))

    assert job(fw)["state"] == WRITTEN


def test_status_is_valid_before_a_master_wrote_one(writer, other):
    assert other(SLAVE).status(0) == (status.OK, "")


def test_a_slave_follows_the_jobs(start, fw, writer, other):
    job_id = start()
    slave = other(SLAVE)
    writer.send(create_status_message(job_id), to=slave)
    assert slave.get_active_jobs() == [job_id]

    writer.send(create_stop_confirmed_message(job_id), to=slave)
    assert not slave.get_active_jobs()
    assert job(fw)["state"] == STARTED


def test_statustopic_must_contain_the_instrument_topic(writer, device_harness):
    with pytest.raises(ConfigurationError, match="instrument_topic"):
        device_harness.create_daemon(
            file_writer.FileWriter,
            name="Misconfigured",
            **dict(CONFIG, statustopic=["fw_status"]),
        )


def test_cache_keeps_the_recent_jobs(start, stop, fw):
    for _ in range(12):
        start()
        stop()

    assert [j["number"] for j in fw.jobs] == list(range(44, 54))


def test_restart_does_not_block_until_a_writer_reports(start, fw, writer, other):
    job_id = start()
    fw.jobs = fw.jobs + [{"job_id": "x", "job_number": 3}]  # old format
    restarted = other(MASTER)

    assert not restarted.get_active_jobs()
    writer.send(create_status_message(job_id), to=restarted)
    assert restarted.get_active_jobs() == [job_id]


class FakeController:
    def __init__(self, reqid="script 1"):
        self.estop_functions = []
        self.events = []
        self.reqid_work = reqid

    def add_estop_function(self, func, args):
        self.estop_functions.append((func, args))

    def eventfunc(self, event, data):
        self.events.append(event)


def hook(fw, device_harness, controller):
    with device_harness.activate("daemon") as daemon_session:
        daemon_session.daemon_device._controller = controller
        fw.doInit(MASTER)
    return controller


@pytest.fixture
def controller(fw, device_harness):
    controller = hook(fw, device_harness, FakeController())
    hook(fw, device_harness, controller)
    return controller


def test_hooks_into_the_daemon_once(controller):
    controller.eventfunc("done", {"reqid": "x", "success": True})

    assert len(controller.estop_functions) == 1
    assert controller.events == ["done"]


def test_immediate_stop_stops_every_job(controller, two_running_jobs, writer, daemon):
    func, args = controller.estop_functions[0]
    with daemon():
        func(*args)

    assert writer.stopped == list(two_running_jobs)


@pytest.mark.parametrize("lost", [False, True])
@pytest.mark.parametrize(
    "script, success, stopped",
    [("script 1", False, True), ("script 1", True, False), ("other", False, False)],
)
def test_script_that_does_not_finish_closes_its_file(
    controller, start, fw, writer, daemon, script, success, stopped, lost
):
    job_id = start()
    if lost:
        lose_contact(fw)
    with daemon():
        controller.eventfunc("done", {"reqid": script, "success": success})

    assert writer.stopped == ([job_id] if stopped else [])


def test_finished_script_hands_its_file_to_the_user(controller, start, writer, daemon):
    start()
    with daemon():
        controller.eventfunc("done", {"reqid": "script 1", "success": True})
        controller.eventfunc("done", {"reqid": "script 1", "success": False})

    assert not writer.stopped


def test_end_of_script_never_raises_into_the_daemon(
    controller, start, writer, daemon, caplog
):
    start()
    writer.error = "broker down"
    with daemon():
        controller.eventfunc("done", {"reqid": "script 1", "success": False})

    assert "stop it with stop_filewriting(42)" in caplog.text


@pytest.mark.parametrize("lost", [False, True])
def test_daemon_restart_stops_jobs_of_scripts_that_died(
    fw, writer, start, device_harness, lost
):
    hook(fw, device_harness, FakeController("script 1"))
    job_id = start()
    if lost:
        lose_contact(fw)
    hook(fw, device_harness, FakeController("setup"))

    assert writer.stopped == [job_id]


def test_daemon_restart_keeps_files_the_user_opened(
    fw, writer, start, device_harness, daemon
):
    controller = hook(fw, device_harness, FakeController())
    start()
    with daemon():
        controller.eventfunc("done", {"reqid": "script 1", "success": True})
    hook(fw, device_harness, FakeController("setup"))

    assert not writer.stopped


def test_list_jobs_shows_the_most_recent_jobs(start, stop, fw, daemon, caplog):
    for _ in range(3):
        start()
        stop()
    caplog.clear()
    with daemon():
        fw.list_jobs(2)

    numbers = [line.split()[0] for line in caplog.messages]
    assert [n for n in numbers if n.isdigit()] == ["43", "44"]


def test_replay_resends_the_original_job_with_its_time_window(
    start, stop, fw, writer, daemon
):
    start()
    stop()
    original = job(fw)
    writer.send(create_stop_confirmed_message(original["id"]))
    with daemon():
        fw.replay_job(42)

    replay = job(fw)
    assert replay["replay_of"] == 42
    assert (replay["start"], replay["stop"]) == (original["start"], original["stop"])
    sent = deserialise_pl72(writer.pool[-1])
    assert sent.nexus_structure == '{"counter": 42}'
    assert sent.stop_time == pytest.approx(original["stop"] * 1000, abs=1)
    assert not fw.get_active_jobs()


def test_replay_needs_a_finished_job(start, fw, daemon):
    start()
    lose_contact(fw)
    with daemon(), pytest.raises(RuntimeError, match="not finished"):
        fw.replay_job(42)

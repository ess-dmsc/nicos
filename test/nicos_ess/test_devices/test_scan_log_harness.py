import time
from types import SimpleNamespace

import pytest
from streaming_data_types.logdata_f144 import deserialise_f144

from nicos import session
from nicos.core import MASTER, SIMULATION
from nicos.core.data.dataset import PointDataset
from nicos.core.data.manager import DataManager
from nicos.utils import readFileCounter
from nicos_ess.devices.datasinks import scan_log
from nicos_ess.devices.datasinks.scan_log import ScanLogSink
from test.nicos_ess.test_devices.doubles import StubKafkaProducer

TOPIC = "instr_nicos_devices"
SHARED = {"brokers": ["localhost:9092"], "topic": TOPIC, "update_interval": 0}


@pytest.fixture
def kafka_stubs(monkeypatch):
    monkeypatch.setattr(
        scan_log.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )


@pytest.fixture
def sink(daemon_device_harness, kafka_stubs, tmp_path):
    del kafka_stubs
    session.experiment.data = DataManager()
    session.experiment.dataroot = str(tmp_path)
    session.experiment.proposalpath = str(tmp_path)
    session.experiment.samplepath = str(tmp_path)
    session.experiment.counterfile = "counters"
    session.experiment._setROParam = lambda name, value: None
    with daemon_device_harness.in_mode(MASTER):
        device = daemon_device_harness.create_master(
            ScanLogSink, name="ScanLog", **SHARED
        )
        session.datasinks = [device]
        # The numbers it publishes when created.
        device._producer.messages.clear()
        yield device


def published(sink):
    messages = [deserialise_f144(m["message"]) for m in sink._producer.messages]
    return [(m.source_name, int(m.value), m.timestamp_unix_ns) for m in messages]


def values(sink, source):
    return [value for name, value, _ in published(sink) if name == source]


def file_rows(sink, source):
    """The values kafka-to-nexus writes: it drops a time equal to the last."""
    rows = []
    last = None
    for name, value, timestamp in published(sink):
        if name == source and timestamp != last:
            rows.append(value)
            last = timestamp
    return rows


def run_scan(npoints, *, before_end=lambda point: None):
    dataman = session.experiment.data
    dataman.beginScan()
    for _ in range(npoints):
        point = dataman.beginPoint()
        before_end(point)
        dataman.finishPoint()
    dataman.finishScan()


def start_counting(point):
    """What acquire() does before it starts the detectors."""
    session.experiment.data.putMetainfo({})
    point.started = time.time()


def counter(tmp_path, countertype):
    return readFileCounter(str(tmp_path / "counters"), countertype)


class TestScanLogSink:
    def test_scan_and_points_are_global_counters_with_zero_between(
        self, sink, tmp_path
    ):
        run_scan(2)
        run_scan(1)

        assert values(sink, "scanlog/scan") == [1, 0, 2, 0]
        assert values(sink, "scanlog/point") == [1, 0, 2, 0, 3, 0]
        assert counter(tmp_path, "scan") == 2
        assert counter(tmp_path, "point") == 3

    def test_publishes_zero_for_both_when_created(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        device = daemon_device_harness.create_master(
            ScanLogSink, name="ScanLog", **SHARED
        )

        assert [(name, value) for name, value, _ in published(device)] == [
            ("scanlog/scan", 0),
            ("scanlog/point", 0),
        ]

    def test_publishes_to_the_topic(self, sink):
        run_scan(1)

        assert {m["topic"] for m in sink._producer.messages} == {TOPIC}

    def test_counting_continues_from_counters_file(self, sink, tmp_path):
        (tmp_path / "counters").write_text("scan 41\npoint 99\n")

        run_scan(1)

        assert values(sink, "scanlog/scan") == [42, 0]
        assert values(sink, "scanlog/point") == [100, 0]

    def test_timestamps_are_ordered_and_points_lie_within_the_scan(self, sink):
        run_scan(3)

        scan_start, scan_end = [
            ts for name, _, ts in published(sink) if name == "scanlog/scan"
        ]
        point_times = [ts for name, _, ts in published(sink) if name == "scanlog/point"]
        assert point_times == sorted(point_times)
        assert scan_start <= point_times[0]
        assert point_times[-1] <= scan_end

    def test_a_point_that_never_counts_is_logged_over_its_window(self, sink):
        later = int(time.time()) + 100

        def window(point):
            point.started = later + 0.5
            point.finished = later + 2.25

        run_scan(1, before_end=window)

        point_messages = [m for m in published(sink) if m[0] == "scanlog/point"]
        # A float time in s holds the ns of today to about 0.25 us.
        assert [(name, value) for name, value, _ in point_messages] == [
            ("scanlog/point", 1),
            ("scanlog/point", 0),
        ]
        assert [ts for _, _, ts in point_messages] == [
            pytest.approx((later + 0.5) * 1e9, abs=1000),
            pytest.approx((later + 2.25) * 1e9, abs=1000),
        ]

    def test_a_point_is_logged_when_its_detectors_start(self, sink):
        def count(point):
            before = time.time_ns()
            start_counting(point)
            # Published while counting, not when the point ends.
            assert values(sink, "scanlog/point") == [1]
            (start,) = [ts for name, _, ts in published(sink) if name.endswith("point")]
            assert before <= start <= int(point.started * 1e9)

        run_scan(1, before_end=count)

        assert values(sink, "scanlog/point") == [1, 0]

    def test_metainfo_twice_logs_the_start_once(self, sink):
        def count(point):
            start_counting(point)
            start_counting(point)

        run_scan(1, before_end=count)

        assert values(sink, "scanlog/point") == [1, 0]

    def test_repeats_add_no_rows_to_the_file(self, sink):
        def count(point):
            sink._publish_current()
            start_counting(point)
            sink._publish_current()
            sink._publish_current()

        sink._publish_current()
        run_scan(4, before_end=count)
        sink._publish_current()

        assert file_rows(sink, "scanlog/scan") == [0, 1, 0]
        assert file_rows(sink, "scanlog/point") == [0, 1, 0, 2, 0, 3, 0, 4, 0]

    def test_time_never_goes_back_on_a_source(self, sink):
        def late_end(point):
            start_counting(point)
            sink._publish_current()
            # The point ended before the repeat above was sent.
            point.finished = point.started

        run_scan(1, before_end=late_end)

        for source in ("scanlog/scan", "scanlog/point"):
            times = [ts for name, _, ts in published(sink) if name == source]
            assert times == sorted(times)

    def test_repeater_runs_and_stops_on_shutdown(
        self, daemon_device_harness, kafka_stubs
    ):
        del kafka_stubs
        device = daemon_device_harness.create_master(
            ScanLogSink, name="ScanLog", **{**SHARED, "update_interval": 0.01}
        )
        deadline = time.monotonic() + 5
        while len(published(device)) < 6 and time.monotonic() < deadline:
            time.sleep(0.01)

        device.doShutdown()

        assert len(published(device)) >= 6
        assert not device._thread.is_alive()
        assert device._producer.flushes == 1
        assert len(set(published(device))) == 2
        assert {value for _, value, _ in published(device)} == {0}

    def test_messages_are_keyed_by_source(self, sink):
        run_scan(1, before_end=start_counting)

        for message in sink._producer.messages:
            source = deserialise_f144(message["message"]).source_name
            assert message["key"] == source.encode()

    def test_count_outside_scan_logs_only_a_point(self, sink):
        session.experiment.data.beginPoint()
        session.experiment.data.finishPoint()

        assert values(sink, "scanlog/scan") == []
        assert values(sink, "scanlog/point") == [1, 0]

    def test_one_message_per_point_regardless_of_detectors(self, sink):
        dataset = PointDataset(
            detectors=[SimpleNamespace(name="det1"), SimpleNamespace(name="det2")]
        )

        assert len(sink.createHandlers(dataset)) == 1

    def test_nothing_is_published_in_simulation(
        self, sink, daemon_device_harness, tmp_path
    ):
        with daemon_device_harness.in_mode(SIMULATION):
            run_scan(2)

            assert published(sink) == []
            assert not (tmp_path / "counters").exists()

    def test_publish_failure_does_not_break_the_scan(self, sink, monkeypatch):
        def fail(*args, **kwargs):
            raise BufferError("queue full")

        monkeypatch.setattr(sink._producer, "produce", fail)

        run_scan(2)

    def test_warns_once_until_a_message_gets_through(self, sink, monkeypatch, caplog):
        real_produce = sink._producer.produce

        def fail(*args, **kwargs):
            raise BufferError("queue full")

        def warnings():
            return [
                r
                for r in caplog.records
                if r.levelname == "WARNING" and r.name.endswith("ScanLog")
            ]

        monkeypatch.setattr(sink._producer, "produce", fail)
        run_scan(2)
        sink._publish_current()
        assert len(warnings()) == 1

        monkeypatch.setattr(sink._producer, "produce", real_produce)
        sink._publish_current()
        assert any("again" in r.getMessage() for r in caplog.records)

        monkeypatch.setattr(sink._producer, "produce", fail)
        sink._publish_current()
        assert len(warnings()) == 2

    def test_failed_delivery_warns_once(self, sink, monkeypatch, caplog):
        def undelivered(*args, on_delivery_callback, **kwargs):
            on_delivery_callback("broker down", None)

        monkeypatch.setattr(sink._producer, "produce", undelivered)
        run_scan(2)

        warnings = [
            r.getMessage()
            for r in caplog.records
            if r.levelname == "WARNING" and r.name.endswith("ScanLog")
        ]
        assert warnings == [f"could not publish to {TOPIC}: broker down"]

    def test_nexus_logs_hold_both_numbers_as_int64(self, sink):
        logs = {log["name"]: log for log in sink.nexus_logs()}

        assert set(logs) == {"scan", "point"}
        for settype, log in logs.items():
            assert log["attributes"][0]["values"] == "NXlog"
            (module,) = log["children"]
            assert module["module"] == "f144"
            assert module["config"]["source"] == f"scanlog/{settype}"
            assert module["config"]["topic"] == TOPIC
            assert module["config"]["dtype"] == "int64"


class TestScanLogSinkRoles:
    def test_only_the_daemon_publishes(self, device_harness, kafka_stubs):
        # Pollers load the system setup, with its sinks, too.
        del kafka_stubs
        daemon_device, poller_device = device_harness.create_pair(
            ScanLogSink, name="ScanLog", shared=SHARED
        )

        assert len(daemon_device._producer.messages) == 2
        assert poller_device._producer is None
        assert poller_device._thread is None

    def test_never_publishes_in_simulation(self, daemon_device_harness, kafka_stubs):
        del kafka_stubs
        device = daemon_device_harness.create_sim(ScanLogSink, name="ScanLog", **SHARED)

        assert device._producer is None
        assert device._thread is None

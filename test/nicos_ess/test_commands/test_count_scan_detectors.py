import json
import threading
import time
from dataclasses import asdict

import numpy as np
import pytest
from streaming_data_types import serialise_da00, serialise_hs01
from streaming_data_types.dataarray_da00 import Variable

from nicos.commands.measure import count
from nicos.commands.scan import scan
from nicos.devices.epics.pva import caproto, p4p

from nicos_ess.devices.datasources import just_bin_it, livedata
from nicos_ess.devices.datasources.livedata_utils import JobId, WorkflowId
from nicos_ess.devices.epics import area_detector as epics_area_detector
from nicos_ess.devices.epics.pva import epics_devices as ess_epics_devices
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.test_devices.doubles import (
    FakeEpicsBackend,
    patch_kafka_stubs,
)
from test.nicos_ess.test_devices.test_area_detector_harness import (
    PV_ROOT,
    seed_area_detector_defaults,
)


session_setup = None

WORKFLOW_ID = WorkflowId(
    instrument="dummy",
    namespace="detector_data",
    name="panel_0_xy",
    version=1,
)
JOB_ID = JobId(source_name="panel_0", job_number="job-1")
OUTPUT_NAME = "current"
SELECTOR = f"{WORKFLOW_ID}@{JOB_ID.source_name}#{JOB_ID.job_number}/{OUTPUT_NAME}"


def start_daemon(target):
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread


def make_jbi_histogram(image, total):
    return serialise_hs01(
        {
            "source": image.name,
            "timestamp": int(time.time() * 1000),
            "current_shape": [image.num_bins],
            "dim_metadata": [
                {
                    "length": image.num_bins,
                    "bin_boundaries": np.arange(image.num_bins + 1, dtype=np.int64),
                    "unit": "us",
                    "label": "tof",
                }
            ],
            "data": np.full(
                (image.num_bins,), total / image.num_bins, dtype=np.float64
            ),
            "info": json.dumps(
                {
                    "id": image._unique_id,
                    "state": "COUNTING",
                    "rate": 0.0,
                }
            ),
        }
    )


def make_da00_message(total):
    source_name = json.dumps(
        {
            "workflow_id": asdict(WORKFLOW_ID),
            "job_id": asdict(JOB_ID),
            "output_name": OUTPUT_NAME,
        }
    )
    signal = np.array([1, 2, total - 3], dtype=np.int32)
    return serialise_da00(
        source_name=source_name,
        timestamp_ns=123456789,
        data=[
            Variable(
                name="signal",
                data=signal,
                shape=signal.shape,
                axes=["tof"],
                unit="counts",
                label="Detector signal",
            ),
            Variable(
                name="tof",
                data=np.array([0.0, 1.0, 2.0], dtype=np.float64),
                shape=(3,),
                axes=["tof"],
                unit="ms",
                label="TOF",
            ),
        ],
    )


class TestAreaDetectorCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        backend = FakeEpicsBackend()
        seed_area_detector_defaults(backend)
        self.acquire_targets = []
        monkeypatch.setattr(
            p4p,
            "P4pWrapper",
            lambda timeout=3.0, context=None: backend,
        )
        monkeypatch.setattr(
            caproto,
            "CaprotoWrapper",
            lambda timeout=3.0: backend,
        )

        original_do_acquire = epics_area_detector.AreaDetector.doAcquire

        def simulate_acquire(device):
            original_do_acquire(device)
            target = (device._lastpreset or {}).get("n", 0)
            self.acquire_targets.append(target)
            backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"
            backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 0

            def complete():
                time.sleep(0.02)
                backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = target
                backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"

            start_daemon(complete)

        monkeypatch.setattr(
            epics_area_detector.AreaDetector, "doAcquire", simulate_acquire
        )

        session.unloadSetup()
        session.loadSetup("ess_count_scan_area_detector", {})
        session.updateLiveData = lambda *args, **kwargs: None
        session.experiment.setDetectors(
            [session.getDevice("timedet"), session.getDevice("area_detector")]
        )
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_area_detector_preset_alongside_timer(self, session):
        result = count(t=0.05, camera=2)

        assert len(result) == 1
        assert session.getDevice("camera").read()[0] == 2

    def test_scan_accepts_area_detector_preset_alongside_timer(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=0.05, camera=1)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == ["timer"]
        assert session.getDevice("camera").read()[0] == 1

    def test_count_reuses_area_detector_preset_when_only_timer_key_changes(
        self, session
    ):
        result_1 = count(t=0.05, camera=2)
        result_2 = count(t=0.02)
        result_3 = count(t=0.03, camera=1)
        result_4 = count()

        assert len(result_1) == 1
        assert len(result_2) == 1
        assert len(result_3) == 1
        assert len(result_4) == 1
        assert self.acquire_targets == [2, 2, 1, 1]
        assert session.getDevice("camera").read()[0] == 1


class TestJustBinItCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        backend = FakeEpicsBackend()
        backend.values["SIM:PULSE"] = 0
        self.controller_names = []
        producer = patch_kafka_stubs(
            monkeypatch,
            just_bin_it,
            status_module=status_handler,
        )
        monkeypatch.setattr(
            ess_epics_devices,
            "create_wrapper",
            lambda timeout, use_pva: backend,
        )

        original_do_start = just_bin_it.JustBinItDetector.doStart

        def simulate_start(device, **preset):
            original_do_start(device, **preset)
            config = json.loads(producer.messages[-1]["message"])
            device._response_consumer.push_message(
                json.dumps(
                    {"msg_id": config["msg_id"], "response": "ACK"}
                ).encode()
            )
            self.controller_names.append(
                tuple(ch.name for ch in device._controlchannels)
            )
            image = device._attached_images[0]
            counter = device._attached_counters[0]
            image_target = None
            counter_target = None
            if image in device._channel_presets:
                image_target = device._channel_presets[image][0][1]
            if counter in device._channel_presets:
                counter_target = device._channel_presets[counter][0][1]

            def publish_counter():
                time.sleep(0.02)
                counter.total = counter.offset + counter_target

            def publish_histogram():
                time.sleep(0.02)
                message = make_jbi_histogram(image, total=image_target)
                image.new_messages_callback([(123456789, message)])

            if counter_target is not None:
                start_daemon(publish_counter)
            if image_target is not None:
                start_daemon(publish_histogram)

        monkeypatch.setattr(just_bin_it.JustBinItDetector, "doStart", simulate_start)

        session.unloadSetup()
        session.loadSetup("ess_count_scan_just_bin_it", {})
        session.experiment.setDetectors([session.getDevice("jbi_detector")])
        self.producer = producer
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_runs_against_just_bin_it_with_counter_preset(self, session):
        result = count(n=7)

        config = json.loads(self.producer.messages[0]["message"])
        assert len(result) == 3
        assert result[1] == 7
        assert result[2] == 0
        assert session.getDevice("pulse_counter").read()[0] == 7
        assert config["input_schema"] == "ev44"
        assert config["output_schema"] == "hs01"

    def test_scan_runs_against_just_bin_it_with_hs01_payloads(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], jbi_image=5)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "timer",
            "pulse_counter",
            "jbi_image",
        ]
        assert session.getDevice("jbi_image").read()[0] == 5

    def test_count_switches_between_counter_timer_and_image_presets(self, session):
        result_1 = count(n=7)
        result_2 = count(t=0.05)
        result_3 = count(jbi_image=3)
        result_4 = count()

        assert result_1[1:] == [7, 0]
        assert result_2[1:] == [0, 0]
        assert result_3[1:] == [0, 3]
        assert result_4[1:] == [0, 3]
        assert self.controller_names == [
            ("pulse_counter",),
            ("timer",),
            ("jbi_image",),
            ("jbi_image",),
        ]


class TestLiveDataCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        self.published_totals = []
        self.controller_names = []
        patch_kafka_stubs(monkeypatch, livedata)
        monkeypatch.setattr(livedata, "sleep", lambda *_args, **_kwargs: None)

        original_do_start = livedata.LiveDataCollector.doStart

        def simulate_start(device):
            original_do_start(device)
            self.controller_names.append(
                tuple(ch.name for ch in device._controlchannels)
            )
            total = None
            for channel_presets in device._channel_presets.values():
                if channel_presets:
                    total = channel_presets[0][1]
                    break
            if total is None:
                total = (device._lastpreset or {}).get("n", 6)
            self.published_totals.append(total)

            def publish_da00():
                time.sleep(0.02)
                device._on_data_messages([(123456789, make_da00_message(total=total))])

            start_daemon(publish_da00)

        monkeypatch.setattr(livedata.LiveDataCollector, "doStart", simulate_start)

        session.unloadSetup()
        session.loadSetup("ess_count_scan_livedata", {})
        session.updateLiveData = lambda *args, **kwargs: None
        for channel_name in ("livedata_primary", "livedata_secondary", "livedata_roi"):
            session.getDevice(channel_name).selector = SELECTOR
        session.experiment.setDetectors([session.getDevice("livedata_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_runs_against_livedata_with_da00_payloads(self, session):
        result = count(n=6)
        detector = session.getDevice("livedata_detector")

        assert len(result) == 3
        assert result == [6, 6, 6]
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_primary",
        )
        assert session.getDevice("livedata_primary").read()[0] == 6
        assert session.getDevice("livedata_secondary").read()[0] == 6
        assert session.getDevice("livedata_roi").read()[0] == 6

    def test_scan_runs_against_livedata_with_da00_payloads(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], n=6)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "livedata_primary",
            "livedata_secondary",
            "livedata_roi",
        ]
        assert session.getDevice("livedata_primary").read()[0] == 6

    def test_count_reuses_latest_livedata_preset_across_multiple_calls(self, session):
        result_1 = count(n=6)
        result_2 = count(livedata_secondary=4)
        result_3 = count()

        assert result_1 == [6, 6, 6]
        assert result_2 == [4, 4, 4]
        assert result_3 == [4, 4, 4]
        assert self.controller_names == [
            ("livedata_primary",),
            ("livedata_secondary",),
            ("livedata_secondary",),
        ]
        assert self.published_totals == [6, 4, 4]

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
    name="panel_0_tof",
    version=1,
)
JOB_ID = JobId(source_name="panel_0", job_number="job-1")


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


def jbi_stop_messages(producer):
    return [
        message
        for message in producer.messages
        if message["message"] == b'{"cmd": "stop"}'
    ]


def make_da00_message(output_name, total):
    source_name = json.dumps(
        {
            "workflow_id": asdict(WORKFLOW_ID),
            "job_id": asdict(JOB_ID),
            "output_name": output_name,
        }
    )
    first = total // 3
    second = total // 3
    third = total - first - second
    signal = np.array([first, second, third], dtype=np.int32)
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
                label=f"Detector signal {output_name}",
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
        session.experiment.setDetectors([session.getDevice("area_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_timer_and_area_detector_preset(self, session):
        result = count(t=0.05, camera=2)
        detector = session.getDevice("area_detector")

        assert len(result) == 2
        assert result[1] == 2
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "area_timer",
            "camera",
        )
        assert detector.preset()["t"] == 0.05
        assert session.getDevice("camera").preset() == {"n": 2}
        assert session.getDevice("camera").read()[0] == 2

    def test_count_accepts_area_detector_image_count_alias(self, session):
        result = count(n=2)
        detector = session.getDevice("area_detector")

        assert len(result) == 2
        assert result[1] == 2
        assert tuple(ch.name for ch in detector._controlchannels) == ("camera",)
        assert session.getDevice("camera").read()[0] == 2

    def test_scan_runs_against_area_detector_with_timer_and_image(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=0.05, camera=1)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "area_timer",
            "camera",
        ]
        assert session.getDevice("camera").read()[0] == 1

    def test_count_keeps_image_channel_state_when_only_timer_key_changes(
        self, session
    ):
        detector = session.getDevice("area_detector")

        def run_count(**preset):
            session.experiment.setDetectors([detector])
            return count(**preset)

        result_1 = run_count(camera=2)
        result_2 = run_count(t=0.02)
        area_detector_after_timer_only = session.getDevice("area_detector").preset()
        camera_after_timer_only = session.getDevice("camera").preset()
        result_3 = run_count(camera=1)
        result_4 = run_count()

        assert result_1[1] == 2
        assert result_3[1] == 1
        assert result_4[1] == 1
        assert area_detector_after_timer_only == {"t": 0.02}
        assert camera_after_timer_only == {"n": 2}
        assert self.acquire_targets == [2, 2, 1, 1]
        assert session.getDevice("camera").read()[0] == 1


class TestVirtualAreaDetectorCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        session.unloadSetup()
        session.loadSetup("ess_count_scan_virtual_area_detector", {})
        session.updateLiveData = lambda *args, **kwargs: None
        camera = session.getDevice("camera")
        camera.sizex = 32
        camera.sizey = 32
        camera.acquiretime = 0.01
        camera.acquireperiod = 0.01
        camera.update_arraydesc()
        camera._image_array = np.zeros(camera.arraydesc.shape, dtype=camera.arraydesc.dtype)
        session.experiment.setDetectors([session.getDevice("area_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_timer_and_area_detector_preset(self, session):
        result = count(t=0.5, camera=2)
        detector = session.getDevice("area_detector")

        assert len(result) == 2
        assert result[1] == 2
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "area_timer",
            "camera",
        )
        assert detector.preset()["t"] == 0.5
        assert session.getDevice("camera").preset() == {"n": 2}
        assert session.getDevice("camera").read()[0] == 2

    def test_count_accepts_area_detector_image_count_alias(self, session):
        result = count(n=2)
        detector = session.getDevice("area_detector")

        assert len(result) == 2
        assert result[1] == 2
        assert tuple(ch.name for ch in detector._controlchannels) == ("camera",)
        assert session.getDevice("camera").read()[0] == 2

    def test_scan_runs_against_area_detector_with_timer_and_image(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=0.5, camera=1)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "area_timer",
            "camera",
        ]
        assert session.getDevice("camera").read()[0] == 1

    def test_count_keeps_image_channel_state_when_only_timer_key_changes(
        self, session
    ):
        detector = session.getDevice("area_detector")

        def run_count(**preset):
            session.experiment.setDetectors([detector])
            return count(**preset)

        result_1 = run_count(camera=2)
        result_2 = run_count(t=0.2)
        area_detector_after_timer_only = session.getDevice("area_detector").preset()
        camera_after_timer_only = session.getDevice("camera").preset()
        result_3 = run_count(camera=1)
        result_4 = run_count()

        assert result_1[1] == 2
        assert result_3[1] == 1
        assert result_4[1] == 1
        assert area_detector_after_timer_only == {"t": 0.2}
        assert camera_after_timer_only == {"n": 2}
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

            counter = device._attached_counters[0]
            counter_target = None
            if counter in device._channel_presets:
                counter_target = device._channel_presets[counter][0][1]

            selected_image = None
            image_target = None
            for image in device._attached_images:
                if image in device._channel_presets:
                    selected_image = image
                    image_target = device._channel_presets[image][0][1]
                    break

            def publish_counter():
                time.sleep(0.02)
                counter.total = counter.offset + counter_target

            def publish_histogram():
                time.sleep(0.02)
                message = make_jbi_histogram(selected_image, total=image_target)
                selected_image.new_messages_callback([(123456789, message)])

            if counter_target is not None:
                start_daemon(publish_counter)
            if selected_image is not None:
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

    def test_count_accepts_timer_and_image_preset_on_one_detector(self, session):
        result = count(t=0.05, jbi_image_fast=5)
        config = json.loads(self.producer.messages[0]["message"])

        assert len(result) == 4
        assert result[1:] == [0, 5, 0]
        assert self.controller_names == [("jbi_timer", "jbi_image_fast")]
        assert session.getDevice("jbi_detector").preset()["t"] == 0.05
        assert config["input_schema"] == "ev44"
        assert config["output_schema"] == "hs01"
        assert "start" in config
        assert "interval" not in config

    def test_count_runs_against_just_bin_it_with_counter_preset(self, session):
        result = count(n=7)

        assert len(result) == 4
        assert result[1:] == [7, 0, 0]
        assert self.controller_names == [("pulse_counter",)]
        assert session.getDevice("pulse_counter").read()[0] == 7

    def test_scan_runs_against_just_bin_it_with_hs01_payloads(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=0.05, jbi_image_fast=5)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "jbi_timer",
            "pulse_counter",
            "jbi_image_fast",
            "jbi_image_slow",
        ]
        assert session.getDevice("jbi_image_fast").read()[0] == 5

    def test_count_switches_between_counter_timer_and_image_presets(self, session):
        result_1 = count(n=7)
        result_2 = count(t=0.05)
        result_3 = count(jbi_image_fast=3)
        result_4 = count()

        assert result_1[1:] == [7, 0, 0]
        assert result_2[1:] == [0, 0, 0]
        assert result_3[1:] == [0, 3, 0]
        assert result_4[1:] == [0, 3, 0]
        assert self.controller_names == [
            ("pulse_counter",),
            ("jbi_timer",),
            ("jbi_image_fast",),
            ("jbi_image_fast",),
        ]

    def test_count_completes_when_first_image_preset_reaches_target(self, session):
        result = count(jbi_image_fast=5, jbi_image_slow=9)

        assert result[1:] == [0, 5, 0]
        assert self.controller_names == [("jbi_image_fast", "jbi_image_slow")]
        assert session.getDevice("jbi_image_fast").read()[0] == 5
        assert session.getDevice("jbi_image_slow").read()[0] == 0
        assert len(jbi_stop_messages(self.producer)) == 1

    def test_scan_completes_each_point_when_first_image_preset_reaches_target(
        self, session
    ):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], jbi_image_fast=5, jbi_image_slow=9)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "jbi_timer",
            "pulse_counter",
            "jbi_image_fast",
            "jbi_image_slow",
        ]
        assert self.controller_names == [
            ("jbi_image_fast", "jbi_image_slow"),
            ("jbi_image_fast", "jbi_image_slow"),
        ]
        assert session.getDevice("jbi_image_fast").read()[0] == 5
        assert session.getDevice("jbi_image_slow").read()[0] == 0
        assert len(jbi_stop_messages(self.producer)) == 2


class TestVirtualJustBinItCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        session.unloadSetup()
        session.loadSetup("ess_count_scan_virtual_just_bin_it", {})
        session.updateLiveData = lambda *args, **kwargs: None
        session.experiment.setDetectors([session.getDevice("jbi_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_timer_and_image_preset_on_one_detector(self, session):
        result = count(t=1.0, jbi_image_fast=5)
        detector = session.getDevice("jbi_detector")

        assert len(result) == 4
        assert result[2] >= 5
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "jbi_timer",
            "jbi_image_fast",
        )
        assert detector.preset()["t"] == 1.0

    def test_count_runs_against_virtual_just_bin_it_with_counter_preset(self, session):
        result = count(n=20)
        detector = session.getDevice("jbi_detector")

        assert len(result) == 4
        assert result[1] == 20
        assert tuple(ch.name for ch in detector._controlchannels) == ("pulse_counter",)

    def test_scan_runs_against_virtual_just_bin_it_with_image_presets(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=1.0, jbi_image_fast=5)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "jbi_timer",
            "pulse_counter",
            "jbi_image_fast",
            "jbi_image_slow",
        ]
        assert session.getDevice("jbi_image_fast").read()[0] >= 5

    def test_count_completes_when_first_image_preset_reaches_target(self, session):
        result = count(jbi_image_fast=5, jbi_image_slow=1_000_000)
        detector = session.getDevice("jbi_detector")

        assert len(result) == 4
        assert result[2] >= 5
        assert result[3] < 1_000_000
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "jbi_image_fast",
            "jbi_image_slow",
        )


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

            current_channel = session.getDevice("livedata_current")
            total = None
            if current_channel in device._channel_presets:
                total = int(device._channel_presets[current_channel][0][1])
            elif "n" in (device._lastpreset or {}):
                total = int(device._lastpreset["n"])
            elif "livedata_current" in (device._lastpreset or {}):
                total = int(device._lastpreset["livedata_current"])
            if total is None:
                total = 6
            cumulative_total = total + 3
            self.published_totals.append((total, cumulative_total))

            def publish_da00():
                time.sleep(0.02)
                device._on_data_messages(
                    [
                        (123456789, make_da00_message("current", total=total)),
                        (
                            123456790,
                            make_da00_message(
                                "cumulative", total=cumulative_total
                            ),
                        ),
                    ]
                )

            start_daemon(publish_da00)

        monkeypatch.setattr(livedata.LiveDataCollector, "doStart", simulate_start)

        session.unloadSetup()
        session.loadSetup("ess_count_scan_livedata", {})
        session.updateLiveData = lambda *args, **kwargs: None
        session.experiment.setDetectors([session.getDevice("livedata_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_timer_and_current_output_preset(self, session):
        result = count(t=0.05, livedata_current=6)
        detector = session.getDevice("livedata_detector")

        assert len(result) == 3
        assert result[1:] == [6, 9]
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_timer",
            "livedata_current",
        )
        assert detector.preset()["t"] == 0.05
        assert session.getDevice("livedata_current").read()[0] == 6
        assert session.getDevice("livedata_cumulative").read()[0] == 9

    def test_count_runs_against_livedata_with_count_alias(self, session):
        result = count(n=6)
        detector = session.getDevice("livedata_detector")

        assert len(result) == 3
        assert result[1:] == [6, 9]
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_current",
        )
        assert session.getDevice("livedata_current").read()[0] == 6
        assert session.getDevice("livedata_cumulative").read()[0] == 9

    def test_scan_runs_against_livedata_with_da00_payloads(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=0.05, n=6)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "livedata_timer",
            "livedata_current",
            "livedata_cumulative",
        ]
        assert session.getDevice("livedata_current").read()[0] == 6
        assert session.getDevice("livedata_cumulative").read()[0] == 9

    def test_count_reuses_latest_livedata_preset_across_multiple_calls(self, session):
        result_1 = count(n=6)
        result_2 = count(t=0.05)
        result_3 = count(livedata_current=4)
        result_4 = count()

        assert result_1[1:] == [6, 9]
        assert result_2[1:] == [6, 9]
        assert result_3[1:] == [4, 7]
        assert result_4[1:] == [4, 7]
        assert self.controller_names == [
            ("livedata_current",),
            ("livedata_timer",),
            ("livedata_current",),
            ("livedata_current",),
        ]
        assert self.published_totals == [(6, 9), (6, 9), (4, 7), (4, 7)]


class TestVirtualLiveDataCountScan:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        session.unloadSetup()
        session.loadSetup("ess_count_scan_virtual_livedata", {})
        session.updateLiveData = lambda *args, **kwargs: None
        session.experiment.setDetectors([session.getDevice("livedata_detector")])
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_accepts_timer_and_current_output_preset(self, session):
        result = count(t=1.0, livedata_current=1)
        detector = session.getDevice("livedata_detector")

        assert len(result) == 3
        assert result[1] >= 1
        assert result[2] >= result[1]
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_timer",
            "livedata_current",
        )
        assert detector.preset()["t"] == 1.0

    def test_count_runs_against_virtual_livedata_with_count_alias(self, session):
        result = count(n=1)
        detector = session.getDevice("livedata_detector")

        assert len(result) == 3
        assert result[1] >= 1
        assert result[2] >= result[1]
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_current",
        )

    def test_scan_runs_against_virtual_livedata(self, session):
        motor = session.getDevice("motor")

        scan(motor, [0, 1], t=1.0, n=1)
        dataset = session.experiment.data.getLastScans()[-1]

        assert dataset.devvaluelists == [[0.0], [1.0]]
        assert [value.name for value in dataset.detvalueinfo] == [
            "livedata_timer",
            "livedata_current",
            "livedata_cumulative",
        ]

    def test_count_reuses_latest_livedata_preset_across_multiple_calls(self, session):
        result_1 = count(n=1)
        result_2 = count(t=0.2)
        result_3 = count(n=2)
        result_4 = count()
        detector = session.getDevice("livedata_detector")

        assert result_1[1] >= 1
        assert result_2[1] >= 0
        assert result_3[1] >= 2
        assert result_4[1] >= 2
        assert tuple(ch.name for ch in detector._controlchannels) == (
            "livedata_current",
        )

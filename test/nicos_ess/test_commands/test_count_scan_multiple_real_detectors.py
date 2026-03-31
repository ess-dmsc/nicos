import json
import threading
import time
from dataclasses import asdict

import numpy as np
import pytest
from streaming_data_types import serialise_da00, serialise_hs01
from streaming_data_types.dataarray_da00 import Variable

from nicos.commands.measure import count
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


def jbi_stop_messages(producer):
    return [
        message
        for message in producer.messages
        if message["message"] == b'{"cmd": "stop"}'
    ]


class TestMultipleRealDetectorsCount:
    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        backend = FakeEpicsBackend()
        seed_area_detector_defaults(backend)
        backend.values["SIM:PULSE"] = 0
        self.area_targets = []
        self.area_controller_names = []
        self.jbi_configs = []
        self.jbi_controller_names = []
        self.livedata_totals = []
        self.livedata_controller_names = []

        patch_kafka_stubs(
            monkeypatch,
            just_bin_it,
            status_module=status_handler,
        )
        patch_kafka_stubs(monkeypatch, livedata)
        monkeypatch.setattr(livedata, "sleep", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            ess_epics_devices,
            "create_wrapper",
            lambda timeout, use_pva: backend,
        )
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
            self.area_targets.append(target)
            self.area_controller_names.append(
                tuple(ch.name for ch in session.getDevice("area_detector")._controlchannels)
            )
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

        original_jbi_start = just_bin_it.JustBinItDetector.doStart

        def simulate_jbi_start(device, **preset):
            original_jbi_start(device, **preset)
            config = json.loads(device._command_sender.messages[-1]["message"])
            self.jbi_configs.append(config)
            self.jbi_controller_names.append(
                tuple(ch.name for ch in device._controlchannels)
            )
            device._response_consumer.push_message(
                json.dumps(
                    {"msg_id": config["msg_id"], "response": "ACK"}
                ).encode()
            )

            selected_image = None
            image_target = None
            for image in device._attached_images:
                if image in device._channel_presets:
                    selected_image = image
                    image_target = device._channel_presets[image][0][1]
                    break

            def publish_histogram():
                time.sleep(0.04)
                message = make_jbi_histogram(selected_image, total=image_target)
                selected_image.new_messages_callback([(123456789, message)])

            if selected_image is not None:
                start_daemon(publish_histogram)

        monkeypatch.setattr(
            just_bin_it.JustBinItDetector, "doStart", simulate_jbi_start
        )

        original_livedata_start = livedata.LiveDataCollector.doStart

        def simulate_livedata_start(device):
            original_livedata_start(device)
            self.livedata_controller_names.append(
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
            self.livedata_totals.append((total, cumulative_total))

            def publish_da00():
                time.sleep(0.06)
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

        monkeypatch.setattr(
            livedata.LiveDataCollector, "doStart", simulate_livedata_start
        )

        session.unloadSetup()
        session.loadSetup(
            [
                "ess_count_scan_area_detector",
                "ess_count_scan_just_bin_it",
                "ess_count_scan_livedata",
            ],
            {},
        )
        session.updateLiveData = lambda *args, **kwargs: None
        session.experiment.setDetectors(
            [
                session.getDevice("area_detector"),
                session.getDevice("jbi_detector"),
                session.getDevice("livedata_detector"),
            ]
        )
        self.producer = session.getDevice("jbi_detector")._command_sender
        yield
        session.experiment.detlist = []
        session.experiment.envlist = []
        session.unloadSetup()

    def test_count_uses_and_logic_across_real_detectors(self, session):
        result = count(t=0.2, camera=2, jbi_image_fast=5, livedata_current=6)

        assert len(result) == 9
        assert result[1] == 2
        assert result[3] == 0
        assert result[4] == 5
        assert result[5] == 0
        assert result[7:] == [6, 9]

        assert self.area_targets == [2]
        assert self.area_controller_names == [("area_timer", "camera")]
        assert self.jbi_controller_names == [("jbi_timer", "jbi_image_fast")]
        assert self.livedata_controller_names == [
            ("livedata_timer", "livedata_current")
        ]
        assert self.livedata_totals == [(6, 9)]
        assert session.getDevice("area_detector").preset()["t"] == 0.2
        assert session.getDevice("camera").preset() == {"n": 2}
        assert session.getDevice("jbi_detector").preset()["t"] == 0.2
        assert session.getDevice("livedata_detector").preset()["t"] == 0.2

        config = self.jbi_configs[0]
        assert config["input_schema"] == "ev44"
        assert config["output_schema"] == "hs01"
        assert "start" in config
        assert "interval" not in config
        assert len(jbi_stop_messages(self.producer)) == 1

        assert session.getDevice("camera").read()[0] == 2
        assert session.getDevice("jbi_image_fast").read()[0] == 5
        assert session.getDevice("livedata_current").read()[0] == 6

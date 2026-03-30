import numpy as np
import pytest

from nicos.core import ArrayDesc, NicosError, status
from nicos.core.constants import FINAL, INTERMEDIATE, LIVE
from nicos.devices.epics.pva import caproto, p4p
from nicos_ess.devices.epics.area_detector import (
    AreaDetector,
    AreaDetectorCollector,
    OrcaFlash4,
    TimepixDetector,
)
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend


PV_ROOT = "SIM:AD:"
IMAGE_PV = "SIM:AD:IMAGE"
SECOND_PV_ROOT = "SIM:AD2:"
SECOND_IMAGE_PV = "SIM:AD2:IMAGE"
TIMEPIX_PV_ROOT = "SIM:TPX:"
TIMEPIX_IMAGE_PV = "SIM:TPX:IMAGE"
ORCA_PV_ROOT = "SIM:ORCA:"
ORCA_IMAGE_PV = "SIM:ORCA:IMAGE"
ORCA_TOPIC_PV = "SIM:ORCA:TOPIC"
ORCA_SOURCE_PV = "SIM:ORCA:SOURCE"


def seed_area_detector_defaults(fake_backend, pv_root=PV_ROOT, image_pv=IMAGE_PV):
    fake_backend.values.update(
        {
            f"{pv_root}MaxSizeX_RBV": 1024,
            f"{pv_root}MaxSizeY_RBV": 2048,
            f"{pv_root}DataType_RBV": "UInt32",
            f"{pv_root}NumImagesCounter_RBV": 0,
            f"{pv_root}DetectorState_RBV": 0,
            f"{pv_root}DetectorState_RBV.STAT": 0,
            f"{pv_root}DetectorState_RBV.SEVR": 0,
            f"{pv_root}ArrayRate_RBV": 0,
            f"{pv_root}Acquire": 0,
            f"{pv_root}AcquireBusy": "Done",
            image_pv: np.zeros((2048, 1024), dtype=np.uint32).ravel(),
        }
    )


def seed_timepix_defaults(fake_backend):
    seed_area_detector_defaults(
        fake_backend,
        pv_root=TIMEPIX_PV_ROOT,
        image_pv=TIMEPIX_IMAGE_PV,
    )
    fake_backend.values.update(
        {
            f"{TIMEPIX_PV_ROOT}AcquireTime_RBV": 0.1,
            f"{TIMEPIX_PV_ROOT}AcquirePeriod_RBV": 0.2,
            f"{TIMEPIX_PV_ROOT}CHIP0_Vth_fine_RBV": 0,
            f"{TIMEPIX_PV_ROOT}CHIP0_Vth_coarse_RBV": 0,
            f"{TIMEPIX_PV_ROOT}N_Processing": 0,
            f"{TIMEPIX_PV_ROOT}EvFlit_PhMin": 0,
            f"{TIMEPIX_PV_ROOT}EvFlit_PsdMin": 0,
        }
    )


def seed_orca_defaults(fake_backend):
    seed_area_detector_defaults(
        fake_backend,
        pv_root=ORCA_PV_ROOT,
        image_pv=ORCA_IMAGE_PV,
    )
    fake_backend.values.update(
        {
            ORCA_TOPIC_PV: "orca-topic",
            ORCA_SOURCE_PV: "orca-source",
            f"{ORCA_PV_ROOT}SizeX_RBV": 1024,
            f"{ORCA_PV_ROOT}SizeY_RBV": 2048,
            f"{ORCA_PV_ROOT}MinX_RBV": 0,
            f"{ORCA_PV_ROOT}MinY_RBV": 0,
            f"{ORCA_PV_ROOT}BinX_RBV": 1,
            f"{ORCA_PV_ROOT}BinY_RBV": 1,
            f"{ORCA_PV_ROOT}NumImages_RBV": 1,
            f"{ORCA_PV_ROOT}NumExposures_RBV": 1,
            f"{ORCA_PV_ROOT}ImageMode": 2,
            f"{ORCA_PV_ROOT}SubarrayMode-RB": False,
            f"{ORCA_PV_ROOT}Binning-RB": 0,
            f"{ORCA_PV_ROOT}TriggerTimes-RB": 14,
            f"{ORCA_PV_ROOT}TriggerActive-RB": 2,
            f"{ORCA_PV_ROOT}SensorCooler-RB": 0,
            f"{ORCA_PV_ROOT}Temperature-R": 20.0,
        }
    )


@pytest.fixture
def fake_backend(monkeypatch):
    backend = FakeEpicsBackend()
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout=3.0, context=None: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout=3.0: backend)
    seed_area_detector_defaults(backend)
    return backend


def create_area_detector(daemon_device_harness):
    return daemon_device_harness.create_master(
        AreaDetector,
        name="ad_1",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )


def create_timepix_detector(daemon_device_harness):
    return daemon_device_harness.create_master(
        TimepixDetector,
        name="timepix",
        pv_root=TIMEPIX_PV_ROOT,
        image_pv=TIMEPIX_IMAGE_PV,
    )


def create_orca_flash_detector(daemon_device_harness):
    return daemon_device_harness.create_master(
        OrcaFlash4,
        name="orca_camera",
        pv_root=ORCA_PV_ROOT,
        image_pv=ORCA_IMAGE_PV,
        topicpv=ORCA_TOPIC_PV,
        sourcepv=ORCA_SOURCE_PV,
    )


def create_area_detector_collector(daemon_device_harness, **collector_kwargs):
    image = daemon_device_harness.create_master(
        AreaDetector,
        name="camera",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )
    collector = daemon_device_harness.create_master(
        AreaDetectorCollector,
        name="collector",
        images=["camera"],
        **collector_kwargs,
    )
    return image, collector


def create_dual_area_detector_collector(daemon_device_harness, fake_backend):
    seed_area_detector_defaults(
        fake_backend,
        pv_root=SECOND_PV_ROOT,
        image_pv=SECOND_IMAGE_PV,
    )
    primary = daemon_device_harness.create_master(
        AreaDetector,
        name="camera_primary",
        pv_root=PV_ROOT,
        image_pv=IMAGE_PV,
    )
    secondary = daemon_device_harness.create_master(
        AreaDetector,
        name="camera_secondary",
        pv_root=SECOND_PV_ROOT,
        image_pv=SECOND_IMAGE_PV,
    )
    collector = daemon_device_harness.create_master(
        AreaDetectorCollector,
        name="collector",
        images=["camera_primary", "camera_secondary"],
    )
    return primary, secondary, collector


class TestAreaDetectorHarness:
    def test_array_info_returns_tuple_of_arraydesc(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        detector = create_area_detector(daemon_device_harness)

        info = detector.arrayInfo()

        assert isinstance(info, tuple)
        assert isinstance(info[0], ArrayDesc)

    def test_completed_reflects_acquire_status(
        self, daemon_device_harness, fake_backend
    ):
        detector = create_area_detector(daemon_device_harness)

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
        assert detector.isCompleted() is True

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"
        assert detector.isCompleted() is False

    def test_tracks_image_count_presets_and_ignores_unrelated_keys(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        detector = create_area_detector(daemon_device_harness)

        assert set(detector.presetInfo()) == {"n", "ad_1"}

        detector.setPreset(n=3)
        detector.setPreset(t=1)
        detector.setPreset()
        assert detector.preset() == {"n": 3}

    def test_channel_preset_uses_image_counter_progress(
        self, daemon_device_harness, fake_backend
    ):
        detector = create_area_detector(daemon_device_harness)

        detector.setChannelPreset("n", 2)

        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
        assert detector.iscontroller is True
        assert detector.preselection == 2
        assert detector.presetReached("n", 2, 0) is False

        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 2
        assert detector.presetReached("n", 2, 0) is True

    def test_start_marks_device_busy(self, daemon_device_harness, fake_backend):
        detector = create_area_detector(daemon_device_harness)

        detector.start(n=1)

        assert detector._current_status == (status.BUSY, "Acquiring")
        assert fake_backend.values[f"{PV_ROOT}Acquire"] == 1

    def test_completes_on_image_count_preset_before_backend_status(
        self, daemon_device_harness, fake_backend
    ):
        detector = create_area_detector(daemon_device_harness)

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"
        detector.start(n=2)
        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
        assert detector.isCompleted() is False

        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 2
        assert detector.isCompleted() is False

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
        assert detector.isCompleted() is True

    def test_completion_syncs_final_image_before_reporting_done(
        self, daemon_device_harness, fake_backend
    ):
        detector = create_area_detector(daemon_device_harness)
        final_image = np.arange(2048 * 1024, dtype=np.uint32).reshape(2048, 1024)

        detector.start(n=1)
        fake_backend.values[IMAGE_PV] = final_image.ravel()
        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"

        assert not np.array_equal(detector.readArray(FINAL), final_image)
        assert detector.isCompleted() is False

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
        assert detector.isCompleted() is True
        assert np.array_equal(detector.readArray(FINAL), final_image)

    def test_error_takes_precedence_over_reached_image_count(
        self, daemon_device_harness, fake_backend
    ):
        detector = create_area_detector(daemon_device_harness)

        detector.start(n=2)
        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 2
        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "DetectorError"
        fake_backend.values[f"{PV_ROOT}DetectorState_RBV.SEVR"] = 2

        with pytest.raises(NicosError):
            detector.isCompleted()


class TestTimepixDetectorHarness:
    def test_zero_image_preset_does_not_start_acquisition(
        self, daemon_device_harness, fake_backend, monkeypatch
    ):
        seed_timepix_defaults(fake_backend)
        detector = create_timepix_detector(daemon_device_harness)
        wait_calls = []
        monkeypatch.setattr(
            detector,
            "_wait_until",
            lambda *args, **kwargs: wait_calls.append((args, kwargs)),
        )

        detector.start(n=0)

        assert fake_backend.values[f"{TIMEPIX_PV_ROOT}Acquire"] == 0
        assert wait_calls == []

    def test_start_marks_device_busy_and_waits_for_ioc_handshake(
        self, daemon_device_harness, fake_backend, monkeypatch
    ):
        seed_timepix_defaults(fake_backend)
        detector = create_timepix_detector(daemon_device_harness)
        wait_calls = []

        def record_wait(pv_name, expected_value, precision=None, timeout=5.0):
            del precision, timeout
            wait_calls.append((pv_name, expected_value))

        monkeypatch.setattr(detector, "_wait_until", record_wait)

        detector.start(n=1)

        assert detector._current_status == (status.BUSY, "Acquiring")
        assert fake_backend.values[f"{TIMEPIX_PV_ROOT}Acquire"] == 1
        assert fake_backend.values[f"{TIMEPIX_PV_ROOT}WriteData"] == 1
        assert wait_calls[0] == ("ts_ready", 1)
        assert wait_calls[1][0] == "path_last_added"


class TestOrcaFlash4Harness:
    def test_start_without_preset_defaults_to_continuous_mode(
        self, daemon_device_harness, fake_backend
    ):
        seed_orca_defaults(fake_backend)
        detector = create_orca_flash_detector(daemon_device_harness)

        detector.start()

        assert detector._current_status == (status.BUSY, "Acquiring")
        assert fake_backend.values[f"{ORCA_PV_ROOT}Acquire"] == 1
        assert fake_backend.values[f"{ORCA_PV_ROOT}ImageMode"] == 2

    def test_start_applies_image_count_preset_in_multiple_mode(
        self, daemon_device_harness, fake_backend
    ):
        seed_orca_defaults(fake_backend)
        detector = create_orca_flash_detector(daemon_device_harness)

        detector.start(n=3)

        assert detector._current_status == (status.BUSY, "Acquiring")
        assert fake_backend.values[f"{ORCA_PV_ROOT}Acquire"] == 1
        assert fake_backend.values[f"{ORCA_PV_ROOT}ImageMode"] == 1
        assert fake_backend.values[f"{ORCA_PV_ROOT}NumImages"] == 3

    def test_error_takes_precedence_over_reached_image_count(
        self, daemon_device_harness, fake_backend
    ):
        seed_orca_defaults(fake_backend)
        detector = create_orca_flash_detector(daemon_device_harness)

        detector.start(n=2)
        fake_backend.values[f"{ORCA_PV_ROOT}NumImagesCounter_RBV"] = 2
        fake_backend.values[f"{ORCA_PV_ROOT}AcquireBusy"] = "DetectorError"
        fake_backend.values[f"{ORCA_PV_ROOT}DetectorState_RBV.SEVR"] = 2

        with pytest.raises(NicosError):
            detector.isCompleted()


class TestAreaDetectorCollectorHarness:
    def test_replaces_collector_preset_but_keeps_image_channel_state(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        image, collector = create_area_detector_collector(daemon_device_harness)

        assert [value.name for value in collector.valueInfo()] == ["camera"]
        assert "n" in collector.presetInfo()
        assert "camera" in collector.presetInfo()
        assert "t" not in collector.presetInfo()

        collector.setPreset(camera=4)
        assert image.preset() == {"n": 4}

        collector.prepare()
        collector.setPreset(t=1)
        collector.setPreset()
        assert collector.preset() == {"t": 1}
        assert image.preset() == {"n": 4}

    def test_accepts_image_count_alias_from_underlying_channel(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        image, collector = create_area_detector_collector(daemon_device_harness)

        collector.setPreset(n=3)

        assert collector.preset() == {"n": 3}
        assert image.preset() == {"n": 3}

    def test_does_not_persist_live_as_previous_preset(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        image, collector = create_area_detector_collector(daemon_device_harness)

        collector.setPreset(camera=4)
        collector.setPreset(live=True)
        collector.setPreset()

        assert collector.preset() == {"camera": 4}
        assert image.preset() == {"n": 4}

    def test_prepare_leaves_collector_ready_until_start(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        _image, collector = create_area_detector_collector(daemon_device_harness)

        collector.setPreset(camera=1)
        collector.prepare()

        assert collector.isCompleted() is True

    def test_during_measure_hook_supports_intermediate_saveintervals(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        _image, collector = create_area_detector_collector(
            daemon_device_harness,
            liveinterval=1.0,
            saveintervals=[0.2],
        )

        collector.prepare()
        collector.start()

        assert collector.duringMeasureHook(0.05) == LIVE
        assert collector.duringMeasureHook(0.25) == INTERMEDIATE
        assert collector.duringMeasureHook(1.1) == LIVE

        collector.finish()

    def test_pause_reports_unsupported_and_resume_is_noop(
        self, daemon_device_harness, fake_backend
    ):
        del fake_backend
        _image, collector = create_area_detector_collector(daemon_device_harness)

        collector.setPreset(camera=1)
        collector.prepare()
        collector.start()

        assert collector.pause() is False
        collector.resume()

        collector.finish()

    def test_completion_reads_final_image_before_collector_finishes(
        self, daemon_device_harness, fake_backend
    ):
        image, collector = create_area_detector_collector(daemon_device_harness)
        final_image = np.arange(2048 * 1024, dtype=np.uint32).reshape(2048, 1024)

        collector.setPreset(camera=1)
        collector.prepare()
        collector.start()
        fake_backend.values[IMAGE_PV] = final_image.ravel()
        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Busybusybusy"

        assert not np.array_equal(image.readArray(FINAL), final_image)
        assert collector.isCompleted() is False

        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
        assert collector.isCompleted() is True

        scalars, arrays = collector.readResults(FINAL)

        assert scalars == [1]
        assert len(arrays) == 1
        assert np.array_equal(arrays[0], final_image)

    def test_completion_matches_generic_detector_or_semantics(
        self, daemon_device_harness, fake_backend
    ):
        primary, _secondary, collector = create_dual_area_detector_collector(
            daemon_device_harness, fake_backend
        )
        final_image = np.arange(2048 * 1024, dtype=np.uint32).reshape(2048, 1024)

        collector.setPreset(camera_primary=1, camera_secondary=3)
        collector.prepare()
        collector.start()
        fake_backend.values[IMAGE_PV] = final_image.ravel()
        fake_backend.values[f"{PV_ROOT}NumImagesCounter_RBV"] = 1
        fake_backend.values[f"{PV_ROOT}AcquireBusy"] = "Done"
        fake_backend.values[f"{SECOND_PV_ROOT}AcquireBusy"] = "Busybusybusy"
        fake_backend.values[f"{SECOND_PV_ROOT}NumImagesCounter_RBV"] = 0

        assert collector.isCompleted() is True
        assert np.array_equal(primary.readArray(FINAL), final_image)

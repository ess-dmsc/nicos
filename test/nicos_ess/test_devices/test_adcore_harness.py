"""Harness tests for the generic EPICS areaDetector image channel."""

import functools
import logging
import threading
import time

import numpy
import pytest

from nicos.core import (
    FINAL,
    INTERMEDIATE,
    INTERRUPTED,
    LIVE,
    SIMULATION,
    CommunicationError,
    HardwareError,
    NicosError,
    status,
)
from nicos.devices.generic import Detector
from nicos_ess.devices.epics.adcore import AreaDetector
from nicos_ess.devices.epics.pva import epics_common
from test.nicos_ess.test_devices.doubles.adcore_camera import (
    CAM_ROOT,
    DATA_TYPES,
    IMAGE_MODES,
    IMAGE_ROOT,
    SHAPE,
    acquire_puts,
    camera_pv,
    create_camera,
    deliver,
    image_pv,
    is_acquiring,
    refuse_start,
    run_count,
    set_acquiring,
    set_state,
    take_a_frame_after_the_counter_is_read,
    take_frames,
)


@pytest.fixture
def camera(device_harness, camera_ioc):
    return create_camera(device_harness, starttimeout=0.05, finishtimeout=0.05)[0]


@pytest.fixture
def daemon(device_harness):
    return functools.partial(device_harness.run, "daemon")


def test_maxage_zero_reads_status_and_value_from_hardware(daemon, camera, camera_ioc):
    camera_ioc.values[camera_pv("NumImagesCounter_RBV")] = 17

    camera_ioc.get_calls.clear()
    daemon(camera.status, 0)
    assert daemon(camera.read, 0) == [17]

    gets = [pv for kind, pv, _ in camera_ioc.get_calls if kind == "get_pv_value"]
    assert {camera_pv("DetectorState_RBV"), camera_pv("AcquireBusy")} <= set(gets)
    assert camera_pv("NumImagesCounter_RBV") in gets
    # the message is only read to explain an Error
    assert camera_pv("StatusMessage_RBV") not in gets


def test_the_frame_is_neither_monitored_nor_cached(
    device_harness, daemon, camera, camera_ioc
):
    monitored = {pv for pv, *_ in camera_ioc.subscriptions}
    assert camera_pv("NumImagesCounter_RBV") in monitored
    assert image_pv("ArrayData") not in monitored
    # ArrayData is not connected at startup because connecting reads the whole frame.
    assert image_pv("ArrayData") not in camera_ioc.connect_calls

    run_count(device_harness, camera, camera_ioc, frames=3)
    daemon(camera.readArray, FINAL)

    cached = [camera._cache.get(camera, name) for name in ("value", *camera.parameters)]
    assert not any(isinstance(value, numpy.ndarray) for value in cached)


def test_shape_and_dtype_come_from_the_plugin(device_harness, camera_ioc):
    camera_ioc.values[image_pv("DataType_RBV")] = DATA_TYPES.index("Float32")
    camera, _poller = create_camera(device_harness)

    assert camera.arrayInfo()[0].shape == SHAPE
    assert camera.arrayInfo()[0].dtype == numpy.float32


def test_a_wider_waveform_is_cast_to_the_declared_dtype(
    device_harness, daemon, camera, camera_ioc
):
    # ADOrca IOCs carry UInt16 NDArrays in a LONG waveform.
    run_count(device_harness, camera, camera_ioc)
    size = int(numpy.prod(SHAPE))
    camera_ioc.values[image_pv("ArrayData")] = numpy.arange(size, dtype=numpy.int32)

    frame = daemon(camera.readArray, FINAL)

    assert frame.dtype == numpy.uint16
    assert frame.shape == SHAPE
    assert frame[-1, -1] == size - 1


def test_a_payload_that_does_not_fit_the_shape_is_refused(
    device_harness, daemon, camera, camera_ioc
):
    run_count(device_harness, camera, camera_ioc)
    camera_ioc.values[image_pv("ArrayData")] = numpy.arange(7, dtype=numpy.uint16)

    with pytest.raises(CommunicationError, match="7 elements"):
        daemon(camera.readArray, FINAL)


def test_a_plugin_without_a_frame_keeps_the_last_shape(
    device_harness, daemon, camera_ioc
):
    camera_ioc.values[image_pv("NDimensions_RBV")] = 0
    camera, _poller = create_camera(device_harness)
    daemon(camera.prepare)
    assert camera.arrayInfo()[0].shape == (1, 1)

    camera_ioc.values[image_pv("NDimensions_RBV")] = len(SHAPE)
    run_count(device_harness, camera, camera_ioc)
    daemon(camera.readArray, FINAL)
    assert camera.arrayInfo()[0].shape == SHAPE

    # This is what the plugin reports after its IOC was restarted.
    camera_ioc.values[image_pv("NDimensions_RBV")] = 0
    daemon(camera.prepare)
    assert camera.arrayInfo()[0].shape == SHAPE


def test_frames_have_up_to_three_dimensions(device_harness, daemon, camera, camera_ioc):
    camera_ioc.values[image_pv("NDimensions_RBV")] = 3
    camera_ioc.values[image_pv("ArraySize2_RBV")] = 2
    camera_ioc.values[image_pv("ArrayData")] = numpy.zeros(48, numpy.uint16)
    run_count(device_harness, camera, camera_ioc)
    assert daemon(camera.readArray, FINAL).shape == (2, *SHAPE)

    camera_ioc.values[image_pv("NDimensions_RBV")] = 4
    with pytest.raises(CommunicationError, match="reports 4 dimensions"):
        daemon(camera.prepare)


def test_an_unknown_data_type_is_refused(daemon, camera, camera_ioc):
    camera_ioc.value_choices[image_pv("DataType_RBV")] = ["Int128"]
    camera_ioc.values[image_pv("DataType_RBV")] = 0

    with pytest.raises(CommunicationError, match="unknown data type 'Int128'"):
        daemon(camera.prepare)


@pytest.mark.parametrize(
    "preset, mode", [(None, "Continuous"), (1, "Single"), (70, "Multiple")]
)
def test_the_preset_picks_the_image_mode(daemon, camera, camera_ioc, preset, mode):
    if preset:
        daemon(camera.setChannelPreset, camera.name, preset)

    daemon(camera.start)

    assert camera_ioc.values[camera_pv("ImageMode")] == IMAGE_MODES.index(mode)
    assert camera_ioc.values[camera_pv("NumImages")] == (70 if preset == 70 else 1)


def test_completion_follows_acquire_busy_not_the_counter(daemon, camera, camera_ioc):
    daemon(camera.setChannelPreset, camera.name, 5)

    daemon(camera.start)
    # start waits until the IOC reports that it acquires
    assert daemon(camera.status, 0)[0] == status.BUSY
    take_frames(camera_ioc, 7)
    assert daemon(camera.isCompleted) is False

    set_acquiring(camera_ioc, False)
    assert daemon(camera.isCompleted) is True


def test_a_refused_start_raises_with_the_ioc_message(daemon, camera, camera_ioc):
    refuse_start(camera_ioc, "Acquire Period must be greater than ReadoutTime")

    with pytest.raises(HardwareError, match="Acquire Period must be greater"):
        daemon(camera.start)


def test_a_start_whose_busy_flash_was_missed_counts_by_the_frames(
    daemon, camera, camera_ioc
):
    plain_put = type(camera_ioc).put_pv_value.__get__(camera_ioc)

    def over_without_busy(pvname, value, wait=False):
        plain_put(pvname, value, wait)
        if pvname == camera_pv("Acquire") and value:
            take_frames(camera_ioc, 1)

    camera_ioc.put_pv_value = over_without_busy

    daemon(camera.start)

    assert acquire_puts(camera_ioc) == [1]


def test_the_start_sees_a_busy_flash_during_the_put(device_harness, daemon, camera_ioc):
    camera = create_camera(device_harness, starttimeout=5, finishtimeout=0.05)[0]
    put = camera_ioc.put_pv_value

    def over_at_once(pvname, value, wait=False):
        put(pvname, value, wait)
        if pvname == camera_pv("Acquire") and value:
            set_acquiring(camera_ioc, False)

    camera_ioc.put_pv_value = over_at_once

    started = time.monotonic()
    daemon(camera.start)

    assert time.monotonic() - started < 1


def test_prepare_stops_a_leftover_acquisition(daemon, camera, camera_ioc, caplog):
    daemon(camera.prepare)
    assert acquire_puts(camera_ioc) == []  # an idle camera is left alone

    set_acquiring(camera_ioc, True)
    daemon(camera.prepare)

    assert not is_acquiring(camera_ioc)
    assert "still acquiring, so it is stopped first" in caplog.text


def test_prepare_fails_when_the_camera_does_not_stop(daemon, camera, camera_ioc):
    set_acquiring(camera_ioc, True)
    put = camera_ioc.put_pv_value
    camera_ioc.put_pv_value = lambda pv, value, wait=False: (
        put(pv, value, wait) if pv != camera_pv("Acquire") else None
    )

    with pytest.raises(HardwareError, match="did not stop within"):
        daemon(camera.prepare)


def test_a_follower_pauses_by_stopping_and_resumes_by_restarting(
    daemon, camera, camera_ioc
):
    daemon(camera.start)

    assert daemon(camera.pause) is True
    assert not is_acquiring(camera_ioc)
    daemon(camera.resume)
    assert is_acquiring(camera_ioc)


def test_a_controller_refuses_to_pause(daemon, camera, camera_ioc):
    daemon(camera.setChannelPreset, camera.name, 5)
    daemon(camera.start)

    assert daemon(camera.pause) is False
    assert is_acquiring(camera_ioc)


def test_a_refused_resume_raises(daemon, camera, camera_ioc):
    # frames taken before the pause must not make the refused resume look started
    daemon(camera.start)
    take_frames(camera_ioc, 3)
    daemon(camera.pause)
    refuse_start(camera_ioc, "no triggers")

    with pytest.raises(HardwareError, match="no triggers"):
        daemon(camera.resume)


def test_detector_states(daemon, camera, camera_ioc):
    set_state(camera_ioc, "Aborted")
    assert daemon(camera.status, 0) == (status.OK, "")
    set_state(camera_ioc, "Disconnected")
    assert daemon(camera.status, 0) == (status.ERROR, "Disconnected")
    set_state(camera_ioc, "Error", "Acquisition timeout")
    assert daemon(camera.status, 0) == (status.WARN, "Error: Acquisition timeout")
    camera_ioc.emit_update(camera_pv("DetectorState_RBV"), value=42)
    assert daemon(camera.status, 0) == (status.WARN, "unknown detector state 42")


def test_monitor_updates_reach_the_cache(device_harness, camera, camera_ioc):
    camera_ioc.emit_update(camera_pv("NumImagesCounter_RBV"), value=7)
    set_acquiring(camera_ioc, True)

    assert camera._cache.get(camera, "value") == 7
    assert camera._cache.get(camera, "status")[0] == status.BUSY


def test_stop_ends_the_acquisition(daemon, camera, camera_ioc):
    daemon(camera.start)
    daemon(camera.stop)

    assert acquire_puts(camera_ioc) == [1, 0]


def test_a_count_leaves_no_subscription_open(device_harness, camera, camera_ioc):
    subscriptions = len(camera_ioc.subscriptions)

    run_count(device_harness, camera, camera_ioc, frames=2, preset=2)
    device_harness.run("daemon", camera.readArray, FINAL)

    assert len(camera_ioc.subscriptions) == subscriptions


def test_a_normal_count_logs_no_warning(
    device_harness, daemon, camera, camera_ioc, caplog
):
    run_count(device_harness, camera, camera_ioc, frames=2, preset=2)
    daemon(camera.readArray, FINAL)

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_a_dry_run_counts_the_preset_times_the_period(device_harness, camera_ioc):
    camera = device_harness.create(
        "daemon",
        AreaDetector,
        name="dry_camera",
        mode=SIMULATION,
        pv_root=CAM_ROOT,
        image_pv_root=IMAGE_ROOT,
        acquireperiod=0.2,
    )
    with device_harness.activate("daemon") as session:
        session.setMode(SIMULATION)
        started = session.clock.time
        camera.start()
        camera.finish()
        assert session.clock.time == started

        camera.setChannelPreset(camera.name, 4)
        camera.start()
        camera.finish()
        assert session.clock.time == pytest.approx(started + 4 * 0.2)


def run_on_detector(device_harness, daemon, preset=5):
    detector = device_harness.create_daemon(Detector, name="det", images=["camera"])
    daemon(detector.prepare)
    daemon(detector.start, camera=preset)
    return detector


@pytest.mark.parametrize("cause", ["unknown state", "lost connection"])
def test_a_camera_that_cannot_be_read_keeps_the_count_running(
    device_harness, daemon, camera, camera_ioc, cause
):
    detector = run_on_detector(device_harness, daemon)
    take_frames(camera_ioc, 1)
    if cause == "unknown state":
        camera_ioc.emit_update(camera_pv("DetectorState_RBV"), value=42)
    else:
        camera_ioc.disconnect_backend()
    assert daemon(detector.isCompleted) is False

    camera_ioc.connect_backend()
    set_acquiring(camera_ioc, False)
    assert daemon(detector.isCompleted) is True


@pytest.mark.parametrize("end", ["finish", "stop"])
def test_the_poller_shows_an_error_only_during_a_run(
    device_harness, daemon, camera_ioc, end
):
    camera, poller = create_camera(
        device_harness, starttimeout=0.05, finishtimeout=0.05
    )
    daemon(camera.start)

    set_state(camera_ioc, "Error", "trigger timeout")

    error = (status.ERROR, "Error: trigger timeout")
    assert device_harness.run("poller", poller.status, 0) == error
    assert camera._cache.get(camera, "status") == error

    set_acquiring(camera_ioc, False, "Error")
    daemon(getattr(camera, end))
    assert camera._cache.get(camera, "status") == (status.WARN, error[1])


def test_an_alarm_on_the_counter_during_a_run_is_not_shown_as_busy(
    daemon, camera, camera_ioc
):
    daemon(camera.start)
    alarm = (status.UNKNOWN, "INVALID alarm")
    camera_ioc.alarms[camera_pv("NumImagesCounter_RBV")] = alarm

    assert daemon(camera.status, 0) == alarm


def test_prepare_ends_a_run_that_was_never_finished(
    device_harness, daemon, camera, camera_ioc
):
    # nicos.core.acquire does not stop the detector when another channel of it
    # fails to start, so the camera run is neither finished nor stopped.
    detector = run_on_detector(device_harness, daemon)
    set_acquiring(camera_ioc, False)
    set_state(camera_ioc, "Error", "trigger timeout")

    daemon(detector.prepare)

    assert daemon(detector.isCompleted) is True


def test_an_error_left_by_the_last_run_does_not_block_the_next_count(
    device_harness, daemon, camera, camera_ioc
):
    detector = device_harness.create_daemon(Detector, name="det", images=["camera"])
    set_state(camera_ioc, "Error")

    daemon(detector.prepare)
    assert daemon(detector.isCompleted) is True
    daemon(detector.start, camera=1)

    assert acquire_puts(camera_ioc) == [1]
    assert is_acquiring(camera_ioc)


def test_an_error_during_the_run_fails_the_count(
    device_harness, daemon, camera, camera_ioc
):
    detector = run_on_detector(device_harness, daemon)
    set_acquiring(camera_ioc, False)
    set_state(camera_ioc, "Error", "Acquisition timeout")

    with pytest.raises(NicosError, match="Acquisition timeout"):
        daemon(detector.isCompleted)


def test_dropped_arrays_are_not_a_status(daemon, camera, camera_ioc):
    camera_ioc.emit_update(image_pv("DroppedArrays_RBV"), value=12)

    assert daemon(camera.status, 0) == (status.OK, "")


def test_dropped_arrays_are_logged_once_per_rise(device_harness, camera_ioc, caplog):
    create_camera(device_harness)

    for count in (12, 12, 15):
        camera_ioc.emit_update(image_pv("DroppedArrays_RBV"), value=count)

    assert caplog.text.count("dropped 12 arrays") == 1
    assert caplog.text.count("dropped 15 arrays") == 1


def test_the_two_iocs_are_tracked_separately(device_harness, camera_ioc):
    _camera, poller = create_camera(device_harness)
    lost = epics_common.LOST_CONNECTION_STATUS

    camera_ioc.emit_connection(camera_pv("DetectorState_RBV"), False)
    assert device_harness.run("poller", poller.status, None) == lost
    camera_ioc.emit_connection(image_pv("DataType_RBV"), False)
    camera_ioc.emit_connection(camera_pv("DetectorState_RBV"), True)
    assert device_harness.run("poller", poller.status, None) == lost

    camera_ioc.emit_connection(image_pv("DataType_RBV"), True)
    assert device_harness.run("poller", poller.status, None)[0] == status.OK


def test_nothing_is_handed_out_before_a_count(daemon, camera):
    for quality in (LIVE, INTERMEDIATE, FINAL, INTERRUPTED):
        assert daemon(camera.readArray, quality) is None


def test_live_shows_nothing_until_the_first_new_frame(
    device_harness, daemon, camera, camera_ioc
):
    run_count(device_harness, camera, camera_ioc, frames=2)

    daemon(camera.start)
    assert daemon(camera.readArray, LIVE) is None

    take_frames(camera_ioc, 1)
    assert (daemon(camera.readArray, LIVE) == 3).all()


def test_live_sends_each_frame_once(daemon, camera, camera_ioc):
    daemon(camera.start)
    take_frames(camera_ioc, 1)

    assert (daemon(camera.readArray, LIVE) == 1).all()
    assert daemon(camera.readArray, LIVE) is None
    assert (daemon(camera.readArray, FINAL) == 1).all()

    take_frames(camera_ioc, 1)
    assert (daemon(camera.readArray, LIVE) == 2).all()


def test_a_frame_that_arrives_during_a_live_read_is_sent_next(
    daemon, camera, camera_ioc
):
    daemon(camera.start)
    take_frames(camera_ioc, 1)
    get = camera_ioc.get_pv_value

    def next_frame_after_the_data(pvname, as_string=False):
        value = get(pvname, as_string)
        if pvname == image_pv("ArrayData"):
            camera_ioc.get_pv_value = get
            take_frames(camera_ioc, 1)
        return value

    camera_ioc.get_pv_value = next_frame_after_the_data

    assert (daemon(camera.readArray, LIVE) == 1).all()
    assert (daemon(camera.readArray, LIVE) == 2).all()


def end_with_the_plugin_behind(daemon, camera, backend, plugin_holds):
    """Let the driver take 3 frames while the plugin only holds *plugin_holds*.

    With None the plugin receives none of the 3 frames.
    """
    daemon(camera.start)
    take_frames(backend, 3, plugin_follows=False)
    if plugin_holds is not None:
        deliver(backend, plugin_holds)
    set_acquiring(backend, False)
    daemon(camera.finish)


def test_final_waits_for_the_plugin_to_receive_the_last_frame(
    daemon, camera, camera_ioc
):
    daemon(setattr, camera, "finishtimeout", 2)
    end_with_the_plugin_behind(daemon, camera, camera_ioc, 2)

    late = threading.Timer(0.1, deliver, args=(camera_ioc, 3))
    late.start()
    try:
        assert (daemon(camera.readArray, FINAL) == 3).all()
    finally:
        late.cancel()


def test_final_reports_a_plugin_that_never_catches_up(
    daemon, camera, camera_ioc, caplog
):
    end_with_the_plugin_behind(daemon, camera, camera_ioc, 2)

    assert (daemon(camera.readArray, FINAL) == 2).all()
    assert "did not receive the last frame (3)" in caplog.text


def test_final_never_hands_out_a_frame_of_an_earlier_run(
    daemon, camera, camera_ioc, caplog
):
    deliver(camera_ioc, 9)  # frame 9 is left over from before the start
    end_with_the_plugin_behind(daemon, camera, camera_ioc, None)

    assert daemon(camera.readArray, FINAL) is None
    assert "received no frame of this acquisition" in caplog.text


@pytest.mark.parametrize("quality", [LIVE, INTERMEDIATE, FINAL])
def test_frames_that_the_plugin_owes_the_last_run_are_not_handed_out(
    daemon, camera, camera_ioc, quality
):
    end_with_the_plugin_behind(daemon, camera, camera_ioc, 1)
    daemon(camera.start)
    take_frames(camera_ioc, 1, plugin_follows=False)
    deliver(camera_ioc, 3)
    set_acquiring(camera_ioc, False)
    daemon(camera.finish)

    assert daemon(camera.readArray, quality) is None


@pytest.mark.parametrize("held", [500, 3])
def test_frames_count_after_array_counter_was_reset(
    device_harness, daemon, camera_ioc, held
):
    # An operator can set ArrayCounter to 0 on the OPI screen, and the plugin
    # keeps its last frame.
    camera = create_camera(device_harness, starttimeout=0.05, finishtimeout=2)[0]
    deliver(camera_ioc, held)
    daemon(camera.start)
    assert daemon(camera.readArray, LIVE) is None

    take_frames(camera_ioc, 3, plugin_follows=False)
    set_acquiring(camera_ioc, False)
    daemon(camera.finish)
    late = threading.Timer(0.1, deliver, args=(camera_ioc, 3))
    late.start()
    try:
        assert (daemon(camera.readArray, FINAL) == 3).all()
    finally:
        late.cancel()


def test_final_takes_a_frame_that_came_after_the_counter_was_read(
    device_harness, daemon, camera_ioc, caplog
):
    camera = create_camera(device_harness, starttimeout=0.05, finishtimeout=2)[0]
    run_count(device_harness, camera, camera_ioc, frames=3)
    take_a_frame_after_the_counter_is_read(camera_ioc)
    started = time.monotonic()

    assert (daemon(camera.readArray, FINAL) == 4).all()
    assert time.monotonic() - started < 1
    assert "did not receive" not in caplog.text


def test_final_without_any_frame_is_empty(
    device_harness, daemon, camera, camera_ioc, caplog
):
    run_count(device_harness, camera, camera_ioc, frames=0)

    assert daemon(camera.readArray, FINAL) is None
    assert "no image was acquired" in caplog.text


def test_the_no_image_warning_follows_the_image_counter(
    device_harness, daemon, camera, camera_ioc, caplog
):
    run_count(device_harness, camera, camera_ioc, frames=0)
    camera_ioc.values[camera_pv("NumImagesCounter_RBV")] = (
        3  # ArrayCounter did not move
    )

    assert daemon(camera.readArray, FINAL) is None
    assert "no image was acquired" not in caplog.text
    assert "received no frame of this acquisition" in caplog.text


def test_a_dead_ioc_fails_only_the_final_read(daemon, camera, camera_ioc):
    daemon(camera.start)
    take_frames(camera_ioc, 4)
    daemon(camera.stop)
    assert (daemon(camera.readArray, INTERRUPTED) == 4).all()

    camera_ioc.disconnect_backend()
    for quality in (LIVE, INTERMEDIATE, INTERRUPTED):
        assert daemon(camera.readArray, quality) is None
    with pytest.raises(CommunicationError):
        daemon(camera.readArray, FINAL)


def test_the_device_is_creatable_in_simulation_mode(device_harness, camera_ioc):
    camera = device_harness.create(
        "daemon",
        AreaDetector,
        name="sim_camera",
        mode=SIMULATION,
        pv_root=CAM_ROOT,
        image_pv_root=IMAGE_ROOT,
    )

    assert camera.readArray(FINAL).shape == (1, 1)


def test_settings_are_read_from_and_written_to_the_ioc(daemon, camera, camera_ioc):
    # the volatile parameters read values that were changed on the OPI screen
    camera_ioc.values[camera_pv("AcquireTime_RBV")] = 0.25
    camera_ioc.values[camera_pv("ImageMode_RBV")] = IMAGE_MODES.index("Multiple")
    assert daemon(getattr, camera, "acquiretime") == 0.25
    assert daemon(getattr, camera, "imagemode") == "Multiple"

    daemon(setattr, camera, "acquiretime", 0.5)
    daemon(setattr, camera, "imagemode", "Single")
    assert camera_ioc.values[camera_pv("AcquireTime")] == 0.5
    assert camera_ioc.values[camera_pv("ImageMode")] == IMAGE_MODES.index("Single")


def test_a_paused_follower_reports_all_images_of_the_count(daemon, camera, camera_ioc):
    daemon(camera.start)
    take_frames(camera_ioc, 7)
    assert daemon(camera.read, 0) == [7]
    assert daemon(camera.pause)
    daemon(camera.resume)
    take_frames(camera_ioc, 3)
    daemon(camera.finish)

    assert daemon(camera.read, 0) == [10]

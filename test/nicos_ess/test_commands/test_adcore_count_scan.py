"""Tests of what the adcore image channel sends to ``session.updateLiveData``
in the real NICOS count loop.

The fake camera in the backend fixture takes its images right away on
``Acquire``. Without a preset it takes one image and keeps acquiring until NICOS
stops it, like a long exposure. The camera in the slow_backend fixture takes
its images over time.
"""

import threading
import time

import numpy
import pytest

from nicos.commands.measure import count
from nicos.commands.scan import scan
from nicos.devices.epics.pva import caproto, p4p
from test.nicos_ess.command_helpers import (
    loaded_setup,
    scan_positions,
    set_detectors,
)
from test.nicos_ess.test_devices.doubles import FakeEpicsBackend
from test.nicos_ess.test_devices.doubles.adcore_camera import (
    IMAGE_MODES,
    acquire_puts,
    camera_pv,
    image_pv,
    seed_camera,
    set_acquiring,
    take_frames,
)

session_setup = None

STALE_FRAME_VALUE = 999
# This is longer than the liveinterval of 0.05 s in the setup.
FRAME_PERIOD = 0.1


def camera_with_a_stale_frame(monkeypatch):
    backend = seed_camera(FakeEpicsBackend())
    monkeypatch.setattr(p4p, "P4pWrapper", lambda timeout: backend)
    monkeypatch.setattr(caproto, "CaprotoWrapper", lambda timeout: backend)
    # The plugin still holds the previous run's last image.
    size = backend.values[image_pv("ArrayData")].size
    backend.values[image_pv("ArrayData")] = numpy.full(
        size, STALE_FRAME_VALUE, "uint16"
    )
    return backend


@pytest.fixture
def backend(monkeypatch):
    backend = camera_with_a_stale_frame(monkeypatch)
    put = backend.put_pv_value

    def acquire_at_once(pvname, value, wait=False):
        put(pvname, value, wait)
        if pvname != camera_pv("Acquire") or not value:
            return
        mode = IMAGE_MODES[backend.values[camera_pv("ImageMode")]]
        if mode == "Continuous":
            take_frames(backend, 1)
            return
        take_frames(
            backend, 1 if mode == "Single" else backend.values[camera_pv("NumImages")]
        )
        set_acquiring(backend, False)

    backend.put_pv_value = acquire_at_once
    return backend


@pytest.fixture
def slow_backend(monkeypatch):
    """A camera that takes one image every FRAME_PERIOD after Acquire.

    The plugin holds the stale image during the first live ticks of a count.
    """
    backend = camera_with_a_stale_frame(monkeypatch)
    put = backend.put_pv_value
    threads = []

    def acquire_slowly(count):
        for _ in range(count):
            time.sleep(FRAME_PERIOD)
            take_frames(backend, 1)
        set_acquiring(backend, False)

    def acquire_over_time(pvname, value, wait=False):
        put(pvname, value, wait)
        if pvname == camera_pv("Acquire") and value:
            thread = threading.Thread(
                target=acquire_slowly,
                args=(backend.values[camera_pv("NumImages")],),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

    backend.put_pv_value = acquire_over_time
    yield backend
    for thread in threads:
        thread.join(timeout=5)


def test_live_updates_show_the_images_in_order_and_end_with_the_last(
    session, slow_backend, live_updates
):
    with loaded_setup(session, "ess_adcore_count_scan"):
        set_detectors(session, "det")
        count(cam=8)

    received = live_updates.frames()
    assert {det for det, _frame in received} == {"det"}
    frames = [int(frame.data.flat[0]) for _det, frame in received]
    # The stale image from the previous run must never be shown.
    assert STALE_FRAME_VALUE not in frames
    assert frames[0] < 8
    assert frames == sorted(frames)
    _det, last = received[-1]
    assert (last.data == 8).all()


def test_the_image_is_sent_in_the_smallest_type_that_holds_it(
    session, backend, live_updates
):
    with loaded_setup(session, "ess_adcore_count_scan"):
        set_detectors(session, "det")
        count(cam=1)

    _det, last = live_updates.frames()[-1]
    assert (last.data == 1).all()
    assert last.data.dtype == numpy.uint8


def test_a_long_exposure_is_not_resent_on_every_live_tick(
    session, backend, live_updates
):
    # A 0.3 s count with a liveinterval of 0.05 s has six live ticks. The one
    # image still goes out only once live and once as the final result.
    with loaded_setup(session, "ess_adcore_count_scan"):
        set_detectors(session, "det")
        count(t=0.3)

    received = live_updates.frames()
    assert len(received) == 2
    assert all((frame.data == 1).all() for _det, frame in received)


def test_a_timed_count_stops_the_camera(session, backend, live_updates):
    with loaded_setup(session, "ess_adcore_count_scan"):
        set_detectors(session, "det")
        count(t=0.1)

    assert backend.values[camera_pv("AcquireBusy")] == 0


def test_each_scan_point_is_one_acquisition(session, backend, live_updates):
    with loaded_setup(session, "ess_adcore_count_scan"):
        set_detectors(session, "det")
        scan(session.getDevice("axis"), 0, 1, 2, cam=2)
        dataset = session.experiment.data.getLastScans()[-1]

    assert scan_positions(dataset) == [0.0, 1.0]
    assert acquire_puts(backend).count(1) == 2
    cam_index = [info.name for info in dataset.detvalueinfo].index("cam")
    assert [point[cam_index] for point in dataset.detvaluelists] == [2, 2]
    # The image counter keeps running over the scan, so the second point ends
    # on image 4.
    received = live_updates.frames()
    assert [int(frame.data.flat[0]) for _det, frame in received] == [2, 4]

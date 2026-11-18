"""A fake EPICS areaDetector camera with an image plugin for the adcore tests."""

import numpy

from nicos_ess.devices.epics.adcore import AreaDetector

CAM_ROOT = "SIM:AD:cam1:"
IMAGE_ROOT = "SIM:AD:image1:"
SHAPE = (4, 6)

# The choice lists follow the order in ADBase.template and NDArrayBase.template.
DETECTOR_STATES = [
    "Idle",
    "Acquire",
    "Readout",
    "Correct",
    "Saving",
    "Aborting",
    "Error",
    "Waiting",
    "Initializing",
    "Disconnected",
    "Aborted",
]
DATA_TYPES = [f"{u}Int{bits}" for bits in (8, 16, 32, 64) for u in ("", "U")]
DATA_TYPES += ["Float32", "Float64"]
IMAGE_MODES = ["Single", "Multiple", "Continuous"]
ACQUIRE_BUSY = ["Done", "Acquiring"]


def camera_pv(suffix):
    return f"{CAM_ROOT}{suffix}"


def image_pv(suffix):
    return f"{IMAGE_ROOT}{suffix}"


def seed_camera(backend):
    """Set up an idle camera whose image plugin holds frame 0 of SHAPE."""
    backend.values.update(
        {
            camera_pv("NumImagesCounter_RBV"): 0,
            camera_pv("ArrayCounter_RBV"): 0,
            camera_pv("Acquire"): 0,
            camera_pv("AcquireBusy"): 0,
            camera_pv("DetectorState_RBV"): 0,
            camera_pv("StatusMessage_RBV"): "",
            camera_pv("ImageMode"): 2,
            camera_pv("ImageMode_RBV"): 2,
            camera_pv("NumImages"): 1,
            camera_pv("NumImages_RBV"): 1,
            camera_pv("AcquireTime"): 0.1,
            camera_pv("AcquireTime_RBV"): 0.1,
            camera_pv("AcquirePeriod"): 0.2,
            camera_pv("AcquirePeriod_RBV"): 0.2,
            camera_pv("NumExposures"): 1,
            camera_pv("NumExposures_RBV"): 1,
            camera_pv("ArrayRate_RBV"): 5.0,
            image_pv("ArrayData"): numpy.zeros(int(numpy.prod(SHAPE)), numpy.uint16),
            image_pv("UniqueId_RBV"): 0,
            image_pv("ArrayCounter_RBV"): 0,
            image_pv("NDimensions_RBV"): len(SHAPE),
            image_pv("ArraySize0_RBV"): SHAPE[1],
            image_pv("ArraySize1_RBV"): SHAPE[0],
            image_pv("ArraySize2_RBV"): 0,
            image_pv("DataType_RBV"): DATA_TYPES.index("UInt16"),
            image_pv("DroppedArrays_RBV"): 0,
        }
    )
    backend.value_choices[camera_pv("AcquireBusy")] = ACQUIRE_BUSY
    backend.value_choices[camera_pv("DetectorState_RBV")] = DETECTOR_STATES
    backend.value_choices[camera_pv("ImageMode_RBV")] = IMAGE_MODES
    backend.value_choices[image_pv("DataType_RBV")] = DATA_TYPES

    put = backend.put_pv_value

    def put_like_the_ioc(pvname, value, wait=False):
        put(pvname, value, wait)
        # The IOC ignores a stop of a camera that does not acquire.
        if pvname == camera_pv("Acquire") and (value or is_acquiring(backend)):
            if value:
                backend.values[camera_pv("NumImagesCounter_RBV")] = 0
            set_acquiring(backend, bool(value))

    backend.put_pv_value = put_like_the_ioc
    return backend


def set_acquiring(backend, acquiring, state=None):
    state = state or ("Acquire" if acquiring else "Idle")
    backend.emit_update(
        camera_pv("DetectorState_RBV"), value=DETECTOR_STATES.index(state)
    )
    backend.emit_update(camera_pv("AcquireBusy"), value=int(acquiring))


def is_acquiring(backend):
    return backend.values[camera_pv("AcquireBusy")] == 1


def set_state(backend, state, message=""):
    backend.emit_update(camera_pv("StatusMessage_RBV"), value=message)
    backend.emit_update(
        camera_pv("DetectorState_RBV"), value=DETECTOR_STATES.index(state)
    )


def refuse_start(backend, message):
    """Make the IOC answer Acquire=1 with Aborted and *message* like ADOrca does."""
    put = backend.put_pv_value

    def refuse(pvname, value, wait=False):
        if pvname == camera_pv("Acquire") and value:
            backend.values[camera_pv("StatusMessage_RBV")] = message
            set_acquiring(backend, False, "Aborted")
            return
        put(pvname, value, wait)

    backend.put_pv_value = refuse


def take_a_frame_after_the_counter_is_read(backend):
    """Make the camera take one frame right after the next read of ArrayCounter."""
    get = backend.get_pv_value

    def get_then_take(pvname, as_string=False):
        value = get(pvname, as_string)
        if pvname == camera_pv("ArrayCounter_RBV"):
            backend.get_pv_value = get
            take_frames(backend, 1)
        return value

    backend.get_pv_value = get_then_take


def deliver(backend, unique_id):
    """Let the image plugin receive frame *unique_id*, filled with that number."""
    size = backend.values[image_pv("ArrayData")].size
    backend.values[image_pv("ArrayData")] = numpy.full(size, unique_id, numpy.uint16)
    backend.emit_update(image_pv("UniqueId_RBV"), value=unique_id)
    received = backend.values[image_pv("ArrayCounter_RBV")] + 1
    backend.emit_update(image_pv("ArrayCounter_RBV"), value=received)


def take_frames(backend, count=1, plugin_follows=True):
    for _ in range(count):
        unique_id = backend.values[camera_pv("ArrayCounter_RBV")] + 1
        backend.values[camera_pv("ArrayCounter_RBV")] = unique_id
        backend.values[camera_pv("NumImagesCounter_RBV")] += 1
        if plugin_follows:
            deliver(backend, unique_id)


def run_count(device_harness, camera, backend, frames=1, preset=None):
    """Start a count, take *frames* frames, let the driver end the run and finish."""
    if preset is not None:
        device_harness.run("daemon", camera.setChannelPreset, camera.name, preset)
    device_harness.run("daemon", camera.start)
    take_frames(backend, frames)
    set_acquiring(backend, False)
    device_harness.run("daemon", camera.finish)


def create_camera(device_harness, device_class=AreaDetector, name="camera", **config):
    """Create the daemon and poller copies of a camera on the fake IOC."""
    shared = {"pv_root": CAM_ROOT, "image_pv_root": IMAGE_ROOT, "pva": True}
    shared.update(config)
    return device_harness.create_pair(device_class, name=name, shared=shared)


def puts_to(backend, suffix):
    return [value for pv, value, _wait in backend.put_calls if pv == camera_pv(suffix)]


def acquire_puts(backend):
    return puts_to(backend, "Acquire")

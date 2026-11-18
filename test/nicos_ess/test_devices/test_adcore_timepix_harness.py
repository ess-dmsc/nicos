"""Harness tests for the TimePix3 camera with EMPIR processing."""

import pytest

from nicos.core import CommunicationError
from nicos_ess.devices.epics.adcore import TimepixDetector
from test.nicos_ess.test_devices.doubles.adcore_camera import (
    CAM_ROOT,
    acquire_puts,
    camera_pv,
    create_camera,
    puts_to,
    run_count,
)


def text(chars):
    return bytes(chars).decode().rstrip("\x00")


@pytest.fixture
def tpx_backend(camera_ioc):
    camera_ioc.values.update(
        {
            camera_pv("CHIP0_Vth_fine"): 99,
            camera_pv("CHIP0_Vth_fine_RBV"): 100,
            camera_pv("CHIP0_Vth_coarse"): 6,
            camera_pv("CHIP0_Vth_coarse_RBV"): 7,
            camera_pv("EvFlit_PhMin"): 2.0,
            camera_pv("EvFlit_PsdMin"): 0.5,
            camera_pv("N_Processing"): 0,
            camera_pv("RawFilePath"): [0],
            camera_pv("WriteData"): 0,
            camera_pv("TSReady"): 1,
            camera_pv("PathToAdd"): [0],
            camera_pv("PathLastAdded"): [0],
        }
    )
    camera_ioc.trigger_arrives = camera_ioc.empir_follows = True
    ioc_put = camera_ioc.put_pv_value

    def put(pvname, value, wait=False):
        ioc_put(pvname, value, wait)
        if pvname == camera_pv("Acquire") and value and camera_ioc.trigger_arrives:
            camera_ioc.emit_update(camera_pv("TSReady"), value=1)
        elif pvname == camera_pv("PathToAdd") and camera_ioc.empir_follows:
            camera_ioc.emit_update(camera_pv("PathLastAdded"), value=value)

    camera_ioc.put_pv_value = put
    return camera_ioc


def create_timepix(device_harness, **config):
    config.setdefault("starttimeout", 0.1)
    return create_camera(device_harness, TimepixDetector, "tpx", **config)


def test_the_raw_folder_is_set_in_prepare_and_handed_to_empir_after_the_start(
    device_harness, tpx_backend
):
    tpx, _poller = create_timepix(device_harness, rawdir="file:/scratch")

    device_harness.run("daemon", tpx.prepare)
    run_count(device_harness, tpx, tpx_backend, frames=1, preset=1)

    order = [pv.removeprefix(CAM_ROOT) for pv, _v, _w in tpx_backend.put_calls]
    assert order[:3] == ["RawFilePath", "WriteData", "TSReady"]
    assert order.index("Acquire") < order.index("PathToAdd")
    folder = text(tpx_backend.values[camera_pv("PathToAdd")])
    assert folder.startswith("raw_tpx_")
    assert (
        text(tpx_backend.values[camera_pv("RawFilePath")]) == f"file:/scratch/{folder}"
    )


def test_each_acquisition_gets_its_own_raw_folder(device_harness, tpx_backend):
    tpx, _poller = create_timepix(device_harness, rawdir="file:/scratch")

    for _ in range(2):
        device_harness.run("daemon", tpx.prepare)
        run_count(device_harness, tpx, tpx_backend, frames=1, preset=1)

    folders = [text(value) for value in puts_to(tpx_backend, "PathToAdd")]
    assert len(folders) == 2
    assert folders[0] != folders[1]
    raw_paths = [text(value) for value in puts_to(tpx_backend, "RawFilePath")]
    assert raw_paths == [f"file:/scratch/{folder}" for folder in folders]


def test_without_a_trigger_the_start_fails_before_empir_gets_the_folder(
    device_harness, tpx_backend
):
    tpx, _poller = create_timepix(device_harness)
    tpx_backend.trigger_arrives = False

    device_harness.run("daemon", tpx.prepare)
    with pytest.raises(CommunicationError, match="the first trigger"):
        device_harness.run("daemon", tpx.start)

    assert puts_to(tpx_backend, "PathToAdd") == []


def test_when_empir_does_not_queue_the_folder_the_start_fails(
    device_harness, tpx_backend
):
    tpx, _poller = create_timepix(device_harness)
    tpx_backend.empir_follows = False

    device_harness.run("daemon", tpx.prepare)
    with pytest.raises(CommunicationError, match="EMPIR to queue"):
        device_harness.run("daemon", tpx.start)

    assert len(puts_to(tpx_backend, "PathToAdd")) == 1


@pytest.mark.parametrize("failure", ["trigger_arrives", "empir_follows"])
def test_a_failed_start_leaves_the_camera_idle_and_not_writing(
    device_harness, tpx_backend, failure
):
    tpx, _poller = create_timepix(device_harness)
    setattr(tpx_backend, failure, False)

    device_harness.run("daemon", tpx.prepare)
    with pytest.raises(CommunicationError):
        device_harness.run("daemon", tpx.start)

    assert acquire_puts(tpx_backend) == [1, 0]
    assert puts_to(tpx_backend, "WriteData") == [1, 0]


@pytest.mark.parametrize(
    "refused, write_data_puts",
    [("RawFilePath", [0]), ("WriteData", []), ("TSReady", [1, 0])],
)
def test_a_refused_prepare_put_fails_the_prepare_and_stops_writing(
    device_harness, tpx_backend, refused, write_data_puts
):
    tpx, _poller = create_timepix(device_harness)
    ioc_put = tpx_backend.put_pv_value

    def put(pvname, value, wait=False):
        if pvname == camera_pv(refused):
            raise CommunicationError("Put not supported")
        ioc_put(pvname, value, wait)

    tpx_backend.put_pv_value = put
    with pytest.raises(CommunicationError, match="Put not supported"):
        device_harness.run("daemon", tpx.prepare)

    assert puts_to(tpx_backend, "WriteData") == write_data_puts
    assert tpx_backend.values[camera_pv("WriteData")] == 0


@pytest.mark.parametrize(
    "parameter, record, readback",
    [
        ("threshold_fine", "CHIP0_Vth_fine", 100),
        ("threshold_coarse", "CHIP0_Vth_coarse", 7),
    ],
)
def test_thresholds_read_the_readback_and_write_the_setpoint(
    device_harness, tpx_backend, parameter, record, readback
):
    tpx, _poller = create_timepix(device_harness)

    assert getattr(tpx, parameter) == readback

    device_harness.run("daemon", setattr, tpx, parameter, 9)

    assert puts_to(tpx_backend, record) == [9]


@pytest.mark.parametrize(
    "parameter, record, value",
    [("min_photons", "EvFlit_PhMin", 2.0), ("min_psd", "EvFlit_PsdMin", 0.5)],
)
def test_the_empir_filters_read_and_write_the_same_record(
    device_harness, tpx_backend, parameter, record, value
):
    tpx, _poller = create_timepix(device_harness)

    assert getattr(tpx, parameter) == value

    device_harness.run("daemon", setattr, tpx, parameter, 0.7)

    assert puts_to(tpx_backend, record) == [0.7]
    assert getattr(tpx, parameter) == 0.7

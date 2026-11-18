"""Harness tests for the ORCA-Flash4 on the ESS ADOrca driver.

Choice lists are the ones the YMIR IOC (YMIR-Det1:cam1:) served on 2026-11-03.
"""

import pytest

from nicos.core import FINAL, InvalidValueError, status
from nicos.devices.generic import ManualSwitch
from nicos_ess.devices.epics.adcore import OrcaFlash4
from test.nicos_ess.test_devices.doubles.adcore_camera import (
    camera_pv,
    create_camera,
    run_count,
)

CHOICES = {
    "TriggerSource": ["Internal", "External", "Software", "Master pulse"],
    "TriggerActive": ["Edge", "Level", "Sync Readout"],
    "TriggerMode": ["Normal", "Start"],
    "TriggerPolarity": ["Negative", "Positive"],
    "TriggerConnector": ["Interface", "BNC"],
    "TriggerGlobalExposure": ["Delayed", "Global Reset"],
    "Binning": ["1x1", "2x2", "4x4"],
    "SensorCooler": ["Off", "On", "Max"],
}


def set_choice(backend, record, choice):
    backend.values[camera_pv(f"{record}-S")] = CHOICES[record].index(choice)
    backend.values[camera_pv(f"{record}-RB")] = CHOICES[record].index(choice)


@pytest.fixture
def orca_backend(camera_ioc):
    for record, choices in CHOICES.items():
        camera_ioc.value_choices[camera_pv(f"{record}-RB")] = choices
        set_choice(camera_ioc, record, choices[0])
    # The YMIR IOC was left in Edge mode with negative polarity.
    set_choice(camera_ioc, "TriggerSource", "External")
    set_choice(camera_ioc, "TriggerConnector", "BNC")
    camera_ioc.value_choices[camera_pv("CoolerStatus-R")] = [
        "Error",
        "Off",
        "Busy",
        "On",
    ]
    camera_ioc.values.update(
        {
            camera_pv("TriggerTimes-S"): 14,
            camera_pv("TriggerTimes-RB"): 14,
            camera_pv("Temperature-R"): -10.0,
            camera_pv("CoolerStatus-R"): 2,
            camera_pv("FrameRate-R"): 1.0,
        }
    )
    return camera_ioc


def create_orca(device_harness, **config):
    return create_camera(device_harness, OrcaFlash4, "orca", **config)


def written(backend):
    return {pv for pv, _value, _wait in backend.put_calls}


class TestExposure:
    @pytest.mark.parametrize("param", ["acquiretime", "acquireperiod"])
    def test_a_time_is_set_as_triggers(
        self, device_harness, orca_backend, caplog, param
    ):
        orca, _poller = create_orca(device_harness)
        assert getattr(orca, param) == pytest.approx(1.0)

        device_harness.run("daemon", setattr, orca, param, 2.5)

        assert orca_backend.values[camera_pv("TriggerTimes-S")] == 35
        # The exposure is set only as TriggerTimes. AcquireTime and
        # AcquirePeriod keep the values that the IOC already has.
        assert written(orca_backend) == {camera_pv("TriggerTimes-S")}
        assert "rounded" not in caplog.text  # 2.5 s is exactly 35 triggers

    def test_the_triggers_are_the_setting_and_time_follows(
        self, device_harness, orca_backend
    ):
        orca, _poller = create_orca(device_harness)

        device_harness.run("daemon", setattr, orca, "numtriggers", 7)
        assert orca_backend.values[camera_pv("TriggerTimes-S")] == 7
        orca_backend.values[camera_pv("TriggerTimes-RB")] = 7  # The IOC reads it back.

        assert orca.numtriggers == 7
        assert orca.acquiretime == orca.acquireperiod == pytest.approx(0.5)

    def test_the_trigger_rate_turns_triggers_into_seconds(
        self, device_harness, orca_backend
    ):
        orca, poller = create_orca(device_harness)
        orca_backend.emit_update(camera_pv("TriggerTimes-RB"), value=7)

        device_harness.run("daemon", setattr, orca, "triggerrate", 1.0)

        assert poller._cache.get(poller, "acquiretime") == pytest.approx(7.0)
        assert poller._cache.get(poller, "acquireperiod") == pytest.approx(7.0)
        assert orca.acquiretime == pytest.approx(7.0)

    def test_a_time_is_set_at_the_trigger_rate(self, device_harness, orca_backend):
        orca, _poller = create_orca(device_harness)

        device_harness.run("daemon", setattr, orca, "triggerrate", 1.0)
        device_harness.run("daemon", setattr, orca, "acquiretime", 3.0)

        assert orca_backend.values[camera_pv("TriggerTimes-S")] == 3

    def test_an_exposure_off_the_trigger_grid_is_rounded(
        self, device_harness, orca_backend, caplog
    ):
        orca, _poller = create_orca(device_harness)

        device_harness.run("daemon", setattr, orca, "acquiretime", 0.1)

        assert orca_backend.values[camera_pv("TriggerTimes-S")] == 1
        assert "rounded to 1 triggers, which is 0.07143 s" in caplog.text

    def test_less_than_one_trigger_is_refused(self, device_harness, orca_backend):
        orca, _poller = create_orca(device_harness)

        with pytest.raises(InvalidValueError, match="at least one trigger"):
            device_harness.run("daemon", setattr, orca, "acquiretime", 0.01)
        with pytest.raises(InvalidValueError, match="at least one trigger"):
            device_harness.run("daemon", setattr, orca, "numtriggers", 0)

        assert written(orca_backend) == set()


@pytest.mark.parametrize(
    "polarity, changed",
    [
        ("Positive", {"TriggerActive-S", "TriggerPolarity-S"}),
        ("Negative", {"TriggerActive-S"}),
    ],
)
def test_prepare_writes_only_what_differs_from_sync_readout(
    device_harness, orca_backend, polarity, changed
):
    orca, _poller = create_orca(device_harness, triggerpolarity=polarity)

    device_harness.run("daemon", orca.prepare)

    assert written(orca_backend) == {camera_pv(record) for record in changed}
    assert orca_backend.values[camera_pv("TriggerActive-S")] == CHOICES[
        "TriggerActive"
    ].index("Sync Readout")
    assert orca_backend.values[camera_pv("TriggerPolarity-S")] == CHOICES[
        "TriggerPolarity"
    ].index(polarity)


def test_binning_is_written_by_index(device_harness, orca_backend):
    orca, _poller = create_orca(device_harness)

    device_harness.run("daemon", setattr, orca, "binning", "4x4")

    assert orca_backend.values[camera_pv("Binning-S")] == 2


def create_orca_with_chiller(device_harness, chiller_state):
    chiller = device_harness.create_pair(
        ManualSwitch, name="chiller", shared={"states": ["OFF", "ON"]}
    )[0]
    device_harness.run("daemon", chiller.maw, chiller_state)
    return create_orca(device_harness, watercooler="chiller")


def test_cooling_is_refused_while_the_chiller_is_off(device_harness, orca_backend):
    orca, _poller = create_orca_with_chiller(device_harness, "OFF")

    with pytest.raises(InvalidValueError, match="chiller is off"):
        device_harness.run("daemon", setattr, orca, "cooling", "Max")

    assert camera_pv("SensorCooler-S") not in written(orca_backend)


@pytest.mark.parametrize(
    "chiller_state, cooling", [("ON", "Max"), ("OFF", "Off"), (None, "Max")]
)
def test_cooling_is_set_when_the_chiller_allows_it(
    device_harness, orca_backend, chiller_state, cooling
):
    if chiller_state is None:
        orca, _poller = create_orca(device_harness)
    else:
        orca, _poller = create_orca_with_chiller(device_harness, chiller_state)

    device_harness.run("daemon", setattr, orca, "cooling", cooling)

    assert orca_backend.values[camera_pv("SensorCooler-S")] == CHOICES[
        "SensorCooler"
    ].index(cooling)


def test_the_orca_counts_like_any_area_detector(device_harness, orca_backend):
    orca, _poller = create_orca(device_harness)

    run_count(device_harness, orca, orca_backend, frames=3, preset=3)

    assert device_harness.run("daemon", orca.status, 0)[0] == status.OK
    assert (device_harness.run("daemon", orca.readArray, FINAL) == 3).all()


def test_the_cache_shows_the_exposure_the_device_reads(device_harness, orca_backend):
    # The cached exposure comes from TriggerTimes and ignores AcquireTime. The
    # trigger settings are not parameters, so they leave no cache keys.
    orca, poller = create_orca(device_harness)

    orca_backend.emit_update(camera_pv("TriggerTimes-RB"), value=35)
    orca_backend.emit_update(camera_pv("AcquireTime_RBV"), value=0.1)
    orca_backend.emit_update(camera_pv("AcquirePeriod_RBV"), value=0.2)
    # The first choice of TriggerPolarity is Negative, which differs from the
    # configured polarity.
    for record in CHOICES:
        if record.startswith("Trigger"):
            orca_backend.emit_update(camera_pv(f"{record}-RB"), value=0)

    assert poller._cache.get(poller, "acquiretime") == pytest.approx(2.5)
    assert device_harness.run("daemon", lambda: orca.acquiretime) == pytest.approx(2.5)
    assert poller._cache.get(poller, "numtriggers") == 35
    assert poller._cache.get(poller, "acquireperiod") == pytest.approx(2.5)
    for record in (
        "TriggerSource",
        "TriggerMode",
        "TriggerActive",
        "TriggerGlobalExposure",
        "TriggerConnector",
    ):
        assert poller._cache.get(poller, record.lower()) is None
    assert poller._cache.get(poller, "triggerpolarity") != "Negative"
    assert device_harness.run("daemon", lambda: orca.triggerpolarity) == "Positive"

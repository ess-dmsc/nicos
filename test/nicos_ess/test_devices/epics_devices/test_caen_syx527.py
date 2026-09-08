import time
from types import SimpleNamespace

import pytest

from nicos.core import (
    ADMIN,
    GUEST,
    SIMULATION,
    SLAVE,
    AccessError,
    CanDisable,
    CommunicationError,
    ConfigurationError,
    LimitError,
    ModeError,
    status,
)
from nicos.devices.generic import ParamDevice, ReadonlyParamDevice
from nicos_ess.devices.epics.caen_syx527 import CaenSyx527ChannelGroup
from test.nicos_ess.loki.test_loki_detector_carriage import FakeLokiDetectorMotion

SOURCES = {
    "module01": "SIM:HVM-100:Ch00",
    "module02": "SIM:HVM-101:Ch01",
}

# Only the state bits are monitored; every fault bit is summarised by the
# IOC's -Status-Alarm record.
STATUS_BITS = {"ON": 0, "RU": 1, "RD": 2}

MONITORED_SUFFIXES = (
    "-VMon",
    "-V0Set-RB",
    "-IMon",
    "-I0Set-RB",
    "-Pw-RB",
    "-Status-Alarm",
    *(f"-Status-{record}" for record in STATUS_BITS),
)


@pytest.fixture
def power_supply_backend(fake_backend):
    for source in SOURCES.values():
        fake_backend.values[f"{source}-VMon"] = 0.22
        fake_backend.values[f"{source}-V0Set-RB"] = 800.0
        fake_backend.values[f"{source}-V0Set"] = 800.0
        fake_backend.values[f"{source}-IMon"] = 0.1
        fake_backend.values[f"{source}-I0Set-RB"] = 10.0
        fake_backend.values[f"{source}-I0Set"] = 10.0
        fake_backend.values[f"{source}-Pw"] = 0
        fake_backend.values[f"{source}-Pw-RB"] = 0
        for record in STATUS_BITS:
            fake_backend.values[f"{source}-Status-{record}"] = 0
        fake_backend.values[f"{source}-Status-Alarm"] = 0
        fake_backend.units[f"{source}-VMon"] = "V"
        fake_backend.units[f"{source}-V0Set-RB"] = "V"
        fake_backend.units[f"{source}-V0Set"] = "V"
        fake_backend.units[f"{source}-IMon"] = "uA"
        fake_backend.units[f"{source}-I0Set-RB"] = "uA"
        fake_backend.units[f"{source}-I0Set"] = "uA"
        fake_backend.limits[f"{source}-V0Set"] = (0.0, 3000.0)
        fake_backend.limits[f"{source}-I0Set"] = (0.0, 1000.0)
    return fake_backend


def create_group(device_harness, sources=SOURCES, name="power_group", **config):
    shared = {
        "sources": sources,
        "precision": 1.0,
        "monitor": True,
        "pva": True,
    }
    shared.update(config)
    return device_harness.create_pair(
        CaenSyx527ChannelGroup,
        name=name,
        shared=shared,
    )


def emit_snapshot(backend, sources=SOURCES):
    for source in sources.values():
        for suffix in MONITORED_SUFFIXES:
            backend.emit_update(f"{source}{suffix}")


def emit_status_word(backend, source, word):
    for record, bit in STATUS_BITS.items():
        backend.emit_update(f"{source}-Status-{record}", value=(word >> bit) & 1)


def emit_fault(backend, source, on=True):
    backend.emit_update(f"{source}-Status-Alarm", value=int(on))


def emit_powered(backend, source, on=True):
    backend.emit_update(f"{source}-Pw-RB", value=int(on))
    emit_status_word(backend, source, int(on))


def test_group_uses_live_readback_and_status_pvs_with_epics_units(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)

    assert len(power_supply_backend.subscriptions) == len(MONITORED_SUFFIXES) * len(
        SOURCES
    )
    subscribed_pvs = {
        subscription[0] for subscription in power_supply_backend.subscriptions
    }
    assert f"{SOURCES['module01']}-V0Set-RB" in subscribed_pvs
    assert f"{SOURCES['module01']}-I0Set-RB" in subscribed_pvs
    assert f"{SOURCES['module01']}-Pw-RB" in subscribed_pvs
    assert f"{SOURCES['module01']}-Status-ON" in subscribed_pvs
    assert f"{SOURCES['module01']}-Status-Alarm" in subscribed_pvs
    assert f"{SOURCES['module01']}-Status" not in subscribed_pvs
    # the individual fault bits are left to the IOC screens
    assert f"{SOURCES['module01']}-Status-OC" not in subscribed_pvs
    assert f"{SOURCES['module01']}-Status-UV" not in subscribed_pvs
    startup_pvs = set(power_supply_backend.connect_calls)
    assert f"{SOURCES['module01']}-VMon" in startup_pvs
    assert f"{SOURCES['module01']}-Pw-RB" not in startup_pvs
    assert f"{SOURCES['module01']}-Status-ON" not in startup_pvs
    assert daemon_device.unit == "V"
    assert daemon_device._getParamConfig("currents").unit == "uA"
    assert daemon_device._getParamConfig("current_limits").unit == "uA"


def test_initial_status_waits_for_complete_monitor_snapshot(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)

    assert daemon_device.status() == (
        status.UNKNOWN,
        f"waiting for EPICS data from {len(MONITORED_SUFFIXES) * len(SOURCES)} of "
        f"{len(MONITORED_SUFFIXES) * len(SOURCES)} PVs",
    )


def test_status_reports_how_many_pvs_are_still_missing(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    for source in SOURCES.values():
        for suffix in MONITORED_SUFFIXES[:-1]:
            power_supply_backend.emit_update(f"{source}{suffix}")

    total = len(MONITORED_SUFFIXES) * len(SOURCES)
    assert daemon_device.status() == (
        status.UNKNOWN,
        f"waiting for EPICS data from {len(SOURCES)} of {total} PVs",
    )


def test_group_rejects_mixed_current_units(device_harness, power_supply_backend):
    power_supply_backend.units[f"{SOURCES['module02']}-IMon"] = "A"

    with pytest.raises(ConfigurationError, match="same unit"):
        create_group(device_harness)


def test_group_rejects_mixed_voltage_units(device_harness, power_supply_backend):
    power_supply_backend.units[f"{SOURCES['module02']}-V0Set-RB"] = "kV"

    with pytest.raises(ConfigurationError, match="same unit"):
        create_group(device_harness)


def test_current_parameter_units_are_independent_per_instance(
    device_harness, power_supply_backend
):
    hv_group, _hv_poller = create_group(
        device_harness,
        {"hv": SOURCES["module01"]},
        name="hv_group",
    )
    power_supply_backend.units[f"{SOURCES['module02']}-IMon"] = "A"
    power_supply_backend.units[f"{SOURCES['module02']}-I0Set-RB"] = "A"
    power_supply_backend.units[f"{SOURCES['module02']}-I0Set"] = "A"
    lv_group, _lv_poller = create_group(
        device_harness,
        {"lv": SOURCES["module02"]},
        name="lv_group",
    )

    assert hv_group._getParamConfig("currents").unit == "uA"
    assert hv_group._getParamConfig("current_limits").unit == "uA"
    assert lv_group._getParamConfig("currents").unit == "A"
    assert lv_group._getParamConfig("current_limits").unit == "A"


@pytest.mark.parametrize(
    "sources",
    [
        {},
        {"module01": "SIM:HVM-100:Ch00", "module02": "SIM:HVM-100:Ch00"},
    ],
)
def test_group_rejects_empty_or_duplicate_sources(device_harness, sources):
    with pytest.raises(ConfigurationError):
        device_harness.create_daemon(CaenSyx527ChannelGroup, sources=sources)


def test_disabled_output_is_not_busy_when_voltage_differs_from_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    assert daemon_device.read() == (0.22, 0.22)
    assert daemon_device.target == (800.0, 800.0)
    assert daemon_device.status() == (status.DISABLED, "output disabled")


def test_off_threshold_waits_for_voltage_then_ignores_safe_ramp_down(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(
        device_harness, voltage_off_threshold=5.0
    )
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_update(f"{SOURCES['module01']}-VMon", value=-5.1)
    power_supply_backend.emit_update(f"{SOURCES['module01']}-Status-RD", value=1)

    assert daemon_device.status() == (
        status.BUSY,
        "waiting for output voltages to fall to 5 V or below",
    )

    power_supply_backend.emit_update(f"{SOURCES['module01']}-VMon", value=-5.0)

    assert daemon_device.status() == (status.DISABLED, "output disabled")


def test_enabled_output_is_busy_until_voltage_reaches_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)

    assert daemon_device.status() == (
        status.BUSY,
        "voltage readback has not reached target",
    )

    for source in SOURCES.values():
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)

    assert daemon_device.status() == (status.OK, "output enabled")


def test_current_changes_are_not_movement_but_current_alarms_affect_status(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)

    power_supply_backend.emit_update(f"{SOURCES['module01']}-IMon", value=0.5)
    assert daemon_device.status() == (status.OK, "output enabled")

    power_supply_backend.emit_update(
        f"{SOURCES['module01']}-IMon",
        severity=status.ERROR,
        message="leak current alarm",
    )
    assert daemon_device.status() == (
        status.ERROR,
        "leak current alarm",
    )


def test_daemon_startup_does_not_clobber_the_live_poller_status(
    device_harness, power_supply_backend
):
    config = {"sources": SOURCES, "precision": 1.0, "monitor": True, "pva": True}
    poller_device = device_harness.create_poller(
        CaenSyx527ChannelGroup, name="power_group", **config
    )
    emit_snapshot(power_supply_backend)
    assert poller_device.status() == (status.DISABLED, "output disabled")

    # A daemon restart re-creates the device while the poller keeps running.
    # It never subscribes, so it reads what the poller cached rather than
    # publishing a view of its own, and does so without going to the IOCs.
    power_supply_backend.get_calls.clear()
    daemon_device = device_harness.create_daemon(
        CaenSyx527ChannelGroup, name="power_group", **config
    )

    assert daemon_device.status() == (status.DISABLED, "output disabled")
    assert [
        call for call in power_supply_backend.get_calls if call[0] != "get_units"
    ] == []


def test_status_is_republished_only_when_it_changes(
    device_harness, power_supply_backend
):
    _daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    def status_writes():
        return len(
            poller_device._cache.history(
                poller_device._name, "status", 0, time.time() + 1
            )
        )

    before = status_writes()
    power_supply_backend.emit_update(f"{SOURCES['module01']}-VMon", value=0.23)
    assert status_writes() == before

    emit_fault(power_supply_backend, SOURCES["module01"])
    assert status_writes() == before + 1


def test_volatile_current_parameters_read_the_iocs(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()

    # No monitor update for this one: only a direct read can see it.
    power_supply_backend.values[f"{SOURCES['module01']}-IMon"] = 0.5

    assert daemon_device.currents == (0.5, 0.1)
    assert [call[1] for call in power_supply_backend.get_calls] == [
        f"{source}-IMon" for source in SOURCES.values()
    ]


def test_monitor_status_is_derived_from_the_shared_cache(
    device_harness, power_supply_backend
):
    _daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    assert poller_device._compute_status(None) == (status.DISABLED, "output disabled")

    poller_device._cache.put(
        poller_device._name,
        poller_device._epics.source_key("module01", "status_ramping_down"),
        1,
        time.time(),
    )

    assert poller_device._compute_status(None) == (
        status.BUSY,
        "waiting for outputs to disable",
    )


def test_daemon_and_poller_compute_the_same_status(
    device_harness, power_supply_backend
):
    daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()

    assert daemon_device._compute_status(None) == poller_device._compute_status(None)

    power_supply_backend.emit_update(f"{SOURCES['module02']}-Status-Alarm", value=1)
    assert daemon_device._compute_status(None) == poller_device._compute_status(None)
    assert power_supply_backend.get_calls == []


def test_explicit_daemon_poll_still_reads_hardware(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.values[f"{SOURCES['module01']}-Status-RD"] = 1
    polled_status, _value = device_harness.run_daemon(daemon_device.poll)

    assert polled_status == (
        status.BUSY,
        "waiting for outputs to disable",
    )
    assert device_harness.run_daemon(daemon_device.status) == (
        status.BUSY,
        "waiting for outputs to disable",
    )


def test_enable_polls_and_waits_for_power_readbacks(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()

    device_harness.run_daemon(daemon_device.enable)

    assert isinstance(daemon_device, CanDisable)
    assert daemon_device.status() == (status.BUSY, "waiting for outputs to enable")
    assert all(
        power_supply_backend.values[f"{source}-Pw"] == 1 for source in SOURCES.values()
    )
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)
    assert daemon_device.status() == (status.OK, "output enabled")


def test_poller_poll_can_refresh_monitor_derived_status(
    device_harness, power_supply_backend
):
    daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.values[f"{SOURCES['module01']}-Status-RD"] = 1
    device_harness.run_poller(poller_device.poll)

    assert device_harness.run_daemon(daemon_device.status) == (
        status.BUSY,
        "waiting for outputs to disable",
    )


def test_start_writes_one_voltage_setpoint_per_channel(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    daemon_device.start((100.0, 200.0))

    assert power_supply_backend.values[f"{SOURCES['module01']}-V0Set"] == 100.0
    assert power_supply_backend.values[f"{SOURCES['module02']}-V0Set"] == 200.0
    assert daemon_device.target == (100.0, 200.0)


def test_external_setpoint_readbacks_update_the_group_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_update(f"{SOURCES['module01']}-V0Set-RB", value=123.0)

    assert daemon_device.target == (123.0, 800.0)


def test_current_readbacks_and_limits_are_monitor_driven_parameters(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    assert daemon_device.currents == (0.1, 0.1)
    assert daemon_device.current_limits == (10.0, 10.0)

    power_supply_backend.emit_update(f"{SOURCES['module01']}-IMon", value=0.25)
    power_supply_backend.emit_update(f"{SOURCES['module02']}-I0Set-RB", value=20.0)

    assert daemon_device.currents == (0.25, 0.1)
    assert daemon_device.current_limits == (10.0, 20.0)


def test_setting_current_limits_writes_each_channel(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    daemon_device.current_limits = (100.0, 200.0)

    assert power_supply_backend.values[f"{SOURCES['module01']}-I0Set"] == 100.0
    assert power_supply_backend.values[f"{SOURCES['module02']}-I0Set"] == 200.0


def test_setting_current_limits_honours_epics_limits(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    puts_before = list(power_supply_backend.put_calls)

    with pytest.raises(LimitError, match="module02 limits"):
        daemon_device.current_limits = (100.0, 1001.0)

    assert power_supply_backend.put_calls == puts_before


def test_current_parameters_work_with_generic_param_devices(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    current_readback = device_harness.create_daemon(
        ReadonlyParamDevice,
        name="current_readback",
        device=daemon_device.name,
        parameter="currents",
    )
    current_limit = device_harness.create_daemon(
        ParamDevice,
        name="current_limit",
        device=daemon_device.name,
        parameter="current_limits",
    )

    assert current_readback.read() == (0.1, 0.1)
    assert current_readback.unit == "uA"
    assert current_limit.read() == (10.0, 10.0)
    assert current_limit.unit == "uA"

    current_limit.start((100.0, 200.0))
    assert power_supply_backend.values[f"{SOURCES['module01']}-I0Set"] == 100.0
    assert power_supply_backend.values[f"{SOURCES['module02']}-I0Set"] == 200.0


def test_fix_blocks_voltage_changes_but_not_enable_disable(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    device_harness.run_daemon(daemon_device.fix, "voltage settings locked")
    puts_before_start = list(power_supply_backend.put_calls)

    device_harness.run_daemon(daemon_device.start, (100.0, 200.0))
    device_harness.run_daemon(setattr, daemon_device, "current_limits", (100.0, 200.0))
    assert power_supply_backend.put_calls == puts_before_start

    device_harness.run_daemon(daemon_device.enable)
    assert all(
        power_supply_backend.values[f"{source}-Pw"] == 1 for source in SOURCES.values()
    )

    device_harness.run_daemon(daemon_device.release)
    device_harness.run_daemon(daemon_device.start, (100.0, 200.0))
    device_harness.run_daemon(setattr, daemon_device, "current_limits", (100.0, 200.0))
    assert power_supply_backend.values[f"{SOURCES['module01']}-V0Set"] == 100.0
    assert power_supply_backend.values[f"{SOURCES['module02']}-V0Set"] == 200.0
    assert power_supply_backend.values[f"{SOURCES['module01']}-I0Set"] == 100.0
    assert power_supply_backend.values[f"{SOURCES['module02']}-I0Set"] == 200.0


def test_fix_and_release_require_admin_and_fixed_can_be_configured_at_startup(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(
        device_harness,
        fixed="voltage settings locked at startup",
        fixedby=("setup", ADMIN),
    )
    emit_snapshot(power_supply_backend)

    assert daemon_device.fixed == "voltage settings locked at startup"
    assert daemon_device.fixedby == ("setup", ADMIN)

    with device_harness.activate(device_harness.DAEMON_ROLE) as daemon_session:
        daemon_session.executing_user = SimpleNamespace(name="guest", level=GUEST)
        with pytest.raises(AccessError):
            daemon_device.release()
        with pytest.raises(AccessError):
            daemon_device.fix("guest lock")

        daemon_session.executing_user = SimpleNamespace(name="admin", level=ADMIN)
        assert daemon_device.release()
        assert not daemon_device.fixed
        assert daemon_device.fix("admin lock")

    assert daemon_device.fixedby == ("admin", ADMIN)


def test_one_source_group_has_scalar_value_and_target(
    device_harness, power_supply_backend
):
    sources = {"monitor": SOURCES["module01"]}
    daemon_device, _poller_device = create_group(device_harness, sources)
    emit_snapshot(power_supply_backend, sources)

    assert daemon_device.read() == 0.22
    assert daemon_device.target == 800.0
    assert daemon_device.currents == 0.1
    assert daemon_device.current_limits == 10.0

    daemon_device.start(500.0)
    daemon_device.current_limits = 50.0
    assert power_supply_backend.values[f"{SOURCES['module01']}-V0Set"] == 500.0
    assert power_supply_backend.values[f"{SOURCES['module01']}-I0Set"] == 50.0


def test_status_update_recomputes_from_monitors_without_direct_epics_gets(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()

    emit_fault(power_supply_backend, SOURCES["module02"])

    assert power_supply_backend.get_calls == []
    assert daemon_device.status() == (
        status.ERROR,
        "module02: alarm",
    )


def test_alarm_summary_is_reported_per_channel(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    for source in SOURCES.values():
        emit_fault(power_supply_backend, source)

    assert daemon_device.status() == (
        status.ERROR,
        "module01: alarm; module02: alarm",
    )

    emit_fault(power_supply_backend, SOURCES["module01"], on=False)

    assert daemon_device.status() == (
        status.ERROR,
        "module02: alarm",
    )


def test_value_info_names_each_channel(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)

    assert [value.name for value in daemon_device.valueInfo()] == [
        f"{daemon_device.name}.{source_id}" for source_id in SOURCES
    ]
    assert all(value.unit == "V" for value in daemon_device.valueInfo())


def test_reconnect_reuses_the_last_complete_monitor_snapshot(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_connection(f"{SOURCES['module02']}-Status-Alarm", False)
    assert daemon_device.status() == (
        status.UNKNOWN,
        "lost connection to EPICS",
    )

    power_supply_backend.emit_connection(f"{SOURCES['module02']}-Status-Alarm", True)
    assert daemon_device.status() == (status.DISABLED, "output disabled")

    power_supply_backend.emit_update(f"{SOURCES['module02']}-Status-Alarm")
    assert daemon_device.status() == (status.DISABLED, "output disabled")


@pytest.mark.parametrize("monitor", [True, False])
def test_start_waits_for_all_setpoint_readbacks(
    device_harness, power_supply_backend, monitor
):
    daemon_device, _poller_device = create_group(device_harness, monitor=monitor)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)

    device_harness.run_daemon(daemon_device.start, (1000.0, 1100.0))
    # CAEN input records can still contain the previous setpoints after a put.
    for source in SOURCES.values():
        power_supply_backend.emit_update(f"{source}-V0Set-RB")
    assert daemon_device.target == (1000.0, 1100.0)
    assert not device_harness.run_daemon(daemon_device.isCompleted)

    for source, value in zip(SOURCES.values(), (1000.0, 1100.0)):
        power_supply_backend.emit_update(f"{source}-VMon", value=value)
    first, second = SOURCES.values()
    power_supply_backend.emit_update(f"{first}-V0Set-RB", value=1000.0)
    assert daemon_device.target == (1000.0, 1100.0)
    assert not device_harness.run_daemon(daemon_device.isCompleted)

    power_supply_backend.emit_update(f"{second}-V0Set-RB", value=1100.0)
    assert device_harness.run_daemon(daemon_device.isCompleted)
    assert daemon_device.target == (1000.0, 1100.0)

    # Once acknowledged, subsequent external changes can update the target.
    power_supply_backend.emit_update(f"{second}-V0Set-RB", value=1200.0)
    assert daemon_device.status(0)[0] == status.BUSY
    assert daemon_device.target == (1000.0, 1200.0)


def test_fresh_completion_does_not_let_older_monitors_restore_the_old_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)
    device_harness.run_daemon(daemon_device.start, (1000.0, 1000.0))

    for source in SOURCES.values():
        power_supply_backend.values[f"{source}-V0Set-RB"] = 1000.0
        power_supply_backend.values[f"{source}-VMon"] = 1000.0
    assert device_harness.run_daemon(daemon_device.isCompleted)

    # The IOC has acknowledged the move, but the monitor cache still lags.
    power_supply_backend.emit_update(f"{SOURCES['module01']}-IMon", value=0.2)
    assert daemon_device.target == (1000.0, 1000.0)
    assert daemon_device.status()[0] == status.BUSY
    emit_snapshot(power_supply_backend)
    assert daemon_device.status() == (status.OK, "output enabled")


def test_ramping_warning_does_not_complete_movement(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-Status-RU", value=1)
    pv = f"{SOURCES['module01']}-IMon"
    power_supply_backend.alarms[pv] = status.WARN, "minor current alarm"
    power_supply_backend.emit_update(
        pv, severity=status.WARN, message="minor current alarm"
    )

    assert daemon_device.status() == (
        status.BUSY,
        "2 of 2 outputs ramping",
    )
    assert not device_harness.run_daemon(daemon_device.isCompleted)


@pytest.mark.parametrize(
    "alarm, expected, movement_allowed",
    [
        (status.WARN, (status.DISABLED, "output disabled"), True),
        (status.ERROR, (status.ERROR, "current alarm"), False),
        (status.UNKNOWN, (status.UNKNOWN, "current alarm"), False),
    ],
)
def test_disabled_supply_alarms_and_detector_movement(
    device_harness, power_supply_backend, alarm, expected, movement_allowed
):
    daemon_device, _poller_device = create_group(
        device_harness, voltage_off_threshold=5.0
    )
    motor = create_detector_motor(device_harness, daemon_device)
    emit_snapshot(power_supply_backend)
    pv = f"{SOURCES['module01']}-IMon"
    power_supply_backend.alarms[pv] = alarm, "current alarm"
    power_supply_backend.emit_update(pv, severity=alarm, message="current alarm")
    assert daemon_device.status() == expected
    assert device_harness.run_daemon(motor.isAllowed, 20)[0] == movement_allowed
    if movement_allowed:
        device_harness.run_daemon(motor.start, 20)
        assert motor.target == 20
    else:
        with pytest.raises(LimitError, match="current alarm"):
            device_harness.run_daemon(motor.start, 20)


def test_initial_updates_publish_all_group_values(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)
    assert daemon_device.target == (800.0, 800.0)
    assert daemon_device.read() == (0.22, 0.22)
    for source in SOURCES.values():
        power_supply_backend.values[f"{source}-V0Set-RB"] = 900.0
        power_supply_backend.values[f"{source}-VMon"] = 0.5
    power_supply_backend.get_calls.clear()
    # All value PVs arrive before the final status bit in this snapshot.
    emit_snapshot(power_supply_backend)
    assert daemon_device.read() == (0.5, 0.5)
    assert daemon_device.target == (900.0, 900.0)
    assert daemon_device.status() == (status.DISABLED, "output disabled")
    assert power_supply_backend.get_calls == []


def test_ramp_down_monitor_callback_does_not_read_the_ioc(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(
        device_harness, voltage_off_threshold=5.0
    )
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()
    power_supply_backend.emit_update(f"{SOURCES['module01']}-VMon", value=50.0)
    assert daemon_device.status() == (
        status.BUSY,
        "waiting for output voltages to fall to 5 V or below",
    )
    assert power_supply_backend.get_calls == []


def test_without_monitors_status_reads_the_ioc(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness, monitor=False)
    assert daemon_device.status() == (status.DISABLED, "output disabled")
    device_harness.run_daemon(daemon_device.enable)
    assert daemon_device.status() == (status.BUSY, "waiting for outputs to enable")


@pytest.mark.parametrize("maxage", [None, 60, 0])
def test_read_honours_maxage(device_harness, power_supply_backend, maxage):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        power_supply_backend.values[f"{source}-VMon"] = 2.0
    expected = (2.0, 2.0) if maxage == 0 else (0.22, 0.22)
    assert daemon_device.read(maxage) == expected


@pytest.mark.parametrize(
    "sources, target", [(SOURCES, (100.0, 200.0)), ({"one": "SIM:ONE"}, 100.0)]
)
def test_simulated_commands_do_not_access_epics(
    device_harness, fake_backend, sources, target
):
    device = device_harness.create_daemon(
        CaenSyx527ChannelGroup, mode=SIMULATION, sources=sources, pva=True
    )
    device_harness.run_daemon(device.start, target)
    device_harness.run_daemon(device.enable)
    device_harness.run_daemon(device.disable)
    assert device.read() == target
    assert device.target == target
    assert fake_backend.connect_calls == []
    assert fake_backend.get_calls == []
    assert fake_backend.put_calls == []


@pytest.mark.parametrize("method", ["enable", "disable"])
def test_power_commands_honour_slave_mode(device_harness, power_supply_backend, method):
    device, _ = create_group(device_harness, mode=SLAVE)
    with pytest.raises(ModeError):
        device_harness.run_daemon(getattr(device, method))
    assert power_supply_backend.put_calls == []


@pytest.mark.parametrize("method", ["enable", "disable"])
def test_power_commands_honour_access_requirements(
    device_harness, power_supply_backend, method
):
    device, _ = create_group(device_harness, requires={"level": ADMIN})
    with device_harness.activate(device_harness.DAEMON_ROLE) as active_session:
        active_session.executing_user = SimpleNamespace(name="guest", level=GUEST)
        with pytest.raises(AccessError):
            getattr(device, method)()
    assert power_supply_backend.put_calls == []


def create_detector_motor(device_harness, supply, *, mode=None):
    return device_harness.create_daemon(
        FakeLokiDetectorMotion,
        name="detector_motor",
        power_supply=supply.name,
        motorpv="SIM:MOTOR",
        abslimits=(-100, 100),
        userlimits=(-100, 100),
        **({"mode": mode} if mode is not None else {}),
    )


@pytest.mark.parametrize("voltage, powered", [(50.0, 0), (0.22, 1)])
def test_detector_interlock_rechecks_hardware_when_monitors_lag(
    device_harness, power_supply_backend, voltage, powered
):
    supply, _ = create_group(device_harness, voltage_off_threshold=5.0)
    motor = create_detector_motor(device_harness, supply)
    emit_snapshot(power_supply_backend)
    assert supply.status() == (status.DISABLED, "output disabled")

    first = SOURCES["module01"]
    power_supply_backend.values[f"{first}-VMon"] = voltage
    power_supply_backend.values[f"{first}-Pw-RB"] = powered
    power_supply_backend.values[f"{first}-Status-ON"] = powered
    assert not device_harness.run_daemon(motor.isAllowed, 20)[0]
    with pytest.raises(LimitError):
        device_harness.run_daemon(motor.start, 20)


def test_pending_enable_blocks_detector_before_power_readbacks_update(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness, voltage_off_threshold=5.0)
    motor = create_detector_motor(device_harness, supply)
    emit_snapshot(power_supply_backend)
    assert device_harness.run_daemon(motor.isAllowed, 20)[0]

    device_harness.run_daemon(supply.enable)
    assert supply.status() == (status.BUSY, "waiting for outputs to enable")
    # An unrelated monitor still sees all power readbacks as off.
    power_supply_backend.emit_update(f"{SOURCES['module01']}-IMon", value=0.2)
    assert supply.status() == (status.BUSY, "waiting for outputs to enable")
    with pytest.raises(LimitError, match="waiting for outputs to enable"):
        device_harness.run_daemon(motor.start, 20)

    device_harness.run_daemon(supply.disable)
    assert device_harness.run_daemon(motor.isAllowed, 20)[0]


def test_detector_can_move_in_simulation_without_epics(device_harness, fake_backend):
    supply = device_harness.create_daemon(
        CaenSyx527ChannelGroup, mode=SIMULATION, sources=SOURCES, pva=True
    )
    motor = create_detector_motor(device_harness, supply, mode=SIMULATION)
    device_harness.run_daemon(motor.start, 20)
    assert motor.read() == 20
    assert fake_backend.get_calls == []
    assert fake_backend.put_calls == []


def test_pending_target_survives_daemon_restart(device_harness, power_supply_backend):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)
    device_harness.run_daemon(supply.start, (1000.0, 1100.0))
    device_harness.run_daemon(supply.shutdown)
    restarted = device_harness.create_daemon(
        CaenSyx527ChannelGroup,
        name=supply.name,
        sources=SOURCES,
        precision=1.0,
        pva=True,
    )
    assert restarted.target == (1000.0, 1100.0)
    assert not device_harness.run_daemon(restarted.isCompleted)


def test_current_limit_write_reads_the_previous_value_once(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness)
    power_supply_backend.get_calls.clear()
    supply.current_limits = (100.0, 200.0)
    reads = [
        call[1] for call in power_supply_backend.get_calls if call[0] == "get_pv_value"
    ]
    assert reads == [f"{source}-I0Set-RB" for source in SOURCES.values()]


def test_single_channel_value_info_uses_device_name(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness, sources={"one": SOURCES["module01"]})
    assert [value.name for value in supply.valueInfo()] == [supply.name]


def test_fresh_status_batches_values_and_alarms_once(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    pv = f"{SOURCES['module02']}-IMon"
    power_supply_backend.alarms[pv] = status.ERROR, "current alarm"
    power_supply_backend.get_calls.clear()

    assert supply.status(0) == (status.ERROR, "current alarm")
    # Transport calls are the regression: one batch, no second alarm pass.
    assert power_supply_backend.get_calls == [
        (
            "get_pv_readings",
            {
                f"{source}{suffix}": False
                for source in SOURCES.values()
                for suffix in MONITORED_SUFFIXES
            },
        )
    ]


@pytest.mark.parametrize("maxage", [None, 60, 0])
def test_status_honours_maxage_for_values_and_alarms(
    device_harness, power_supply_backend, maxage
):
    supply, _ = create_group(device_harness, voltage_off_threshold=5.0)
    emit_snapshot(power_supply_backend)
    power_supply_backend.values[f"{SOURCES['module01']}-VMon"] = 50.0
    power_supply_backend.alarms[f"{SOURCES['module02']}-IMon"] = (
        status.ERROR,
        "current alarm",
    )

    expected = (
        (
            status.ERROR,
            "current alarm",
        )
        if maxage == 0
        else (status.DISABLED, "output disabled")
    )
    assert supply.status(maxage) == expected


def test_positive_maxage_batches_only_expired_readings(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness, voltage_off_threshold=5.0)
    emit_snapshot(power_supply_backend)
    old = time.time() - 120
    for key, value in (
        ("status", (status.DISABLED, "output disabled")),
        ("module01/voltage", 0.22),
        ("module02/current/_alarm_status", (status.OK, "")),
    ):
        supply._cache.put(supply.name, key, value, old)
    voltage_pv = f"{SOURCES['module01']}-VMon"
    current_pv = f"{SOURCES['module02']}-IMon"
    power_supply_backend.values[voltage_pv] = 50.0
    power_supply_backend.alarms[current_pv] = status.ERROR, "current alarm"
    power_supply_backend.get_calls.clear()

    assert supply.status(60) == (
        status.ERROR,
        "current alarm",
    )
    assert power_supply_backend.get_calls == [
        ("get_pv_readings", {voltage_pv: False, current_pv: False})
    ]


@pytest.mark.parametrize("key", ["module01/voltage", "module01/voltage/_alarm_status"])
def test_invalidated_monitor_data_does_not_trigger_network_reads(
    device_harness, power_supply_backend, key
):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    supply._cache.invalidate(supply.name, key)
    power_supply_backend.get_calls.clear()

    power_supply_backend.emit_update(f"{SOURCES['module02']}-IMon", value=0.2)

    assert supply.status() == (
        status.UNKNOWN,
        f"waiting for EPICS data from 1 of {len(SOURCES) * len(MONITORED_SUFFIXES)} PVs",
    )
    assert power_supply_backend.get_calls == []
    power_supply_backend.emit_update(f"{SOURCES['module01']}-VMon")
    assert supply.status() == (status.DISABLED, "output disabled")


def test_status_without_monitors_ignores_existing_cached_readings(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    device_harness.run_daemon(supply.shutdown)
    supply = device_harness.create_daemon(
        CaenSyx527ChannelGroup,
        name=supply.name,
        sources=SOURCES,
        monitor=False,
        pva=True,
    )
    power_supply_backend.values[f"{SOURCES['module01']}-Status-Alarm"] = 1
    supply._cache.invalidate(supply.name, "status")

    assert supply.status() == (status.ERROR, "module01: alarm")


def test_fresh_status_reports_disconnected_backend(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.disconnect_backend()

    assert supply.status(0) == (status.UNKNOWN, "lost connection to EPICS")


def test_partial_voltage_write_keeps_the_target_until_successful_retry(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        emit_powered(power_supply_backend, source)
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)
    first, second = SOURCES.values()
    power_supply_backend.put_errors[f"{second}-V0Set"] = TimeoutError("write failed")

    with pytest.raises(CommunicationError, match="write failed"):
        device_harness.run_daemon(supply.start, (1000.0, 1100.0))

    assert power_supply_backend.values[f"{first}-V0Set"] == 1000.0
    assert power_supply_backend.values[f"{second}-V0Set"] == 800.0
    power_supply_backend.emit_update(f"{first}-V0Set-RB", value=1000.0)
    power_supply_backend.emit_update(f"{first}-VMon", value=1000.0)
    assert supply.target == (1000.0, 1100.0)
    assert supply.status(0) == (status.BUSY, "waiting for voltage setpoints to update")
    assert not device_harness.run_daemon(supply.isCompleted)

    power_supply_backend.put_errors.clear()
    device_harness.run_daemon(supply.start, (1000.0, 1100.0))
    power_supply_backend.emit_update(f"{second}-V0Set-RB", value=1100.0)
    power_supply_backend.emit_update(f"{second}-VMon", value=1100.0)
    assert device_harness.run_daemon(supply.isCompleted)


def test_partial_enable_keeps_detector_blocked_until_explicit_disable(
    device_harness, power_supply_backend
):
    supply, _ = create_group(device_harness, voltage_off_threshold=5.0)
    motor = create_detector_motor(device_harness, supply)
    emit_snapshot(power_supply_backend)
    first, second = SOURCES.values()
    power_supply_backend.put_errors[f"{second}-Pw"] = TimeoutError("write failed")

    with pytest.raises(CommunicationError, match="write failed"):
        device_harness.run_daemon(supply.enable)

    assert power_supply_backend.values[f"{first}-Pw"] == 1
    assert power_supply_backend.values[f"{second}-Pw"] == 0
    assert supply.status(0) == (status.BUSY, "waiting for outputs to enable")
    emit_powered(power_supply_backend, first)
    with pytest.raises(LimitError, match="waiting for outputs to enable"):
        device_harness.run_daemon(motor.start, 20)

    power_supply_backend.put_errors.clear()
    device_harness.run_daemon(supply.disable)
    emit_powered(power_supply_backend, first, on=False)
    assert supply.status(0) == (status.DISABLED, "output disabled")
    assert device_harness.run_daemon(motor.isAllowed, 20)[0]

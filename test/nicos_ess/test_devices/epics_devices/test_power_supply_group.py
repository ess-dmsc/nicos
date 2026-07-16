import time
from types import SimpleNamespace

import pytest

from nicos.core import ADMIN, GUEST, AccessError, ConfigurationError, LimitError, status
from nicos.devices.generic import ParamDevice, ReadonlyParamDevice
from nicos_ess.devices.epics.power_supply_group import PowerSupplyGroup

SOURCES = {
    "module01": "SIM:HVM-100:Ch00",
    "module02": "SIM:HVM-101:Ch01",
}


@pytest.fixture
def power_supply_backend(fake_backend):
    for source in SOURCES.values():
        fake_backend.values[f"{source}-VMon"] = 0.22
        fake_backend.values[f"{source}-V0Set"] = 800.0
        fake_backend.values[f"{source}-IMon"] = 0.1
        fake_backend.values[f"{source}-I0Set"] = 10.0
        fake_backend.values[f"{source}-Pw"] = 0
        fake_backend.values[f"{source}-Status"] = 0
        fake_backend.units[f"{source}-VMon"] = "V"
        fake_backend.units[f"{source}-IMon"] = "uA"
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
        PowerSupplyGroup,
        name=name,
        shared=shared,
    )


def emit_snapshot(backend, sources=SOURCES):
    for source in sources.values():
        backend.emit_update(f"{source}-VMon")
        backend.emit_update(f"{source}-V0Set")
        backend.emit_update(f"{source}-IMon")
        backend.emit_update(f"{source}-I0Set")
        backend.emit_update(f"{source}-Status")


def test_group_uses_five_monitors_per_source_and_epics_units(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)

    assert len(power_supply_backend.subscriptions) == 5 * len(SOURCES)
    assert daemon_device.unit == "V"
    assert daemon_device._getParamConfig("currents").unit == "uA"
    assert daemon_device._getParamConfig("current_limits").unit == "uA"


def test_group_rejects_mixed_current_units(device_harness, power_supply_backend):
    power_supply_backend.units[f"{SOURCES['module02']}-IMon"] = "A"

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
        device_harness.create_daemon(PowerSupplyGroup, sources=sources)


def test_disabled_output_is_not_busy_when_voltage_differs_from_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    assert daemon_device.read() == (0.22, 0.22)
    assert daemon_device.target == (800.0, 800.0)
    assert daemon_device.status() == (status.DISABLED, "output disabled")


def test_enabled_output_is_busy_until_voltage_reaches_target(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    for source in SOURCES.values():
        power_supply_backend.emit_update(f"{source}-Status", value=1)

    assert daemon_device.status() == (
        status.BUSY,
        "voltage readback has not reached target",
    )

    for source in SOURCES.values():
        power_supply_backend.emit_update(f"{source}-VMon", value=800.0)

    assert daemon_device.status() == (status.OK, "output enabled")


def test_partial_output_is_warn_not_busy(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_update(f"{SOURCES['module02']}-Status", value=1)

    assert daemon_device.status() == (status.WARN, "1 of 2 outputs enabled")


def test_current_changes_are_not_movement_but_current_alarms_affect_status(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    for source in SOURCES.values():
        power_supply_backend.emit_update(f"{source}-Status", value=1)
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
        "output enabled; leak current alarm",
    )


def test_cached_status_uses_the_atomic_monitor_snapshot(
    device_harness, power_supply_backend
):
    _daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    poller_device._cache.put(
        poller_device._name,
        poller_device._epics.source_key("module01", "status_word"),
        1 << 2,
        time.time(),
    )

    assert poller_device._status_words["module01"] == 0
    assert poller_device._compute_status(None) == (
        status.DISABLED,
        "output disabled",
    )


def test_explicit_daemon_poll_still_reads_hardware(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.values[f"{SOURCES['module01']}-Status"] = 1 << 2
    polled_status, _value = device_harness.run_daemon(daemon_device.poll)

    assert polled_status == (
        status.DISABLED,
        "output disabled; 1 channels ramping",
    )
    assert device_harness.run_daemon(daemon_device.status) == (
        status.DISABLED,
        "output disabled; 1 channels ramping",
    )


def test_enable_relies_on_monitor_updates_when_polling_is_disabled(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)
    power_supply_backend.get_calls.clear()

    device_harness.run_daemon(daemon_device.enable)

    assert power_supply_backend.get_calls == []
    assert all(
        power_supply_backend.values[f"{source}-Pw"] == 1
        for source in SOURCES.values()
    )


def test_poller_poll_can_refresh_monitor_derived_status(
    device_harness, power_supply_backend
):
    daemon_device, poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.values[f"{SOURCES['module01']}-Status"] = 1 << 2
    device_harness.run_poller(poller_device.poll)

    assert device_harness.run_daemon(daemon_device.status) == (
        status.DISABLED,
        "output disabled; 1 channels ramping",
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


def test_current_readbacks_and_limits_are_monitor_driven_parameters(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    assert daemon_device.currents == (0.1, 0.1)
    assert daemon_device.current_limits == (10.0, 10.0)

    power_supply_backend.emit_update(f"{SOURCES['module01']}-IMon", value=0.25)
    power_supply_backend.emit_update(f"{SOURCES['module02']}-I0Set", value=20.0)

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


def test_packed_fault_is_reported_with_its_channel(
    device_harness, power_supply_backend
):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_update(f"{SOURCES['module02']}-Status", value=1 << 3)

    assert daemon_device.status() == (
        status.ERROR,
        "output disabled; module02: over current",
    )


def test_value_info_names_each_channel(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)

    assert [value.name for value in daemon_device.valueInfo()] == list(SOURCES)
    assert all(value.unit == "V" for value in daemon_device.valueInfo())


def test_reconnect_waits_for_fresh_channel_data(device_harness, power_supply_backend):
    daemon_device, _poller_device = create_group(device_harness)
    emit_snapshot(power_supply_backend)

    power_supply_backend.emit_connection(f"{SOURCES['module02']}-Status", False)
    assert daemon_device.status() == (
        status.UNKNOWN,
        "lost connection to EPICS",
    )

    power_supply_backend.emit_connection(f"{SOURCES['module02']}-Status", True)
    assert daemon_device.status() == (
        status.UNKNOWN,
        "waiting for EPICS channel data",
    )

    power_supply_backend.emit_update(f"{SOURCES['module02']}-Status")
    assert daemon_device.status() == (status.DISABLED, "output disabled")

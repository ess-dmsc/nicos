from dataclasses import FrozenInstanceError

import pytest

from nicos.core import (
    CommunicationError,
    ConfigurationError,
    Param,
    Readable,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    ChannelUpdate,
    ConnectionUpdate,
    EpicsChannelComponent,
    EpicsChannelInfo,
    EpicsChannelKind,
    EpicsDeviceBase,
    EpicsEnumParam,
    command_channel,
    enum_command_channel,
    enum_readback_channel,
    enum_setpoint_channel,
    readback_channel,
    resolve_channel_pv_names,
    setpoint_channel,
    status_channel,
)
from nicos_ess.devices.epics.pva.epics_multisource import (
    EpicsMultiSourceBase,
    EpicsMultiSourceComponent,
)
from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    FakeEpicsBackend,
)


class StubLog:
    def __init__(self):
        self.messages = []

    def _record(self, level, msg, *args, **kwargs):
        del kwargs
        self.messages.append((level, msg % args if args else msg))

    def debug(self, msg, *args, **kwargs):
        self._record("debug", msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._record("info", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._record("warning", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._record("error", msg, *args, **kwargs)


EPICS_CHANNELS = {
    "value": readback_channel(".RBV", cache_key="value", primary=True),
    "target": setpoint_channel(".VAL", cache_key="target"),
    "moving": status_channel(".MOVN"),
    "speed": readback_channel(".VELO"),
    "label": readback_channel(".DESC", as_string=True),
}

PV_NAMES = {
    "value": "SIM:M1.RBV",
    "target": "SIM:M1.VAL",
    "moving": "SIM:M1.MOVN",
    "speed": "SIM:M1.VELO",
    "label": "SIM:M1.DESC",
}


class TestEpicsChannelInfo:
    def test_defaults_and_frozen_fields(self):
        info = EpicsChannelInfo("value", ".RBV", EpicsChannelKind.READBACK)
        assert info.kind == EpicsChannelKind.READBACK
        assert info.as_string is False
        assert info.pv_prefix_attr is None
        assert info.pv_name_attr is None
        assert info.subscribe is True
        assert info.refresh_status_on_update is False

        try:
            info.cache_key = "other"
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("EpicsChannelInfo must be immutable")

    def test_rejects_complete_pv_attr_with_suffix(self):
        with pytest.raises(ValueError, match="complete PV"):
            readback_channel(".RBV", pv_name_attr="readpv")

    def test_rejects_complete_pv_attr_with_prefix_attr(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            readback_channel("", pv_name_attr="readpv", pv_prefix_attr="motorpv")

    def test_enum_channels_force_string_readback_and_are_immutable(self):
        info = readback_channel(".VAL", is_enum=True)
        assert info.as_string is True
        assert info.is_enum is True

        with pytest.raises(FrozenInstanceError):
            info.is_enum = False


def make_component(epics_channels=None, pv_names_by_channel=None):
    backend = FakeEpicsBackend()
    component = EpicsChannelComponent(
        EPICS_CHANNELS if epics_channels is None else epics_channels,
        PV_NAMES if pv_names_by_channel is None else pv_names_by_channel,
        wrapper=backend,
    )
    return component, backend


class DynamicEnumProbe(EpicsDeviceBase, Readable):
    parameters = {
        "pv_root": Param("PV root", type=str, mandatory=True, userparam=False),
        "heater_range": Param(
            "EPICS enum backed range",
            type=EpicsEnumParam("range"),
            settable=True,
            volatile=True,
        ),
    }

    _default_pv_prefix_attr = "pv_root"
    _epics_channels = {
        "range": enum_readback_channel("RANGE"),
        "set_range": enum_command_channel("RANGE_S"),
    }

    def doRead(self, maxage=0):
        return ""

    def doReadHeater_Range(self):
        return self._read_channel_cached("range")

    def doWriteHeater_Range(self, value):
        self._epics.put_channel_value("set_range", value)
        return value


def prepare_dynamic_enum_backend(backend):
    backend.value_choices["SIM:RANGE"] = ["Off", "Low", "High"]
    backend.value_choices["SIM:RANGE_S"] = ["Off", "Low", "High"]
    backend.values["SIM:RANGE"] = 0
    backend.values["SIM:RANGE_S"] = "Off"


class TestErrorTranslation:
    def test_get_translates_wrapper_timeout_to_communication_error(self):
        component, backend = make_component()
        component.connect()
        backend.disconnect_backend()

        with pytest.raises(CommunicationError):
            component.get_channel_value("value")

    def test_put_translates_wrapper_timeout_to_communication_error(self):
        component, backend = make_component()
        component.connect()
        backend.disconnect_backend()

        with pytest.raises(CommunicationError):
            component.put_channel_value("target", 1)

    def test_empty_wrapper_timeout_uses_default_message(self):
        class EmptyTimeoutBackend(FakeEpicsBackend):
            def get_pv_value(self, pvname, as_string=False):
                raise TimeoutError("")

        backend = EmptyTimeoutBackend()
        component = EpicsChannelComponent(EPICS_CHANNELS, PV_NAMES, wrapper=backend)
        component.connect()

        with pytest.raises(CommunicationError) as excinfo:
            component.get_channel_value("value")

        assert str(excinfo.value) == "error reading PV SIM:M1.RBV: timed out"


class TestPvResolution:
    def test_pv_name_for_is_a_lookup(self):
        component, _ = make_component()
        assert component.pv_name_for("value") == "SIM:M1.RBV"
        assert component.pv_name_for("unknown_channel") is None

    def test_resolve_channel_pv_names_supports_mixed_roots(self):
        class Device:
            detectorpv = "DET:"
            imagepv = "IMG:"
            vacpv = "VAC:PRESS"
            directpv = "DIRECT:PV"

        channels = {
            "state": status_channel("State"),
            "image": readback_channel("ArrayData", pv_prefix_attr="imagepv"),
            "vacuum": status_channel("", pv_prefix_attr="vacpv"),
            "direct": readback_channel("", pv_name_attr="directpv"),
            "unset_optional": readback_channel(
                "", pv_name_attr="missingpv", allow_missing_pv=True
            ),
        }

        assert resolve_channel_pv_names(Device(), channels, "detectorpv") == {
            "state": "DET:State",
            "image": "IMG:ArrayData",
            "vacuum": "VAC:PRESS",
            "direct": "DIRECT:PV",
            "unset_optional": None,
        }

    def test_resolve_channel_pv_names_rejects_unresolved_required_channel(self):
        class Device:
            name = "probe"

        channels = {
            "value": readback_channel(".RBV"),
        }

        with pytest.raises(ConfigurationError):
            resolve_channel_pv_names(Device(), channels, "motorpv")

    def test_cache_key_for_prefers_channel_info(self):
        component, _ = make_component()
        assert component.cache_key_for("value") == "value"
        assert component.cache_key_for("moving") == "moving"
        assert component.cache_key_for("not_a_channel") == "not_a_channel"

    def test_cache_key_for_none_disables_caching(self):
        channels = dict(
            EPICS_CHANNELS,
            target=setpoint_channel(".VAL", cache_key=None),
        )
        component, _ = make_component(epics_channels=channels)
        assert component.cache_key_for("target") is None

    def test_pvs_to_connect_skips_missing_and_deduplicates(self):
        pv_names_by_channel = dict(PV_NAMES, label=None, speed="SIM:M1.RBV")
        component, _ = make_component(pv_names_by_channel=pv_names_by_channel)
        pvs = component.pvs_to_connect()
        assert pvs.count("SIM:M1.RBV") == 1
        assert None not in pvs
        assert set(pvs) == {"SIM:M1.RBV", "SIM:M1.VAL", "SIM:M1.MOVN"}

    def test_connect_connects_every_pv(self):
        component, backend = make_component()
        component.connect()
        assert set(backend.connect_calls) == set(PV_NAMES.values())

    def test_connect_in_simulation_does_not_touch_pvs(self):
        component, backend = make_component()
        component.connect(simulation=True)
        assert backend.connect_calls == []

    def test_connect_keeps_the_injected_wrapper(self):
        component, backend = make_component()
        component.connect()
        assert component.wrapper is backend


class TestSubscriptions:
    def callback(self, *args, **kwargs):
        pass

    def test_subscribe_channels_subscribes_each_channel(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channels(self.callback)
        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert subscribed == set(PV_NAMES.values())

    def test_subscribe_channels_skips_unsubscribed_channels(self):
        channels = dict(
            EPICS_CHANNELS,
            speed=readback_channel(".VELO", subscribe=False),
        )
        component, backend = make_component(epics_channels=channels)
        component.connect()
        component.subscribe_channels(self.callback)
        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert "SIM:M1.VELO" not in subscribed

    def test_unsubscribed_channel_still_connects_and_reads_on_demand(self):
        channels = dict(
            EPICS_CHANNELS,
            speed=readback_channel(".VELO", subscribe=False),
        )
        component, backend = make_component(epics_channels=channels)
        backend.values["SIM:M1.VELO"] = 7.5

        component.connect()
        component.subscribe_channels(self.callback)

        subscribed = {pv for pv, *_ in backend.subscriptions}
        assert "SIM:M1.VELO" in backend.connect_calls
        assert "SIM:M1.VELO" not in subscribed
        assert component.get_channel_value("speed") == 7.5

    def test_command_channel_is_lazy_and_connects_on_first_write(self):
        channels = dict(EPICS_CHANNELS, stop=command_channel(".STOP"))
        pv_names = dict(PV_NAMES, stop="SIM:M1.STOP")
        component, backend = make_component(
            epics_channels=channels,
            pv_names_by_channel=pv_names,
        )

        component.connect()
        assert "SIM:M1.STOP" not in backend.connect_calls

        component.put_channel_value("stop", 1)

        assert "SIM:M1.STOP" in backend.connect_calls
        assert backend.values["SIM:M1.STOP"] == 1

    def test_subscribe_channel_honours_as_string_from_channel_info(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channel("label", self.callback)
        ((_, _, _, _, as_string),) = backend.subscriptions
        assert as_string is True

    def test_subscribe_channel_without_pv_is_a_noop(self):
        component, backend = make_component(
            pv_names_by_channel=dict(PV_NAMES, label=None)
        )
        component.connect()
        assert component.subscribe_channel("label", self.callback) is None
        assert backend.subscriptions == []

    def test_shutdown_closes_every_subscription(self):
        component, backend = make_component()
        component.connect()
        component.subscribe_channels(self.callback)
        assert len(backend.subscriptions) == len(PV_NAMES)
        component.shutdown()
        assert backend.subscriptions == []
        assert component.subscriptions == []


class TestReadsAndWrites:
    def test_get_channel_value_uses_as_string_from_channel_info(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.DESC"] = b"motor"
        assert component.get_channel_value("label") == "motor"

    def test_put_channel_value_writes_the_resolved_pv(self):
        component, backend = make_component()
        component.connect()
        component.put_channel_value("target", 42.0)
        assert backend.values["SIM:M1.VAL"] == 42.0

    def test_enum_readback_channel_reads_choice_strings_by_default(self):
        channels = {"range": enum_readback_channel(".RANGE")}
        component, backend = make_component(
            epics_channels=channels,
            pv_names_by_channel={"range": "SIM:M1.RANGE"},
        )
        component.connect()
        backend.value_choices["SIM:M1.RANGE"] = ["Off", "Low"]
        backend.values["SIM:M1.RANGE"] = 1

        assert component.get_channel_value("range") == "Low"

    def test_enum_command_channel_writes_exact_value_without_conversion(self):
        channels = {"set_range": enum_command_channel(".RANGE_S")}
        component, backend = make_component(
            epics_channels=channels,
            pv_names_by_channel={"set_range": "SIM:M1.RANGE_S"},
        )
        component.connect()
        backend.value_choices["SIM:M1.RANGE_S"] = ["Off", "Low", "Med", "High"]

        component.put_channel_value("set_range", "High")

        assert backend.values["SIM:M1.RANGE_S"] == "High"
        assert ("get_value_choices", "SIM:M1.RANGE_S", None) not in backend.get_calls


class TestDynamicEnumParam:
    def test_populates_instance_choices_from_epics(
        self, daemon_device_harness, fake_backend
    ):
        prepare_dynamic_enum_backend(fake_backend)

        device = daemon_device_harness.create_master(
            DynamicEnumProbe, name="dynamic_enum", pv_root="SIM:"
        )

        assert device.parameters is not DynamicEnumProbe.parameters
        assert device.parameters["heater_range"].type.vals == ("Off", "Low", "High")
        assert DynamicEnumProbe.parameters["heater_range"].type.vals == ()

    def test_can_set_all_valid_choices(self, daemon_device_harness, fake_backend):
        prepare_dynamic_enum_backend(fake_backend)

        device = daemon_device_harness.create_master(
            DynamicEnumProbe, name="dynamic_enum", pv_root="SIM:"
        )

        choices = device.parameters["heater_range"].type.vals
        assert choices == ("Off", "Low", "High")
        for choice in choices:
            device.heater_range = choice
            assert fake_backend.values["SIM:RANGE_S"] == choice

    def test_rejects_set_value_outside_epics_choices(
        self, daemon_device_harness, fake_backend
    ):
        prepare_dynamic_enum_backend(fake_backend)
        device = daemon_device_harness.create_master(
            DynamicEnumProbe, name="dynamic_enum", pv_root="SIM:"
        )

        with pytest.raises(ConfigurationError, match="invalid value"):
            device.heater_range = "Medium"

    def test_instances_keep_independent_enum_choice_objects(
        self, daemon_device_harness, fake_backend
    ):
        # Guard for the per-instance clone hack in _clone_epics_enum_params:
        # each device deep-copies its enum type so live IOC choices stay
        # isolated. If NICOS's parameter lifecycle changed and the clone stopped
        # taking effect, the two instances would share one enum object and
        # clobber each other's choices - this must then fail loudly.
        for root, choices in (("SIM:", ["Off", "Low"]), ("SIM2:", ["Cold", "Hot"])):
            fake_backend.value_choices[f"{root}RANGE"] = choices
            fake_backend.value_choices[f"{root}RANGE_S"] = choices
            fake_backend.values[f"{root}RANGE"] = 0
            fake_backend.values[f"{root}RANGE_S"] = choices[0]

        first = daemon_device_harness.create_master(
            DynamicEnumProbe, name="enum_a", pv_root="SIM:"
        )
        second = daemon_device_harness.create_master(
            DynamicEnumProbe, name="enum_b", pv_root="SIM2:"
        )

        first_type = first.parameters["heater_range"].type
        second_type = second.parameters["heater_range"].type
        assert first_type is not second_type
        assert first_type.vals == ("Off", "Low")
        assert second_type.vals == ("Cold", "Hot")
        # The shared class template is never mutated by either instance.
        assert DynamicEnumProbe.parameters["heater_range"].type.vals == ()

    def test_pair_reads_monitor_updated_enum_param(self, device_harness, fake_backend):
        prepare_dynamic_enum_backend(fake_backend)
        daemon_device, poller_device = device_harness.create_pair(
            DynamicEnumProbe,
            name="dynamic_enum",
            shared={"pv_root": "SIM:"},
        )

        fake_backend.emit_update("SIM:RANGE", value=2)

        assert device_harness.run_daemon(lambda: daemon_device.heater_range) == "High"
        assert device_harness.run_poller(lambda: poller_device.heater_range) == "High"


class TestWaitFor:
    def test_returns_immediately_when_already_matching(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 0
        component.wait_for("moving", 0, timeout=0.1)
        assert component.subscriptions == []
        assert backend.subscriptions == []

    def test_completes_when_a_monitor_update_matches(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 1

        original_get = backend.get_pv_value

        def get_and_update(pvname, as_string=False):
            result = original_get(pvname, as_string)
            backend.emit_update(pvname, value=0)
            return result

        backend.get_pv_value = get_and_update
        component.wait_for("moving", 0, timeout=1.0)
        assert backend.subscriptions == []

    def test_times_out(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.MOVN"] = 1
        try:
            component.wait_for("moving", 0, timeout=0.05)
        except CommunicationError:
            pass
        else:
            raise AssertionError("expected CommunicationError")
        assert backend.subscriptions == []

    def test_precision_match(self):
        component, backend = make_component()
        component.connect()
        backend.values["SIM:M1.RBV"] = 9.999
        component.wait_for("value", 10.0, timeout=0.1, precision=0.01)


class CacheStub:
    def __init__(self):
        self.data = {}
        self.puts = []

    def put(self, dev, key, value, ts=None):
        self.data[key] = value
        self.puts.append((key, value))

    def get(self, dev, key, default=None, mintime=None):
        return self.data.get(key, default)


class GlueProbe:
    _dispatch_channel_update = EpicsDeviceBase._dispatch_channel_update
    _on_channel_update = EpicsDeviceBase._on_channel_update
    _on_connection_change = EpicsDeviceBase._on_connection_change
    _connection_change_affects_status = (
        EpicsDeviceBase._connection_change_affects_status
    )
    _status_snapshot = EpicsDeviceBase._status_snapshot
    _refresh_status = EpicsDeviceBase._refresh_status
    _read_channel_cached = EpicsDeviceBase._read_channel_cached
    _read_primary_alarm = EpicsDeviceBase._read_primary_alarm
    _log_alarm_once = EpicsDeviceBase._log_alarm_once
    doStatus = EpicsDeviceBase.doStatus

    _primary_channel = "value"
    monitor = True

    def __init__(self, compute_status=None):
        self._epics, self.backend = make_component()
        self._epics.connect()
        self._epics_channels = self._epics.epics_channels
        self._name = "probe"
        self._cache = CacheStub()
        self.log = StubLog()
        self._alarm_state = {}
        self._disconnected = set()
        if compute_status is not None:
            self._compute_status = compute_status
        else:
            self._compute_status = lambda maxage=0: (status.OK, "")


class FailingUpdateProbe(GlueProbe):
    def _on_channel_update(self, update):
        raise RuntimeError("bad callback data")


class TestDeviceGlue:
    def test_value_change_caches_under_resolved_key(self):
        probe = GlueProbe()
        probe._on_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.VAL",
                channel="target",
                value=42.0,
                units="mm",
            )
        )
        assert probe._cache.data["target"] == 42.0

    def test_primary_channel_also_caches_unit_and_alarm(self):
        probe = GlueProbe()
        probe._on_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.RBV",
                channel="value",
                value=1.0,
                units="mm",
                severity=status.WARN,
                message="hot",
            )
        )
        assert probe._cache.data["value"] == 1.0
        assert probe._cache.data["unit"] == "mm"
        assert probe._cache.data["value_status"] == (status.WARN, "hot")

    def test_limits_cache_key_caches_update_limits(self):
        channels = dict(
            EPICS_CHANNELS,
            target=setpoint_channel(
                ".VAL", cache_key="target", limits_cache_key="abslimits"
            ),
        )
        probe = GlueProbe()
        probe._epics, probe.backend = make_component(epics_channels=channels)
        probe._epics.connect()
        probe._epics_channels = probe._epics.epics_channels
        probe._on_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.VAL",
                channel="target",
                value=42.0,
                limits=(-1.0, 1.0),
            )
        )
        assert probe._cache.data["abslimits"] == (-1.0, 1.0)

    def test_status_channel_triggers_status_recompute(self):
        calls = []

        def compute(maxage=0):
            calls.append(maxage)
            return status.BUSY, "moving"

        probe = GlueProbe(compute_status=compute)
        probe._on_channel_update(
            ChannelUpdate(pv_name="SIM:M1.MOVN", channel="moving", value=1)
        )
        assert calls == [None]
        assert probe._cache.data["status"] == (status.BUSY, "moving")

    def test_status_update_logs_alarm_transitions_once(self):
        probe = GlueProbe()
        update = ChannelUpdate(
            pv_name="SIM:M1.RBV",
            channel="value",
            value=1.0,
            severity=status.WARN,
            message="hot",
        )

        probe._on_channel_update(update)
        probe._on_channel_update(update)
        probe._on_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.RBV",
                channel="value",
                value=1.0,
                severity=status.ERROR,
                message="failed",
            )
        )

        assert probe.log.messages == [
            ("warning", "value (hot)"),
            ("error", "value (failed)"),
        ]

    def test_callback_error_caches_visible_unknown_status(self):
        probe = FailingUpdateProbe()

        probe._dispatch_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.RBV",
                channel="value",
                value=99,
            )
        )

        severity, message = probe._cache.data["status"]
        assert severity == status.UNKNOWN
        assert "error handling update for EPICS channel 'value'" in message
        assert "bad callback data" in message
        assert probe.log.messages == [
            (
                "warning",
                "error handling update for EPICS channel 'value' (PV SIM:M1.RBV)",
            )
        ]

    def test_value_only_channel_does_not_recompute_status(self):
        def compute(maxage=0):
            raise AssertionError("status must not be recomputed for VALUE channels")

        probe = GlueProbe(compute_status=compute)
        probe._on_channel_update(
            ChannelUpdate(
                pv_name="SIM:M1.VAL",
                channel="target",
                value=42.0,
                units="mm",
            )
        )
        assert "status" not in probe._cache.data

    def test_primary_disconnect_caches_lost_epics_connection(self):
        probe = GlueProbe()
        probe._on_connection_change(
            ConnectionUpdate("value", False, pv_name="SIM:M1.RBV")
        )
        assert probe._cache.data["status"] == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
        assert any(level == "warning" for level, _ in probe.log.messages)

    def test_non_primary_disconnect_is_ignored(self):
        probe = GlueProbe()
        probe._on_connection_change(
            ConnectionUpdate("target", False, pv_name="SIM:M1.VAL")
        )
        assert "status" not in probe._cache.data
        assert probe.log.messages == []

    def test_one_reconnect_does_not_mask_another_channels_loss(self):
        # 'value' (primary) and 'moving' (status_channel) both affect status.
        probe = GlueProbe()
        probe._on_connection_change(
            ConnectionUpdate("moving", False, pv_name="SIM:M1.MOVN")
        )
        probe._on_connection_change(
            ConnectionUpdate("value", False, pv_name="SIM:M1.RBV")
        )
        probe._on_connection_change(
            ConnectionUpdate("value", True, pv_name="SIM:M1.RBV")
        )
        # 'moving' is still down, so the device must not report OK.
        assert probe.doStatus(maxage=None) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )

    def test_read_cached_prefers_cache(self):
        probe = GlueProbe()
        probe._cache.data["value"] = 5.5
        assert probe._read_channel_cached("value") == 5.5
        assert probe.backend.get_calls == []

    def test_read_cached_falls_back_to_epics(self):
        probe = GlueProbe()
        probe.backend.values["SIM:M1.RBV"] = 3.25
        assert probe._read_channel_cached("value") == 3.25
        assert probe.backend.get_calls

    def test_read_cached_maxage_zero_always_asks(self):
        probe = GlueProbe()
        probe._cache.data["value"] = 5.5
        probe.backend.values["SIM:M1.RBV"] = 3.25
        assert probe._read_channel_cached("value", maxage=0) == 3.25

    def test_status_reads_cache_unless_freshness_is_forced(self):
        probe = GlueProbe()
        probe._cache.data["status"] = (status.BUSY, "moving")
        assert probe.doStatus(maxage=None) == (status.BUSY, "moving")

    def test_primary_alarm_timeout_reports_unknown_connection_loss(self):
        probe = GlueProbe()
        probe.backend.disconnect_backend()
        assert probe._read_primary_alarm() == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )


MULTI_CHANNELS = {
    "voltage": readback_channel("-VMon", cache_key="vmon"),
    "power": setpoint_channel("-Pw", cache_key="power"),
    "status_on": status_channel("-Status-ON"),
}

SOURCES = {
    "ch0": "SIM:HVM-0:Ch0",
    "ch1": "SIM:HVM-0:Ch1",
}


def make_multi_component():
    backend = FakeEpicsBackend()
    component = EpicsMultiSourceComponent(MULTI_CHANNELS, SOURCES, wrapper=backend)
    return component, backend


class MultiGlueProbe:
    _on_channel_update = EpicsMultiSourceBase._on_channel_update
    _on_connection_change = EpicsDeviceBase._on_connection_change
    _connection_change_affects_status = (
        EpicsMultiSourceBase._connection_change_affects_status
    )
    _source_alarm_key = EpicsMultiSourceBase._source_alarm_key
    _compute_status = EpicsMultiSourceBase._compute_status
    _read_source_alarm = EpicsMultiSourceBase._read_source_alarm
    _status_snapshot = EpicsDeviceBase._status_snapshot
    _refresh_status = EpicsDeviceBase._refresh_status
    doStatus = EpicsDeviceBase.doStatus

    monitor = True
    sources = SOURCES
    _epics_channels = MULTI_CHANNELS

    def __init__(self):
        self._name = "multi_probe"
        self._cache = CacheStub()
        self.log = StubLog()
        self._disconnected = set()
        self._epics = EpicsMultiSourceComponent(
            MULTI_CHANNELS, SOURCES, wrapper=FakeEpicsBackend()
        )


class TestMultiSource:
    def test_source_pv_is_prefix_plus_suffix(self):
        component, _ = make_multi_component()
        assert component.source_pv("ch1", "voltage") == "SIM:HVM-0:Ch1-VMon"

    def test_source_key_namespaces_per_source(self):
        component, _ = make_multi_component()
        assert component.source_key("ch0", "voltage") == "ch0/vmon"
        assert component.source_key("ch1", "status_on") == "ch1/status_on"

    def test_channel_keys_are_visible_for_device_stale_guard(self):
        component, _ = make_multi_component()
        assert set(component.pv_names_by_channel) == set(MULTI_CHANNELS)

    def test_pvs_to_connect_is_the_cross_product(self):
        component, _ = make_multi_component()
        pvs = component.pvs_to_connect()
        assert len(pvs) == len(SOURCES) * len(MULTI_CHANNELS)
        assert "SIM:HVM-0:Ch0-Pw" in pvs
        assert "SIM:HVM-0:Ch1-Status-ON" in pvs

    def test_subscribe_channels_populates_source_id_on_updates(self):
        component, backend = make_multi_component()
        component.connect()
        updates = []
        component.subscribe_channels(updates.append)

        backend.values["SIM:HVM-0:Ch1-VMon"] = 999.0
        backend.emit_update("SIM:HVM-0:Ch1-VMon")

        assert len(backend.subscriptions) == len(SOURCES) * len(MULTI_CHANNELS)
        assert updates == [
            ChannelUpdate(
                channel="voltage",
                value=999.0,
                pv_name="SIM:HVM-0:Ch1-VMon",
                source_id="ch1",
            )
        ]

    def test_get_source_value_reads_the_source_pv(self):
        component, backend = make_multi_component()
        component.connect()
        backend.values["SIM:HVM-0:Ch1-VMon"] = 999.0
        assert component.get_source_value("ch1", "voltage") == 999.0

    def test_put_source_value_writes_the_source_pv(self):
        component, backend = make_multi_component()
        component.connect()
        component.put_source_value("ch1", "power", 1)
        assert backend.values["SIM:HVM-0:Ch1-Pw"] == 1

    def test_get_source_value_translates_dead_ioc_to_communication_error(self):
        component, backend = make_multi_component()
        component.connect()
        backend.disconnect_backend()
        with pytest.raises(CommunicationError):
            component.get_source_value("ch1", "voltage")

    def test_put_source_value_translates_dead_ioc_to_communication_error(self):
        component, backend = make_multi_component()
        component.connect()
        backend.disconnect_backend()
        with pytest.raises(CommunicationError):
            component.put_source_value("ch1", "power", 1)

    def test_put_source_value_writes_declared_enum_channel_without_conversion(self):
        channels = {"power": enum_setpoint_channel("-Pw")}
        component = EpicsMultiSourceComponent(
            channels, SOURCES, wrapper=FakeEpicsBackend()
        )
        backend = component.wrapper
        component.connect()

        component.put_source_value("ch1", "power", "On")

        assert backend.values["SIM:HVM-0:Ch1-Pw"] == "On"

    def test_connection_loss_is_part_of_worst_case_status(self):
        probe = MultiGlueProbe()

        probe._on_connection_change(
            ConnectionUpdate(
                "status_on",
                False,
                pv_name="SIM:HVM-0:Ch1-Status-ON",
                source_id="ch1",
            )
        )

        assert probe.doStatus(maxage=None) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )
        assert probe.doStatus(maxage=0) == (
            status.UNKNOWN,
            "lost connection to EPICS",
        )

    def test_reconnect_clears_source_connection_loss_status(self):
        probe = MultiGlueProbe()
        probe._on_connection_change(
            ConnectionUpdate(
                "status_on",
                False,
                pv_name="SIM:HVM-0:Ch1-Status-ON",
                source_id="ch1",
            )
        )

        probe._on_connection_change(
            ConnectionUpdate(
                "status_on",
                True,
                pv_name="SIM:HVM-0:Ch1-Status-ON",
                source_id="ch1",
            )
        )

        assert probe.doStatus(maxage=None) == (status.OK, "")

    def test_connected_source_in_alarm_is_folded_into_status(self):
        # A connected source reporting a hardware alarm must not read OK. The
        # monitor populates the cached path; the IOC's fresh alarm read backs
        # the maxage=0 path (which now reads hardware, per the maxage rule).
        probe = MultiGlueProbe()
        probe._epics.wrapper.alarms["SIM:HVM-0:Ch1-VMon"] = (
            status.ERROR,
            "overvoltage",
        )
        probe._on_channel_update(
            ChannelUpdate(
                channel="voltage",
                value=1.0,
                severity=status.ERROR,
                message="overvoltage",
                source_id="ch1",
            )
        )
        assert probe.doStatus(maxage=None) == (status.ERROR, "overvoltage")
        assert probe.doStatus(maxage=0) == (status.ERROR, "overvoltage")

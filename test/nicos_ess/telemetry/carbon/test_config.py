"""Tests for CarbonConfig parsing and client creation."""

from types import SimpleNamespace

import pytest

from nicos.core import ConfigurationError
from nicos_ess.telemetry.carbon.config import (
    CarbonConfig,
    _parse_bool,
    _parse_float,
    _parse_int,
    _parse_text,
)


class TestParseBool:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (True, True),
            (False, False),
            (1, True),
            (0, False),
            ("true", True),
            ("TRUE", True),
            ("yes", True),
            ("on", True),
            ("1", True),
            ("false", False),
            ("no", False),
            ("off", False),
            ("0", False),
            (None, False),
        ],
    )
    def test_parse_bool(self, value, expected):
        assert _parse_bool("telemetry_enabled", value) == expected

    def test_parse_bool_default(self):
        assert _parse_bool("telemetry_enabled", None, default=True) is True

    @pytest.mark.parametrize("value", ["garbage", 2, 1.5])
    def test_parse_bool_raises_on_invalid_values(self, value):
        with pytest.raises(ConfigurationError):
            _parse_bool("telemetry_enabled", value)


class TestParseNumeric:
    def test_parse_int(self):
        assert _parse_int("telemetry_queue_max", "42", 0) == 42
        assert _parse_int("telemetry_queue_max", None, 7) == 7

    def test_parse_float(self):
        assert _parse_float("telemetry_flush_interval_s", "3.14", 0.0) == pytest.approx(
            3.14
        )
        assert _parse_float("telemetry_flush_interval_s", None, 2.0) == pytest.approx(
            2.0
        )

    @pytest.mark.parametrize(
        "parser, setting_name, value",
        [
            (_parse_int, "telemetry_queue_max", "not_a_number"),
            (_parse_int, "telemetry_queue_max", True),
            (_parse_float, "telemetry_flush_interval_s", "bad"),
            (_parse_float, "telemetry_flush_interval_s", False),
        ],
    )
    def test_numeric_parsers_raise_on_invalid_values(self, parser, setting_name, value):
        with pytest.raises(ConfigurationError):
            parser(setting_name, value, 1)

    def test_parse_int_enforces_range(self):
        with pytest.raises(ConfigurationError):
            _parse_int("telemetry_carbon_port", "0", 2003, minimum=1)

    def test_parse_float_enforces_range(self):
        with pytest.raises(ConfigurationError):
            _parse_float("telemetry_flush_interval_s", "-1", 10, minimum=0)


class TestParseText:
    def test_parse_text(self):
        assert _parse_text("telemetry_prefix", " ess ", "nicosserver") == "ess"
        assert _parse_text("telemetry_prefix", None, "nicosserver") == "nicosserver"

    @pytest.mark.parametrize("value", [[], 1, object()])
    def test_parse_text_raises_on_invalid_values(self, value):
        with pytest.raises(ConfigurationError):
            _parse_text("telemetry_prefix", value, "nicosserver")


class TestCarbonConfigFromNicosConfig:
    def test_returns_none_when_disabled(self):
        assert CarbonConfig.from_nicos_config(SimpleNamespace()) is None

    def test_returns_none_when_explicitly_disabled(self):
        cfg = SimpleNamespace(telemetry_enabled=False)
        assert CarbonConfig.from_nicos_config(cfg) is None

    def test_raises_when_enabled_without_host(self):
        cfg = SimpleNamespace(telemetry_enabled=True)
        with pytest.raises(ConfigurationError):
            CarbonConfig.from_nicos_config(cfg)

    def test_raises_when_enabled_with_blank_host(self):
        cfg = SimpleNamespace(
            telemetry_enabled=True,
            telemetry_carbon_host="   ",
        )
        with pytest.raises(ConfigurationError):
            CarbonConfig.from_nicos_config(cfg)

    @pytest.mark.parametrize(
        "extra_config",
        [
            {"telemetry_carbon_port": "not-a-port"},
            {"telemetry_carbon_port": "70000"},
            {"telemetry_carbon_host": []},
            {"telemetry_prefix": "   "},
            {"telemetry_prefix": 1},
            {"instrument": "   "},
            {"instrument": object()},
            {"telemetry_queue_max": "0"},
            {"telemetry_flush_interval_s": "-1"},
            {"telemetry_heartbeat_interval_s": "-1"},
            {"telemetry_connect_timeout_s": "-1"},
            {"telemetry_send_timeout_s": "-1"},
        ],
    )
    def test_raises_on_invalid_explicit_values(self, extra_config):
        config_values = {
            "telemetry_enabled": True,
            "telemetry_carbon_host": "carbon.local",
            "instrument": "bifrost",
        }
        config_values.update(extra_config)
        cfg = SimpleNamespace(**config_values)
        with pytest.raises(ConfigurationError):
            CarbonConfig.from_nicos_config(cfg)

    def test_returns_config_with_defaults(self):
        cfg = SimpleNamespace(
            telemetry_enabled=True,
            telemetry_carbon_host="carbon.local",
            instrument="bifrost",
        )
        result = CarbonConfig.from_nicos_config(cfg)
        assert isinstance(result, CarbonConfig)
        assert result.host == "carbon.local"
        assert result.port == 2003
        assert result.prefix == "nicosserver"
        assert result.instrument == "bifrost"
        assert result.flush_interval_s == 10.0
        assert result.reconnect_delay_s == 2.0
        assert result.queue_max == 10000

    def test_returns_config_with_overrides(self):
        cfg = SimpleNamespace(
            telemetry_enabled="true",
            telemetry_carbon_host="10.0.0.1",
            telemetry_carbon_port="2004",
            telemetry_prefix="ess",
            instrument="ymir",
            telemetry_flush_interval_s="5",
            telemetry_reconnect_delay_s="3",
            telemetry_queue_max="500",
            telemetry_connect_timeout_s="2",
            telemetry_send_timeout_s="0.5",
            telemetry_heartbeat_interval_s="15",
        )
        result = CarbonConfig.from_nicos_config(cfg)
        assert result.host == "10.0.0.1"
        assert result.port == 2004
        assert result.prefix == "ess"
        assert result.instrument == "ymir"
        assert result.flush_interval_s == 5.0
        assert result.reconnect_delay_s == 3.0
        assert result.queue_max == 500
        assert result.connect_timeout_s == 2.0
        assert result.send_timeout_s == 0.5
        assert result.heartbeat_interval_s == 15.0

    def test_config_is_frozen(self):
        cfg = SimpleNamespace(
            telemetry_enabled=True,
            telemetry_carbon_host="carbon.local",
        )
        result = CarbonConfig.from_nicos_config(cfg)
        with pytest.raises(AttributeError):
            result.host = "other"


def test_direct_carbon_config_defaults_match_nicos_config_defaults():
    cfg = CarbonConfig(host="carbon.local")

    assert cfg.port == 2003
    assert cfg.prefix == "nicosserver"
    assert cfg.instrument == "unknown"

# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Tests for CarbonConfig parsing and client creation."""

from types import SimpleNamespace

import pytest

from nicos.core import ConfigurationError
from nicos_ess.telemetry.carbon.config import (
    CarbonConfig,
    _parse_bool,
    _parse_float,
    _parse_int,
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
        assert _parse_bool(value) == expected

    def test_parse_bool_default(self):
        assert _parse_bool(None, default=True) is True
        assert _parse_bool("garbage", default=True) is True


class TestParseNumeric:
    def test_parse_int(self):
        assert _parse_int("42", 0) == 42
        assert _parse_int("not_a_number", 99) == 99
        assert _parse_int(None, 7) == 7

    def test_parse_float(self):
        assert _parse_float("3.14", 0.0) == pytest.approx(3.14)
        assert _parse_float("bad", 1.5) == pytest.approx(1.5)
        assert _parse_float(None, 2.0) == pytest.approx(2.0)


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
        assert result.prefix == "nicos"
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

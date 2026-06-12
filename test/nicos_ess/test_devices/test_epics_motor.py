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
#   Matt Clarke <matt.clarke@ess.eu>
#
# *****************************************************************************

from unittest.mock import Mock

import pytest

# pytest.importorskip("graypy")
from nicos.commands.device import adjust
from nicos.core import status
from nicos_ess.devices.epics.pva.motor import EpicsMotor
from test.nicos_ess.test_devices.doubles.epics_pva_backend import FakeEpicsComponent

session_setup = "ess_motors"


class FakeEpicsMotor(EpicsMotor):
    position = 0

    @classmethod
    def _initial_values(cls):
        return {
            "speed": 10,
            "position": cls.position,
            "stop": 0,
            "lowlimit": -110,
            "highlimit": 110,
            "readpv": cls.position,
            "writepv": cls.position,
            "offset": 0,
            "enable": 1,
            "direction": 0,
            "unit": "mm",
            "target": 45,
            "position_deadband": 0.1,
            "diallowlimit": -120,
            "dialhighlimit": 120,
            "dir": "Pos",
            "description": "motor1 test device",
            "monitor_deadband": 0.2,
            "moving": False,
            "donemoving": True,
            "value": 0,
            "dialvalue": 0,
        }

    @property
    def values(self):
        return self._values

    def doPreinit(self, mode):
        self._values = self._initial_values()
        self._record_fields = {}
        self._epics = FakeEpicsComponent(self._values)

    def doInit(self, mode):
        pass

    def doRead(self, maxage=None):
        return self._epics.get_pv("position")

    def doReadUnit(self, maxage=None):
        return self.values["unit"]

    def _read_cached(self, field, as_string=None, maxage=None):
        return self.values[field]


class DerivedEpicsMotor(FakeEpicsMotor):
    def doPreinit(self, mode):
        FakeEpicsMotor.doPreinit(self, mode)
        self._record_fields = {"extra_field": "XTR"}


class TestEpicsMotor:
    motor = None

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.motor = self.session.getDevice("motor1")
        self.motor.values["lowlimit"] = -110
        self.motor.values["highlimit"] = 110
        self.motor.offset = 0

    def test_adjust_command_sets_offset_correctly(self):
        assert self.motor.offset == 0

        new_pos = 50
        adjust(self.motor, new_pos)

        assert new_pos == self.motor.offset

    @pytest.mark.skip(reason="I don't think abslimits are supposed to change at all")
    def test_adjust_command_causes_absolute_limits_to_be_updated(self):
        low, high = self.motor.abslimits

        new_pos = 50
        adjust(self.motor, new_pos)

        assert (low + new_pos, high + new_pos) == self.motor.abslimits

    @pytest.mark.skip(reason="Once we configure test epics repo we can reintroduce it")
    def test_adjust_command_causes_user_limits_to_be_updated(self):
        low, high = self.motor.userlimits

        new_pos = 50
        adjust(self.motor, new_pos)

        assert (low + new_pos, high + new_pos) == self.motor.userlimits

    def test_setting_offset_affects_read_offset_correctly(self):
        assert self.motor.offset == 0

        new_offset = 50
        self.motor.offset = new_offset

        assert new_offset == self.motor.offset

    @pytest.mark.skip(reason="I don't think abslimits are supposed to change at all")
    def test_setting_offset_causes_absolute_limits_to_be_updated(self):
        low, high = self.motor.abslimits

        new_offset = 50
        self.motor.offset = new_offset

        assert (low + new_offset, high + new_offset) == self.motor.abslimits

    @pytest.mark.skip(reason="Once we configure test epics repo we can reintroduce it")
    def test_setting_offset_causes_user_limits_to_be_updated(self):
        low, high = self.motor.userlimits

        new_offset = 50
        self.motor.offset = new_offset

        assert (low + new_offset, high + new_offset) == self.motor.userlimits

    @pytest.mark.parametrize(
        "test_alerts_input",
        [
            status.OK,
            status.WARN,
            status.ERROR,
            status.UNKNOWN,
        ],
    )
    @pytest.mark.parametrize(
        "msgtxt_return_values",
        [
            (status.OK, ""),
            (status.WARN, ""),
            (status.ERROR, ""),
            (status.UNKNOWN, ""),
        ],
    )
    def test_alerts_have_correct_precedence(
        self, test_alerts_input, msgtxt_return_values
    ):
        self.motor._get_msgtxt = Mock(return_value=msgtxt_return_values)

        self.motor._log_epics_msg_info = Mock(return_value=None)
        self.motor._motor_status = None, None

        msg_stat, _ = self.motor._get_msgtxt()
        motor_stat, _ = self.motor._update_status_with_msgtxt(test_alerts_input, "")
        assert msg_stat <= motor_stat
        if motor_stat == status.ERROR and msg_stat == status.ERROR:
            assert msg_stat == motor_stat


class TestDerivedEpicsMotor:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.motor1 = self.session.getDevice("motor1")
        self.motor2 = self.session.getDevice("motor2")

    def test_record_fields(self):
        motor1_fields = self.motor1._record_fields
        motor2_fields = self.motor2._record_fields
        difference = set(motor2_fields) ^ set(motor1_fields)
        assert difference

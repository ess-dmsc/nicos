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

import pytest

from nicos.core import status

from test.nicos_ess.test_devices.epics_motor.helpers import (
    START_STATUS_TRANSITION_CASES,
    STATUS_CASES,
    STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES,
    assert_status_result,
    changed_pv_value,
    create_monitored_motor_pair,
    create_motor,
    create_motor_pair,
    pv,
    set_state_pvs,
)


class TestEpicsMotorStatus:
    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_from_direct_backend_state(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        set_state_pvs(fake_backend, state_pvs)
        dev = create_motor(device_harness, **cfg_overrides)

        st, msg = dev.status(0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_from_existing_epics_state_when_pair_is_created(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        set_state_pvs(fake_backend, state_pvs)
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, **cfg_overrides
        )

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "state_pvs,cfg_overrides,expected_status,expected_message,expect_empty_message",
        STATUS_CASES,
    )
    def test_motor_status_updates_while_pair_is_running_via_poller_callbacks(
        self,
        device_harness,
        fake_backend,
        state_pvs,
        cfg_overrides,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, **cfg_overrides
        )
        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.OK

        for key, value in state_pvs:
            fake_backend.emit_update(key, value=value)
        for key, value in state_pvs:
            fake_backend.values[key] = changed_pv_value(value)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    def test_motor_status_warns_immediately_when_only_cnen_changes_to_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv("-PwrAuto"), value=0)
        fake_backend.emit_update(pv(".CNEN"), value=0)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert st == status.WARN
        assert "motor is not enabled" in msg

    def test_motor_status_clears_warning_immediately_when_only_cnen_changes_to_enabled(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv("-PwrAuto")] = 0
        fake_backend.values[pv(".CNEN")] = 0
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)
        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.WARN

        fake_backend.emit_update(pv(".CNEN"), value=1)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert st == status.OK
        assert msg == ""

    def test_motor_status_alarm_error_takes_precedence_over_motion_flags(
        self, device_harness, fake_backend
    ):
        fake_backend.values[pv(".DMOV")] = 0
        fake_backend.values[pv(".MOVN")] = 1
        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        dev = create_motor(device_harness, has_msgtxt=False)

        assert dev.status(0) == (status.ERROR, "record alarm")

    @pytest.mark.parametrize(
        "rbv_alarm,msgtxt_severity,msgtxt,state_pvs,expected_status,expected_message,expect_empty_message",
        STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES,
    )
    def test_motor_status_selects_correct_severity_and_message_source(
        self,
        device_harness,
        fake_backend,
        rbv_alarm,
        msgtxt_severity,
        msgtxt,
        state_pvs,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        fake_backend.alarms[pv(".RBV")] = rbv_alarm
        fake_backend.values[pv("-MsgTxt")] = msgtxt
        fake_backend.values[pv("-MsgTxt.SEVR")] = msgtxt_severity
        set_state_pvs(fake_backend, state_pvs)
        dev = create_motor(device_harness, has_msgtxt=True)

        st, msg = dev.status(0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    @pytest.mark.parametrize(
        "rbv_alarm,msgtxt_severity,msgtxt,state_pvs,expected_status,expected_message,expect_empty_message",
        STATUS_SEVERITY_AND_MESSAGE_PRECEDENCE_CASES,
    )
    def test_motor_status_updates_correct_severity_and_message_source(
        self,
        device_harness,
        fake_backend,
        rbv_alarm,
        msgtxt_severity,
        msgtxt,
        state_pvs,
        expected_status,
        expected_message,
        expect_empty_message,
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=True
        )

        fake_backend.alarms[pv(".RBV")] = rbv_alarm
        fake_backend.values[pv("-MsgTxt")] = msgtxt
        fake_backend.values[pv("-MsgTxt.SEVR")] = msgtxt_severity
        set_state_pvs(fake_backend, state_pvs)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st, msg, expected_status, expected_message, expect_empty_message
        )

    def test_motor_status_from_existing_epics_alarm_state_when_pair_is_created(
        self, device_harness, fake_backend
    ):
        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=False
        )

        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.ERROR,
            "record alarm",
        )

    def test_motor_status_updates_from_alarm_state_while_pair_is_running(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=False
        )

        fake_backend.alarms[pv(".RBV")] = (status.ERROR, "record alarm")
        fake_backend.emit_update(pv(".DMOV"), value=1)
        fake_backend.values[pv(".DMOV")] = 0

        assert device_harness.run_daemon(daemon_device.status, 0) == (
            status.ERROR,
            "record alarm",
        )

    @pytest.mark.parametrize(
        (
            "initial_state_pvs,rbv_alarm,msgtxt_severity,msgtxt,post_start_updates,"
            "expected_status_after_start,expected_message_after_start,"
            "expect_empty_message_after_start,expected_status_after_updates,"
            "expected_message_after_updates,expect_empty_message_after_updates"
        ),
        START_STATUS_TRANSITION_CASES,
    )
    def test_motor_status_transitions_after_start_respect_numeric_priority(
        self,
        device_harness,
        fake_backend,
        initial_state_pvs,
        rbv_alarm,
        msgtxt_severity,
        msgtxt,
        post_start_updates,
        expected_status_after_start,
        expected_message_after_start,
        expect_empty_message_after_start,
        expected_status_after_updates,
        expected_message_after_updates,
        expect_empty_message_after_updates,
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(
            device_harness, has_msgtxt=True
        )
        fake_backend.alarms[pv(".RBV")] = rbv_alarm
        fake_backend.values[pv("-MsgTxt")] = msgtxt
        fake_backend.values[pv("-MsgTxt.SEVR")] = msgtxt_severity

        for key, value in initial_state_pvs:
            fake_backend.emit_update(key, value=value)

        device_harness.run_daemon(daemon_device.start, 5.0)
        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st,
            msg,
            expected_status_after_start,
            expected_message_after_start,
            expect_empty_message_after_start,
        )

        for key, value in post_start_updates:
            fake_backend.emit_update(key, value=value)

        st, msg = device_harness.run_daemon(daemon_device.status, 0)
        assert_status_result(
            st,
            msg,
            expected_status_after_updates,
            expected_message_after_updates,
            expect_empty_message_after_updates,
        )

    def test_motor_connection_loss_sets_communication_failure_status_in_monitor_mode(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.disconnect_backend()

        # Cached status should immediately reflect communication failure
        assert device_harness.run_daemon(daemon_device.status) == (
            status.ERROR,
            "communication failure",
        )

        # if checking status with maxage=0, it will raise timeout error due to direct backend access, even in monitor mode
        hardware_status = device_harness.run_daemon(daemon_device.status, 0)
        assert hardware_status[0] == status.ERROR
        assert "timed out" in hardware_status[1]


class TestEpicsMotorCacheAndReadPaths:
    def test_daemon_read_uses_poller_cached_rbv_update(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv(".RBV"), value=9.5)
        fake_backend.values[pv(".RBV")] = 99.0

        assert device_harness.run_daemon(daemon_device.read, 0) == 9.5

    def test_daemon_iscompleted_uses_poller_cached_updates(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_monitored_motor_pair(device_harness)

        fake_backend.emit_update(pv(".RBV"), value=3.0)
        fake_backend.emit_update(pv(".VAL"), value=3.0)
        fake_backend.emit_update(pv(".RDBD"), value=0.1)
        fake_backend.emit_update(pv(".MOVN"), value=1)
        assert device_harness.run_daemon(daemon_device.isCompleted) is False

        fake_backend.emit_update(pv(".MOVN"), value=0)
        assert device_harness.run_daemon(daemon_device.isCompleted) is True

    def test_daemon_read_uses_backend_directly_when_monitor_is_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        fake_backend.emit_update(pv(".RBV"), value=9.5)
        fake_backend.values[pv(".RBV")] = 99.0

        assert device_harness.run_daemon(daemon_device.read, 0) == 99.0

    def test_daemon_status_uses_backend_directly_when_monitor_is_disabled(
        self, device_harness, fake_backend
    ):
        daemon_device, _poller_device = create_motor_pair(device_harness, monitor=False)

        fake_backend.emit_update(pv(".MISS"), value=1)
        fake_backend.values[pv(".MISS")] = 0

        assert device_harness.run_daemon(daemon_device.status, 0)[0] == status.OK

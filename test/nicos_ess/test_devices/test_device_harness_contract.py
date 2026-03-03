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

"""Contract tests for the reusable NICOS device harness.

These tests protect against harness drift when core NICOS session/cache APIs
change, and they verify helper methods used by device tests.
"""

from inspect import signature
from types import SimpleNamespace

import pytest

from nicos import session as nicos_session
from nicos.core import MAIN, MASTER, POLLER
from nicos.devices.cacheclient import CacheClient
from nicos.core.sessions import Session
from test.nicos_ess.device_harness import InMemoryCache, UnitTestSession
from test.nicos_ess.test_devices.doubles import HarnessLinearAxis


CACHE_METHODS = [
    "addCallback",
    "removeCallback",
    "get",
    "put",
    "put_raw",
    "setRewrite",
    "unsetRewrite",
    "clear",
    "invalidate",
    "history",
    "lock",
    "unlock",
]

SESSION_METHODS = [
    "getDevice",
    "delay",
    "checkAccess",
    "getExecutingUser",
    "checkUserLevel",
    "beginActionScope",
    "endActionScope",
    "action",
]


class HarnessSessionProbe(HarnessLinearAxis):
    """Test double that captures mode/sessiontype seen during device init."""

    def doInit(self, mode):
        self._init_mode = mode
        self._init_sessiontype = nicos_session.sessiontype
        super().doInit(mode)


@pytest.mark.parametrize("method_name", CACHE_METHODS)
def test_inmemory_cache_signature_matches_cacheclient(method_name):
    # If NICOS changes these signatures, harness users should notice immediately.
    assert signature(getattr(InMemoryCache, method_name)) == signature(
        getattr(CacheClient, method_name)
    )


@pytest.mark.parametrize("method_name", SESSION_METHODS)
def test_unittest_session_signature_matches_core_session(method_name):
    # Keep the unit session drop-in compatible for device code paths.
    assert signature(getattr(UnitTestSession, method_name)) == signature(
        getattr(Session, method_name)
    )


def test_inmemory_cache_put_aged_creates_stale_entries_for_maxage_tests():
    # Setup
    cache = InMemoryCache()

    # Act
    cache.put_aged("dev", "value", 12.3, age_seconds=10, now=100.0)

    # Assert
    assert cache.get("dev", "value", mintime=95.0) is None
    assert cache.get("dev", "value", mintime=85.0) == 12.3


def test_daemon_device_harness_create_master_helper(daemon_device_harness):
    # Setup + Act
    axis = daemon_device_harness.create_master(HarnessLinearAxis, name="axis")

    # Assert
    assert axis.read() == 0.0


def test_daemon_device_harness_create_master_uses_master_mode_and_main_sessiontype(
    daemon_device_harness,
):
    # Setup + Act
    axis = daemon_device_harness.create_master(HarnessSessionProbe, name="axis")

    # Assert
    assert axis._mode == MASTER
    assert axis._init_mode == MASTER
    assert axis._init_sessiontype == MAIN


def test_daemon_device_harness_create_master_allows_sessiontype_override(
    daemon_device_harness,
):
    # Setup + Act
    axis = daemon_device_harness.create_master(
        HarnessSessionProbe,
        name="axis",
        sessiontype=POLLER,
    )

    # Assert
    assert axis._init_mode == MASTER
    assert axis._init_sessiontype == POLLER


def test_device_harness_create_pair_and_role_helpers(device_harness):
    # Setup
    transport = SimpleNamespace(value=1.0, target=1.0, moving=False)
    daemon, poller = device_harness.create_pair(
        HarnessLinearAxis,
        name="linear_axis",
        shared={"transport": transport},
    )

    # Act
    device_harness.run_poller(poller._cache.put, poller._name, "moving", True)
    moving = device_harness.run_daemon(daemon._cache.get, daemon, "moving")

    # Assert
    assert moving is True
    assert device_harness.run_daemon(lambda: nicos_session.sessiontype) == MAIN
    assert device_harness.run_poller(lambda: nicos_session.sessiontype) == POLLER


def test_device_harness_create_master_uses_role_specific_sessiontypes(device_harness):
    # Setup + Act
    daemon_axis = device_harness.create_master(
        "daemon",
        HarnessSessionProbe,
        name="probe",
    )
    poller_axis = device_harness.create_master(
        "poller",
        HarnessSessionProbe,
        name="probe",
    )

    # Assert
    assert daemon_axis._init_mode == MASTER
    assert poller_axis._init_mode == MASTER
    assert daemon_axis._init_sessiontype == MAIN
    assert poller_axis._init_sessiontype == POLLER

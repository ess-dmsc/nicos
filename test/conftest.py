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
#   Georg Brandl <g.brandl@fz-juelich.de>
#
# *****************************************************************************

"""Py.test configuration file containing fixtures for individual tests."""

import os
import sys
import time
from os import path

import pytest

from nicos import config, session as nicos_session
from nicos.core import MASTER
from nicos.utils import updateFileCounter

from test.utils import (
    TestSession,
    cache_addr,
    cleanup,
    killSubprocess,
    startCache,
    startElog,
)


def _safe_kill(proc):
    """Best-effort subprocess cleanup used during fixture teardown.

    We intentionally do not re-raise here so teardown errors do not hide the
    original test failure. Startup failures are still raised directly.
    """
    if not proc:
        return
    try:
        killSubprocess(proc)
    except Exception as err:
        name = getattr(proc, "nicos_name", "<unknown>")
        pid = getattr(proc, "pid", "<unknown>")
        sys.stderr.write("Failed to terminate %s process %s: %s\n" % (name, pid, err))


# This fixture will run during the entire test suite.  Therefore, the special
# cache stresstests must use a different port.
@pytest.fixture(scope="session", autouse=True)
def setup_test_suite():
    """General test suite setup (handles cacheserver and elog server)"""
    # make the test suite run the same independent of the hostname
    os.environ["INSTRUMENT"] = "test"
    try:
        cleanup()
    except OSError:
        sys.stderr.write(
            "Failed to clean up old test dir. Check if NICOS "
            "processes are still running."
        )
        sys.stderr.write("=" * 80)
        raise
    cache = startCache(cache_addr)
    elog = None
    try:
        # Elog startup can take >2s on current Python/uv environments.
        # Any startup failure should fail the whole session fixture, but we
        # first try to stop the already-running cache process.
        elog = startElog(wait=5)
    except Exception:
        # Deliberately broad: startElog/startSubprocess may fail with different
        # exception types depending on whether startup or wait-callback failed.
        _safe_kill(cache)
        raise
    try:
        yield
    finally:
        # Always attempt process teardown, also if setup/tests raised.
        _safe_kill(elog)
        _safe_kill(cache)


@pytest.fixture(scope="class")
def session(request):
    """Test session fixture"""

    nicos_session.__class__ = TestSession
    # pylint: disable=unnecessary-dunder-call
    nicos_session.__init__(request.module.__name__)
    # override the sessionid: test module, and a finer resolved timestamp
    nicos_session.sessionid = "%s-%s" % (request.module.__name__, time.time())
    nicos_session.setMode(getattr(request.module, "session_mode", MASTER))
    if request.module.session_setup:
        nicos_session.unloadSetup()
        nicos_session.loadSetup(
            request.module.session_setup,
            **getattr(request.module, "session_load_kw", {}),
        )
    if getattr(request.module, "session_spmode", False):
        nicos_session.setSPMode(True)
    yield nicos_session
    nicos_session.setSPMode(False)
    nicos_session.shutdown()


@pytest.fixture(scope="class")
def dataroot(request, session):
    """Dataroot handling fixture"""

    exp = session.experiment
    dataroot = path.join(config.nicos_root, request.module.exp_dataroot)
    os.makedirs(dataroot)

    counter = path.join(dataroot, exp.counterfile)
    updateFileCounter(counter, "scan", 42)
    updateFileCounter(counter, "point", 42)

    exp._setROParam("dataroot", dataroot)
    exp.new(1234, user="testuser")
    exp.sample.new({"name": "mysample"})

    return dataroot


@pytest.fixture
def log(session):
    """Clear nicos log handler content"""
    handler = session.testhandler
    handler.clear()
    return handler

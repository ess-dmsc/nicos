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

"""NICOS tests for Simple Parameter Mode."""

from nicos.core import SPMError

from test.utils import raises

session_setup = "axis"
session_spmode = True


def spmexec(session, source):
    session.runsource(source)


def test_spm(session):
    # note the use of createDevice here; devices used via SPM must be in the
    # "explicit devices" list, but the TestSession does not autocreate devices
    axis = session.createDevice("axis", explicit=True)
    axis.maw(0)

    # normal command execution
    spmexec(session, "maw axis 1")
    assert axis() == 1
    spmexec(session, "scan axis 1 1 2")
    assert axis() == 2

    # "direct" invocation of devices
    spmexec(session, "axis 2")
    assert axis() == 2

    # more complicated commands
    session.createDevice("slow_motor", explicit=True)
    # automatic stringification of some parameters
    spmexec(session, "get slow_motor userlimits")
    # args in parentheses/brackets are preserved
    spmexec(session, "set slow_motor userlimits (0, 2)")

    # invalid or missing syntax
    assert raises(SPMError, spmexec, session, "get axis")
    assert raises(SPMError, spmexec, session, "read @axis")
    # only one form allowed
    assert raises(SPMError, spmexec, session, "scan axis [0, 1, 2]")

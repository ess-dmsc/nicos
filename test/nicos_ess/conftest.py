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

from test.nicos_ess.device_harness import (
    isolated_daemon_device_harness,
    isolated_device_harness,
)


@pytest.fixture
def device_harness():
    """Default NICOS-style harness with daemon and poller sessions."""
    with isolated_device_harness() as harness:
        yield harness


@pytest.fixture
def daemon_device_harness():
    """Single-session daemon-style harness fixture."""
    with isolated_daemon_device_harness() as harness:
        yield harness

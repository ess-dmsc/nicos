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

from nicos_ess.devices.epics.pva import epics_common
from nicos_ess.utilities.live_frame import decode
from test.nicos_ess.device_harness import (
    isolated_daemon_device_harness,
    isolated_device_harness,
)
from test.nicos_ess.test_devices.doubles.adcore_camera import seed_camera
from test.nicos_ess.test_devices.doubles.epics_pva_backend import patch_create_wrapper


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


@pytest.fixture
def fake_epics_backend_factory(monkeypatch):
    """Factory fixture to patch EPICS wrapper creation for a specific module."""

    def _install(module):
        return patch_create_wrapper(monkeypatch, module)

    return _install


@pytest.fixture
def camera_ioc(fake_epics_backend_factory):
    """A fake areaDetector IOC with an idle camera and its image plugin."""
    return seed_camera(fake_epics_backend_factory(epics_common))


class LiveUpdates(list):
    """The calls of session.updateLiveData as (parameters, databuffers, labelbuffers)."""

    def frames(self):
        """Return the detector name and the decoded frame of each array sent."""
        return [
            (parameters["det"], decode(desc, buffer, labelbuffers))
            for parameters, databuffers, labelbuffers in self
            for desc, buffer in zip(parameters["datadescs"], databuffers, strict=True)
        ]


@pytest.fixture
def live_updates(session, monkeypatch):
    """Record what reaches the clients through session.updateLiveData."""
    updates = LiveUpdates()

    def update_live_data(parameters, databuffers, labelbuffers=None):
        # The sender may reuse its buffers, so the test keeps copies.
        databuffers = [bytes(buffer) for buffer in databuffers]
        if labelbuffers is not None:
            labelbuffers = [bytes(buffer) for buffer in labelbuffers]
        updates.append((parameters, databuffers, labelbuffers))

    monkeypatch.setattr(session, "updateLiveData", update_live_data)
    return updates

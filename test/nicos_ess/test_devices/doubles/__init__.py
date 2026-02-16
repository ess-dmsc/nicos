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
#   NICOS contributors
#
# *****************************************************************************

"""Reusable doubles for ESS device tests."""

from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    FakeEpicsBackend,
    analog_moveable_config,
    mapped_config,
    patch_create_wrapper,
    string_moveable_config,
)
from test.nicos_ess.test_devices.doubles.mapped_controller_devices import (
    HarnessLinearAxis,
    HarnessMoveableNoPrecision,
)

__all__ = [
    "FakeEpicsBackend",
    "HarnessLinearAxis",
    "HarnessMoveableNoPrecision",
    "analog_moveable_config",
    "mapped_config",
    "patch_create_wrapper",
    "string_moveable_config",
]

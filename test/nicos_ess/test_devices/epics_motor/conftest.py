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

from nicos_ess.devices.epics.pva import motor

from test.nicos_ess.test_devices.doubles import patch_create_wrapper
from test.nicos_ess.test_devices.epics_motor.helpers import pv


@pytest.fixture
def fake_backend(monkeypatch):
    return patch_create_wrapper(monkeypatch, motor)


@pytest.fixture(autouse=True)
def default_motor_pvs(fake_backend):
    defaults = {
        ".RBV": 2.5,
        ".DRBV": 2.5,
        ".VAL": 2.5,
        ".STOP": 0,
        ".VELO": 1.0,
        ".OFF": 0.0,
        ".HLM": 120.0,
        ".LLM": -120.0,
        ".DHLM": 120.0,
        ".DLLM": -120.0,
        ".CNEN": 1,
        ".SET": 0,
        ".FOFF": 0,
        ".DIR": "Pos",
        ".EGU": "mm",
        ".HOMF": 0,
        ".HOMR": 0,
        ".RDBD": 0.1,
        ".DESC": "Test Motor",
        ".MDEL": 0.1,
        ".VMAX": 10.0,
        ".VBAS": 0.1,
        ".DMOV": 1,
        ".MOVN": 0,
        ".MISS": 0,
        ".STAT": 0,
        ".SEVR": 0,
        ".LVIO": 0,
        ".LLS": 0,
        ".HLS": 0,
        "-Err": 0,
        "-ErrRst": 0,
        "-PwrAuto": 1,
        "-MsgTxt": "",
        "-MsgTxt.SEVR": 0,
    }
    for suffix, value in defaults.items():
        fake_backend.values[pv(suffix)] = value

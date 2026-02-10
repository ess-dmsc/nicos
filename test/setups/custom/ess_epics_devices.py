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
# *****************************************************************************

devices = dict(
    PvaReadable=device(
        "test.nicos_ess.test_devices.test_epics_devices.FakeEpicsReadableDevice",
        description="EPICS readable with fake wrapper",
        readpv="TEST:READ",
        unit="",
    ),
    PvaStringReadable=device(
        "test.nicos_ess.test_devices.test_epics_devices.FakeEpicsStringReadableDevice",
        description="EPICS string readable with fake wrapper",
        readpv="TEST:STR:READ",
        unit="",
    ),
    PvaAnalogMoveable=device(
        "test.nicos_ess.test_devices.test_epics_devices.FakeEpicsAnalogMoveableDevice",
        description="EPICS analog moveable with fake wrapper",
        readpv="TEST:ANA:READ",
        writepv="TEST:ANA:WRITE",
        unit="",
    ),
    PvaAnalogMoveableWithTarget=device(
        "test.nicos_ess.test_devices.test_epics_devices."
        "FakeEpicsAnalogMoveableWithTargetDevice",
        description="EPICS analog moveable with target PV and fake wrapper",
        readpv="TEST:ANAT:READ",
        writepv="TEST:ANAT:WRITE",
        targetpv="TEST:ANAT:TARGET",
        unit="",
    ),
    PvaMappedReadable=device(
        "test.nicos_ess.test_devices.test_epics_devices.FakeEpicsMappedReadableDevice",
        description="EPICS mapped readable with fake wrapper",
        readpv="TEST:MAP:READ",
        fallback="UNKNOWN",
        unit="",
    ),
    PvaMappedMoveable=device(
        "test.nicos_ess.test_devices.test_epics_devices.FakeEpicsMappedMoveableDevice",
        description="EPICS mapped moveable with fake wrapper",
        readpv="TEST:MMAP:READ",
        writepv="TEST:MMAP:WRITE",
        mapping={"CLOSED": 0, "OPEN": 1},
        unit="",
    ),
    PvaManualMappedAnalogMoveable=device(
        "test.nicos_ess.test_devices.test_epics_devices."
        "FakeEpicsManualMappedAnalogMoveableDevice",
        description="EPICS manual mapped analog moveable with fake wrapper",
        readpv="TEST:MAN:READ",
        writepv="TEST:MAN:WRITE",
        targetpv="TEST:MAN:TARGET",
        mapping={"slow": 10.0, "fast": 20.0},
        unit="",
    ),
)

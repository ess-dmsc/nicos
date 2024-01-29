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
#   Alexander Lenz <alexander.lenz@frm2.tum.de>
#
# *****************************************************************************

# generate stub TACO modules as needed to be able to import nicos.devices.taco
# modules and document them

import logging
import sys
import types


class NICOSTACOStub:
    pass


STUBS = dict(
    TACOClient = ['class Client', 'exception TACOError'],
    TACOStates = ['ALARM=45', 'AUTOMATIC=17', 'BAKEING=31', 'BAKE_REQUESTED=30',
                  'BEAM_ENABLE=21', 'BLOCKED=22', 'CLOSED=3', 'CLOSING=40',
                  'COMPLETE=1009', 'COUNTING=42', 'DEVICE_NORMAL=1005',
                  'DEVICE_OFF=1', 'DISABLED=46', 'EXTRACTED=8', 'FAULT=23',
                  'FORBIDDEN=38', 'FORCED_CLOSE=34', 'FORCED_OPEN=33',
                  'HEATER_OFF=1014', 'HIGH=6', 'HOLD=1008', 'HOLDBACK=1007',
                  'HV_ENABLE=20', 'INIT=11', 'INSERTED=7', 'LOCAL=15', 'LOW=5',
                  'MOVING=9', 'NEGATIVE_ENDSTOP=29', 'OFF=1001', 'OFF_UNAUTHORISED=35',
                  'ON=2', 'ON_NOT_REACHED=48', 'ON_NOT_REGULAR=36', 'OPEN=4',
                  'OPENING=39', 'OVERFLOW=1002', 'POSITIVE_ENDSTOP=28',
                  'PRESELECTION_REACHED=1003', 'RAMP=18', 'REMOTE=16', 'RESET=1006',
                  'RESETTING=37', 'RUN=14', 'RUNNING=44', 'SERVICE=13', 'STANDBY=12',
                  'STANDBY_NOT_REACHED=47', 'STARTED=1004', 'STARTING=24',
                  'START_REQUESTED=26', 'STOPPED=43', 'STOPPING=25', 'STOP_BAKE=32',
                  'STOP_REQUESTED=27', 'TRIPPED=19', 'UNDEFINED=41', 'UNKNOWN=0',
                  'VACUUM_FAILURE=1012', 'VACUUM_NOT_REACHED=1011', 'WARMUP=10',
                  'WATER_NOT_ATTACHED=1013'],
    TACOCommands = [],
    DEVERRORS = [],
    IOCommon = ['MODE_NORMAL=0', 'MODE_RATEMETER=1', 'MODE_PRESELECTION=2'],
    IO = ['class AnalogInput', 'class AnalogOutput', 'class DigitalInput',
          'class DigitalOutput', 'class StringIO', 'class Timer',
          'class Counter'],
    Encoder = ['class Encoder'],
    Motor = ['class Motor'],
    PowerSupply = ['class CurrentControl', 'class VoltageControl'],
    RS485Client = ['class RS485Client'],
    Temperature = ['class Sensor', 'class Controller'],
    TMCS = ['class Channel', 'class Admin'],
    Modbus = ['class Modbus'],
    ProfibusDP = ['class IO'],
    Detector = ['class Detector'],
    SIS3400 = ['class Timer', 'class MonitorCounter', 'class HistogramCounter'],
    tango = ['class DeviceProxy', 'class DevState', 'class DevVoid',
             'class DeviceAttribute', 'class DeviceState',
             'member DevState.ON=0',
             'member DevState.OFF=1',
             'member DevState.CLOSE=2',
             'member DevState.OPEN=3',
             'member DevState.INSERT=4',
             'member DevState.EXTRACT=5',
             'member DevState.MOVING=6',
             'member DevState.STANDBY=7',
             'member DevState.FAULT=8',
             'member DevState.INIT=9',
             'member DevState.RUNNING=10',
             'member DevState.ALARM=11',
             'member DevState.DISABLE=12',
             'member DevState.UNKNOWN=13',
             'class constants',
             'member constants.NUMPY_SUPPORT=True',
             'exception ConnectionFailed', 'exception CommunicationFailed',
             'exception WrongNameSyntax', 'exception DevFailed',
             'exception NonDbDevice', 'exception WrongData',
             'exception NonSupportedFeature', 'exception AsynCall',
             'exception AsynReplyNotArrived', 'exception EventSystemFailed',
             'exception DeviceUnlocked', 'exception NotAllowed',
             ],
)


def generate_stubs():
    logging.basicConfig()
    root_log = logging.getLogger()
    for modname, content in STUBS.items():
        try:
            __import__(modname)
        except Exception:
            pass  # generate stub below
        else:
            continue
        mod = types.ModuleType(modname, "NICOS stub module")
        for obj in content:
            if obj.startswith('class '):
                setattr(mod, obj[6:], type(obj[6:], (NICOSTACOStub,), {}))
            elif obj.startswith('exception '):
                setattr(mod, obj[10:], type(obj[10:], (Exception,), {}))
            elif obj.startswith('member '):
                name, member = obj[7:].split('.')
                member, value = member.split('=')
                setattr(getattr(mod, name), member, value)
            else:
                name, value = obj.split('=')
                setattr(mod, name, eval(value))
        sys.modules[modname] = mod
        root_log.info('generated TACO stub module %r', modname)

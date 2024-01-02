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
#   Alexander Lenz <alexander.lenz@frm2.tum.de>
#
# *****************************************************************************

from nicos.core import HasLimits, HasPrecision, Moveable, Param, oneof, status
from nicos.devices.tango import PyTangoDevice

from .generic import GenericLimaCCD
from .optional import LimaCooler


class Andor3LimaCCD(GenericLimaCCD):
    """
    This device class is an extension to the GenericLimaCCD that adds the
    hardware specific functionality for all Andor SDK3 based cameras.
    """

    READOUTRATES = [280, 200, 100]  # Values from sdk manual
    ELSHUTTERMODES = ['rolling', 'global']  # Values from sdk manual

    parameters = {
        'readoutrate':   Param('Rate of pixel readout from sensor',
                               type=oneof(*READOUTRATES),
                               unit='MHz', settable=True, volatile=True,
                               category='general'),
        'elshuttermode': Param('On-sensor electronic shuttering mode',
                               type=oneof(*ELSHUTTERMODES),
                               settable=True, volatile=True,
                               category='general'),
        'framerate':     Param('Frame rate',
                               type=float, unit='Hz', settable=False,
                               volatile=True, category='general'),
    }

    def doInfo(self):
        for p in ('readoutrate', 'elshuttermode', 'framerate'):
            self._pollParam(p)
        return []

    def doReadReadoutrate(self):
        return int(self._hwDev._dev.adc_rate[3:])

    def doWriteReadoutrate(self, value):
        self._hwDev._dev.adc_rate = 'MHZ%i' % value

    def doReadElshuttermode(self):
        return self._hwDev._dev.electronic_shutter_mode.lower()

    def doWriteElshuttermode(self, value):
        self._hwDev._dev.electronic_shutter_mode = value.upper()

    def doReadFramerate(self):
        return self._hwDev._dev.frame_rate

    def _specialInit(self):
        # set some dummy roi to avoid strange lima rotation behaviour
        # (not at 0, 0 to avoid possible problems with strides)
        self._writeRawRoi((8, 8, 8, 8))
        # ensure NO rotation
        self._dev.image_rotation = 'NONE'
        # set full detector size as roi
        self._writeRawRoi((0, 0, 0, 0))


class Andor3TemperatureController(PyTangoDevice, HasLimits, HasPrecision,
                                  LimaCooler, Moveable):
    """
    This devices provides access to the cooling feature of Andor3 cameras.
    """

    COOLER_STATUS_MAP = {
        'Fault': status.ERROR,
        'Drift': status.ERROR,
        'Cooler Off': status.OK,
        'Stabilised': status.OK,
        'Cooling': status.BUSY,
        'Not Stabilised': status.BUSY,
    }

    def doRead(self, maxage=0):
        return self._dev.temperature

    def doStatus(self, maxage=0):
        coolerState = self._dev.cooling_status
        nicosState = self.COOLER_STATUS_MAP.get(coolerState, status.UNKNOWN)

        return (nicosState, coolerState)

    def doStart(self, target):
        self._dev.temperature_sp = target
        self.cooleron = True

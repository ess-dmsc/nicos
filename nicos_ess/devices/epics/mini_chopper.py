#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
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
#   Michael Wedel <michael.wedel@esss.se>
#   Nikhil Biyani <nikhil.biyani@psi.ch>
#   Michael Hart <michael.hart@stfc.ac.uk>
#
# *****************************************************************************

from nicos.core import Attach, Moveable, Override, status, \
    tupleof, usermethod, Readable
from nicos.devices.epics import EpicsMoveable, EpicsReadable


class EssChopper(Moveable):
    attached_devices = {
        'speed': Attach('Speed of the chopper disc.', Moveable),
        'phase': Attach('Phase of the chopper disc', Moveable),
        'state': Attach('Current state of the chopper', Readable),
        # 'command': Attach('Command PV of the chopper', EpicsMoveable)
    }

    parameter_overrides = {
        'fmtstr': Override(default='Speed=%.2f Delay=%.2f'),
        'unit': Override(mandatory=False),
    }

    hardware_access = False
    valuetype = tupleof(float, float)

    def doRead(self, maxage=0):
        return [self._attached_speed.read(maxage),
                self._attached_phase.read(maxage)]

    def doStart(self, pos):
        if hasattr(self, '_attached_state') and \
           self._attached_state.read() == 'init':
            self.initialize()

        self._attached_speed.move(pos[0])
        self._attached_phase.move(pos[1])
        # self._attached_command.move('start')

    def doStop(self):
        self._attached_command.move('stop')

    def doStatus(self, maxage=0):
        # TODO: For error states set the status to not OK
        return status.OK, self._attached_state.read()
    #
    # @usermethod
    # def initialize(self):
    #     self._attached_command.move('init')
    #
    # @usermethod
    # def deinitialize(self):
    #     self._attached_command.move('deinit')

